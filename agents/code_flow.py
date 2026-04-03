import json
import re
import duckdb
from strands import Agent
from strands.models import BedrockModel
from config.settings import get_settings
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a senior engineer tracing code execution flow.
Analyze the code and describe the execution flow as a sequence of steps.

Return a JSON object:
{
  "entry_points": ["<function or class that starts execution>"],
  "steps": [
    {
      "step": 1,
      "description": "<what happens, e.g. 'user calls foo() with params x, y'>",
      "calls": ["<function/method called>"],
      "returns": "<what is returned or emitted>"
    }
  ],
  "summary": "<one paragraph narrative of the full flow>"
}
Return ONLY valid JSON. No markdown fences."""


def run_code_flow(conn: duckdb.DuckDBPyConnection, job_id: str,
                  file_path: str, content: str, file_hash: str,
                  language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, "code_flow", language, custom_prompt)
    if cached:
        return cached

    s = get_settings()
    model = BedrockModel(model_id=s.bedrock_model_id, temperature=s.bedrock_temperature,
                         region_name=s.aws_region)
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)
    chunks = chunk_by_lines(content, max_tokens=4000)

    all_steps = []
    entry_points = []
    step_counter = 1
    for chunk in chunks:
        prompt = (f"Language: {language or 'unknown'}\nFile: {file_path}\n"
                  f"Lines {chunk['start_line']}-{chunk['end_line']}:\n\n{chunk['content']}")
        raw = str(agent(prompt))
        text = re.sub(r"^```(?:json)?\n?", "", raw.strip())
        text = re.sub(r"\n?```$", "", text)
        try:
            parsed = json.loads(text)
            for ep in parsed.get("entry_points", []):
                if ep not in entry_points:
                    entry_points.append(ep)
            for step in parsed.get("steps", []):
                step["step"] = step_counter
                step_counter += 1
                all_steps.append(step)
        except (json.JSONDecodeError, ValueError):
            pass

    result = {
        "entry_points": entry_points,
        "steps": all_steps,
        "summary": f"{len(all_steps)} execution steps traced for {file_path}."
    }
    write_cache(conn, job_id=job_id, feature="code_flow", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="code_flow", source_ref=file_path,
                language=language, summary=result["summary"])
    return result
