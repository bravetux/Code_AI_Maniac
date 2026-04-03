import json
import re
import duckdb
from strands import Agent
from strands.models import BedrockModel
from config.settings import get_settings
from tools.run_linter import run_linter
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a code quality expert performing semantic static analysis.
You will receive linter findings (Layer 1) and the source code.
Your job is Layer 2: identify issues that linters miss — security anti-patterns, logic smells, dead code, performance issues.

Return JSON:
{
  "semantic_findings": [
    {
      "line": <integer>,
      "category": "<security|performance|logic|maintainability>",
      "severity": "<critical|major|minor>",
      "description": "<issue description>",
      "suggestion": "<how to fix>"
    }
  ],
  "summary": "<one sentence overall assessment>"
}
Return ONLY valid JSON. No markdown fences."""


def run_static_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                        file_path: str, content: str, file_hash: str,
                        language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, "static_analysis", language, custom_prompt)
    if cached:
        return cached

    # Layer 1: run linters
    linter_result = run_linter(file_path, language or "")

    # Layer 2: LLM semantic analysis
    s = get_settings()
    model = BedrockModel(model_id=s.bedrock_model_id, temperature=s.bedrock_temperature,
                         region_name=s.aws_region)
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)

    chunks = chunk_by_lines(content, max_tokens=3000)
    all_semantic = []
    for chunk in chunks:
        linter_context = json.dumps(linter_result.get("findings", []))
        prompt = (f"Language: {language or 'unknown'}\nFile: {file_path}\n"
                  f"Linter findings (Layer 1): {linter_context}\n\n"
                  f"Source code (lines {chunk['start_line']}-{chunk['end_line']}):\n"
                  f"{chunk['content']}")
        raw = str(agent(prompt))
        text = re.sub(r"^```(?:json)?\n?", "", raw.strip())
        text = re.sub(r"\n?```$", "", text)
        try:
            parsed = json.loads(text)
            all_semantic.extend(parsed.get("semantic_findings", []))
        except (json.JSONDecodeError, ValueError):
            pass

    result = {
        "linter_findings": linter_result.get("findings", []),
        "semantic_findings": all_semantic,
        "linter_skipped": linter_result.get("skipped", False),
        "summary": f"{len(linter_result.get('findings', []))} linter issues, "
                   f"{len(all_semantic)} semantic issues found."
    }
    write_cache(conn, job_id=job_id, feature="static_analysis", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="static_analysis", source_ref=file_path,
                language=language, summary=result["summary"])
    return result
