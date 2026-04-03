import json
import re
import duckdb
from strands import Agent
from strands.models import BedrockModel
from config.settings import get_settings
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a business analyst reverse-engineering requirements from code.
Analyze the source code and extract functional requirements.

Return a JSON object:
{
  "requirements": [
    {
      "id": "REQ-001",
      "component": "<class or module name>",
      "statement": "The system shall <verb> <object>.",
      "source_lines": [<line numbers>]
    }
  ],
  "summary": "<overall system purpose in one paragraph>"
}
Return ONLY valid JSON. No markdown fences."""


def run_requirement_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                              file_path: str, content: str, file_hash: str,
                              language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, "requirement", language, custom_prompt)
    if cached:
        return cached

    s = get_settings()
    model = BedrockModel(model_id=s.bedrock_model_id, temperature=s.bedrock_temperature,
                         region_name=s.aws_region)
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)

    chunks = chunk_by_lines(content, max_tokens=4000)
    all_reqs = []
    counter = 1
    for chunk in chunks:
        prompt = (f"Language: {language or 'unknown'}\nFile: {file_path}\n"
                  f"Lines {chunk['start_line']}-{chunk['end_line']}:\n\n{chunk['content']}")
        raw = str(agent(prompt))
        text = re.sub(r"^```(?:json)?\n?", "", raw.strip())
        text = re.sub(r"\n?```$", "", text)
        try:
            parsed = json.loads(text)
            for req in parsed.get("requirements", []):
                req["id"] = f"REQ-{counter:03d}"
                counter += 1
                all_reqs.append(req)
        except (json.JSONDecodeError, ValueError):
            pass

    result = {
        "requirements": all_reqs,
        "summary": f"{len(all_reqs)} requirement(s) extracted from {file_path}."
    }
    write_cache(conn, job_id=job_id, feature="requirement", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="requirement", source_ref=file_path,
                language=language, summary=result["summary"])
    return result
