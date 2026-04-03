import json
import re
import duckdb
from strands import Agent
from strands.models import BedrockModel
from config.settings import get_settings
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a senior software engineer performing a code review.
Analyze the provided code for bugs, security issues, and logic errors.

Return a JSON object with this exact structure:
{
  "bugs": [
    {
      "line": <integer line number>,
      "severity": "<critical|major|minor>",
      "description": "<clear description of the bug>",
      "suggestion": "<specific fix suggestion>",
      "github_comment": "<ready-to-paste GitHub review comment>"
    }
  ],
  "summary": "<one sentence summary of findings>"
}

If no bugs are found, return {"bugs": [], "summary": "No bugs found."}
Return ONLY valid JSON. No markdown fences."""


def _make_model() -> BedrockModel:
    s = get_settings()
    return BedrockModel(
        model_id=s.bedrock_model_id,
        temperature=s.bedrock_temperature,
        region_name=s.aws_region,
    )


def _parse_json_response(text: str) -> dict:
    """Extract JSON from agent response, handling common wrapping."""
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

    system = custom_prompt or _SYSTEM_PROMPT
    model = _make_model()
    agent = Agent(model=model, system_prompt=system)

    chunks = chunk_by_lines(content, max_tokens=3000)
    all_bugs = []

    for chunk in chunks:
        prompt = (f"Language: {language or 'unknown'}\n"
                  f"File: {file_path}\n"
                  f"Lines {chunk['start_line']}-{chunk['end_line']}:\n\n"
                  f"{chunk['content']}")
        raw = str(agent(prompt))
        try:
            parsed = _parse_json_response(raw)
            all_bugs.extend(parsed.get("bugs", []))
        except (json.JSONDecodeError, ValueError):
            pass  # partial failure — continue with other chunks

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
        "summary": f"{len(deduped)} bug(s) found." if deduped else "No bugs found."
    }

    write_cache(conn, job_id=job_id, feature="bug_analysis",
                file_hash=file_hash, language=language,
                custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="bug_analysis",
                source_ref=file_path, language=language,
                summary=result["summary"])
    return result
