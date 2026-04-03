import json
import re
import duckdb
from strands import Agent
from strands.models import BedrockModel
from config.settings import get_settings
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a senior engineer writing GitHub pull request review comments.
Given bug findings and/or static analysis findings, generate ready-to-paste review comments
in GitHub inline comment format.

Return JSON:
{
  "comments": [
    {
      "file": "<file path>",
      "line": <integer>,
      "body": "<GitHub review comment text — use markdown>",
      "severity": "<critical|major|minor|suggestion>"
    }
  ],
  "summary": "<overall PR review summary suitable for the top-level comment>"
}
Return ONLY valid JSON. No markdown fences."""


def run_comment_generation(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           bug_results: dict | None = None,
                           static_results: dict | None = None) -> dict:
    cached = check_cache(conn, file_hash, "comment_generator", language, custom_prompt)
    if cached:
        return cached

    s = get_settings()
    model = BedrockModel(model_id=s.bedrock_model_id, temperature=s.bedrock_temperature,
                         region_name=s.aws_region)
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)

    context_parts = [f"File: {file_path}"]
    if bug_results:
        context_parts.append(
            f"Bug Analysis findings:\n{json.dumps(bug_results.get('bugs', []), indent=2)}"
        )
    if static_results:
        all_findings = (static_results.get("linter_findings", [])
                        + static_results.get("semantic_findings", []))
        context_parts.append(
            f"Static Analysis findings:\n{json.dumps(all_findings, indent=2)}"
        )

    prompt = "\n\n".join(context_parts)
    raw = str(agent(prompt))
    text = re.sub(r"^```(?:json)?\n?", "", raw.strip())
    text = re.sub(r"\n?```$", "", text)
    try:
        result = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        result = {"comments": [], "summary": raw}

    write_cache(conn, job_id=job_id, feature="comment_generator", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="comment_generator", source_ref=file_path,
                language=language, summary=f"{len(result.get('comments', []))} comments generated.")
    return result
