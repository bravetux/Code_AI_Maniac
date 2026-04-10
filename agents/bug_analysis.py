import json
import re
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history
from config.settings import get_settings

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
      "fixed_snippet": "<minimal corrected code snippet that resolves the bug — include only the lines that change, with enough surrounding context to be applied>",
      "github_comment": "<ready-to-paste GitHub PR review comment in markdown>"
    }
  ],
  "narrative": "<overall review narrative — patterns you noticed, general code quality assessment, biggest concerns, what the author should focus on first>",
  "summary": "<one sentence count of findings>"
}

If no bugs are found, return {"bugs": [], "narrative": "<your assessment of why the code is sound>", "summary": "No bugs found."}"""


_parse_json_response = parse_json_response


_CACHE_KEY = "bug_analysis:v2"   # bump when output schema changes


def run_bug_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                     file_path: str, content: str, file_hash: str,
                     language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

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

    # Normalise severity — templates may instruct high/medium/low instead of
    # the expected critical/major/minor, causing bugs to vanish from the UI.
    _SEV_MAP = {
        "critical": "critical", "high": "critical", "error": "critical",
        "major": "major", "medium": "major", "warning": "major",
        "minor": "minor", "low": "minor", "info": "minor",
        "suggestion": "minor", "note": "minor", "trivial": "minor",
    }
    for bug in all_bugs:
        raw = (bug.get("severity") or "").strip().lower()
        bug["severity"] = _SEV_MAP.get(raw, "minor")

    # Deduplicate by (line, description)
    seen = set()
    deduped = []
    for bug in all_bugs:
        key = (bug.get("line"), bug.get("description", "")[:50])
        if key not in seen:
            seen.add(key)
            deduped.append(bug)

    # Attach original_snippet — extract programmatically from file content
    context = get_settings().bug_context_lines
    file_lines = content.splitlines()
    for bug in deduped:
        line_no = bug.get("line")
        try:
            line_no = int(line_no)   # LLM sometimes returns a string
        except (TypeError, ValueError):
            line_no = None
        if line_no and line_no >= 1:
            start = max(0, line_no - 1 - context)
            end = min(len(file_lines), line_no + context)
            bug["original_snippet"] = "\n".join(file_lines[start:end])
            bug["snippet_start_line"] = start + 1  # 1-based for display
            bug["line"] = line_no   # normalise to int
        else:
            bug["original_snippet"] = ""
            bug["snippet_start_line"] = None

    result = {
        "bugs": deduped,
        "narrative": "\n\n".join(narratives) if narratives else "",
        "summary": f"{len(deduped)} bug(s) found." if deduped else "No bugs found.",
        "language": language or "",
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY,
                file_hash=file_hash, language=language,
                custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="bug_analysis",
                source_ref=file_path, language=language,
                summary=result["summary"])
    return result
