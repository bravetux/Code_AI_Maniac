import json
import re
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a senior software engineer doing a thorough code review.

For each bug, security issue, or logic error you find:
- Explain clearly what is wrong and why it is wrong
- Describe what could go wrong at runtime (crashes, data corruption, security breach, etc.)
- Identify the root cause — not just the symptom
- Give a concrete, specific fix (not generic advice)
- Note if this bug is a symptom of a broader design or pattern problem

Be as thorough as you would be when reviewing a colleague's code before a production release.
Do not skip minor issues — a minor issue today can become a critical bug under load or edge cases.

Return a JSON object:
{
  "bugs": [
    {
      "line": <integer line number>,
      "severity": "<critical|major|minor>",
      "description": "<thorough explanation of what is wrong and why — can be multiple sentences>",
      "runtime_impact": "<what actually goes wrong at runtime if this bug is not fixed>",
      "root_cause": "<the underlying reason this bug exists>",
      "suggestion": "<specific, concrete fix — include example code if helpful>",
      "github_comment": "<ready-to-paste GitHub PR review comment in markdown>"
    }
  ],
  "narrative": "<overall review narrative — patterns you noticed, general code quality assessment, biggest concerns, what the author should focus on first>",
  "summary": "<one sentence count of findings>"
}

If no bugs are found, return {"bugs": [], "narrative": "<your assessment of why the code is sound>", "summary": "No bugs found."}"""


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return json.loads(text)


def run_bug_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                     file_path: str, content: str, file_hash: str,
                     language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, "bug_analysis", language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)

    chunks = chunk_by_lines(content, max_tokens=3000)
    all_bugs = []
    narratives = []

    for chunk in chunks:
        prompt = (f"Language: {language or 'detect from code'}\n"
                  f"File: {file_path}\n"
                  f"Lines {chunk['start_line']}-{chunk['end_line']}:\n\n"
                  f"{chunk['content']}")
        raw = str(agent(prompt))
        try:
            parsed = _parse_json_response(raw)
            all_bugs.extend(parsed.get("bugs", []))
            if parsed.get("narrative"):
                narratives.append(parsed["narrative"])
        except (json.JSONDecodeError, ValueError):
            # If JSON parsing fails, treat entire response as narrative
            narratives.append(raw)

    # Deduplicate by (line, description)
    seen = set()
    deduped = []
    for bug in all_bugs:
        key = (bug.get("line"), bug.get("description", "")[:50])
        if key not in seen:
            seen.add(key)
            deduped.append(bug)

    result = {
        "bugs": deduped,
        "narrative": "\n\n".join(narratives) if narratives else "",
        "summary": f"{len(deduped)} bug(s) found." if deduped else "No bugs found.",
    }

    write_cache(conn, job_id=job_id, feature="bug_analysis",
                file_hash=file_hash, language=language,
                custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="bug_analysis",
                source_ref=file_path, language=language,
                summary=result["summary"])
    return result
