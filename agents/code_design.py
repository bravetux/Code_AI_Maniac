import json
import re
import duckdb
from strands import Agent
from strands.models import BedrockModel
from config.settings import get_settings
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a senior software architect creating design documentation.
Analyze the provided source code and produce a design document.

Return a JSON object with this structure:
{
  "title": "<component/module name>",
  "purpose": "<what this code does in 2-3 sentences>",
  "responsibilities": ["<responsibility 1>", "<responsibility 2>"],
  "public_api": [
    {"name": "<function/class name>", "signature": "<signature>", "description": "<what it does>"}
  ],
  "dependencies": ["<import or external system>"],
  "data_contracts": "<description of inputs/outputs/data shapes>",
  "markdown": "<full design doc in Markdown format>"
}
Return ONLY valid JSON. No markdown fences."""


def run_code_design(conn: duckdb.DuckDBPyConnection, job_id: str,
                    file_path: str, content: str, file_hash: str,
                    language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, "code_design", language, custom_prompt)
    if cached:
        return cached

    s = get_settings()
    model = BedrockModel(model_id=s.bedrock_model_id, temperature=s.bedrock_temperature,
                         region_name=s.aws_region)
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)

    # For design docs, prefer whole-file context; chunk only if needed
    chunks = chunk_by_lines(content, max_tokens=6000)
    if len(chunks) == 1:
        prompt = f"Language: {language or 'unknown'}\nFile: {file_path}\n\n{content}"
        raw = str(agent(prompt))
    else:
        # Summarise each chunk then synthesise
        summaries = []
        for chunk in chunks:
            p = (f"Summarise this code section (lines {chunk['start_line']}-{chunk['end_line']}):\n"
                 f"{chunk['content']}")
            summaries.append(str(agent(p)))
        prompt = (f"Based on these section summaries, write a full design doc for {file_path}:\n\n"
                  + "\n---\n".join(summaries))
        raw = str(agent(prompt))

    text = raw.strip()
    text = re.sub(r"^```(?:json)?\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    try:
        result = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        result = {"markdown": raw, "title": file_path, "purpose": "", "responsibilities": [],
                  "public_api": [], "dependencies": [], "data_contracts": ""}

    write_cache(conn, job_id=job_id, feature="code_design", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="code_design", source_ref=file_path,
                language=language, summary=result.get("purpose", "Design doc generated."))
    return result
