import json
import re
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a principal engineer writing a thorough GitHub pull request review.

You will be given automated findings (bugs, static analysis). Your job is to turn these into
high-quality, actionable PR review comments — the kind a thoughtful senior engineer writes, not
a linting bot.

For each comment:
- Reference the exact line and explain the issue in context
- Don't just restate the automated finding — add insight: why does this matter here, what is the
  consequence in this specific codebase, what is the best fix given the surrounding code
- Use a constructive, collegial tone (this is a code review, not a blame exercise)
- Use markdown formatting: code blocks for suggested fixes, bold for key points

Also write a top-level PR summary comment that:
- Gives an honest overall assessment
- Prioritises what the author must fix before merge vs. nice-to-haves
- Notes any positive aspects of the code (good practices, clean sections)

Return JSON:
{
  "comments": [
    {
      "file": "<file path>",
      "line": <integer>,
      "severity": "<critical|major|minor|suggestion>",
      "body": "<full markdown review comment — be thorough, not terse>"
    }
  ],
  "summary": "<top-level PR review comment in markdown — overall assessment, must-fix items, positives>"
}"""


def run_comment_generation(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           bug_results: dict | None = None,
                           static_results: dict | None = None) -> dict:
    cached = check_cache(conn, file_hash, "comment_generator", language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    context_parts = [f"File under review: `{file_path}`"]

    bugs = (bug_results or {}).get("bugs", [])
    if bugs:
        context_parts.append(
            f"Bug analysis findings ({len(bugs)} bugs):\n" + json.dumps(bugs, indent=2)
        )
    if (bug_results or {}).get("narrative"):
        context_parts.append(f"Bug analysis narrative:\n{bug_results['narrative']}")

    linter   = (static_results or {}).get("linter_findings", [])
    semantic = (static_results or {}).get("semantic_findings", [])
    if linter or semantic:
        context_parts.append(
            f"Static analysis findings ({len(linter)} linter, {len(semantic)} semantic):\n"
            + json.dumps(linter + semantic, indent=2)
        )
    if (static_results or {}).get("narrative"):
        context_parts.append(f"Static analysis narrative:\n{static_results['narrative']}")

    prompt = "\n\n".join(context_parts)
    raw = str(agent(prompt))
    try:
        result = parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        result = {"comments": [], "summary": raw}

    write_cache(conn, job_id=job_id, feature="comment_generator", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="comment_generator", source_ref=file_path,
                language=language,
                summary=f"{len(result.get('comments', []))} PR comments generated.")
    return result
