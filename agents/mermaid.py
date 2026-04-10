import json
import re
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPTS = {
    "flowchart": """Generate a Mermaid flowchart diagram for the given code.
Return JSON: {"diagram_type": "flowchart", "mermaid_source": "<valid mermaid flowchart LR code>", "description": "<what the diagram shows>"}
Return ONLY valid JSON. No markdown fences.""",

    "sequence": """Generate a Mermaid sequence diagram for the given code.
Return JSON: {"diagram_type": "sequence", "mermaid_source": "<valid mermaid sequenceDiagram code>", "description": "<what the diagram shows>"}
Return ONLY valid JSON. No markdown fences.""",

    "class": """Generate a Mermaid class diagram for the given code.
Return JSON: {"diagram_type": "class", "mermaid_source": "<valid mermaid classDiagram code>", "description": "<what the diagram shows>"}
Return ONLY valid JSON. No markdown fences.""",
}


def run_mermaid(conn: duckdb.DuckDBPyConnection, job_id: str,
                file_path: str, content: str, file_hash: str,
                language: str | None, custom_prompt: str | None,
                diagram_type: str = "flowchart",
                flow_context: dict | None = None) -> dict:
    """
    Generate a Mermaid diagram. If flow_context is provided (from CodeFlowAgent),
    it is injected into the prompt to avoid redundant Bedrock calls.
    """
    cache_key = f"mermaid_{diagram_type}"
    cached = check_cache(conn, file_hash, cache_key, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    system = resolve_prompt(custom_prompt, _SYSTEM_PROMPTS.get(diagram_type, _SYSTEM_PROMPTS["flowchart"]))
    agent = Agent(model=model, system_prompt=system)

    if flow_context:
        prompt = (f"Based on this execution flow analysis, generate a {diagram_type} diagram:\n\n"
                  f"{json.dumps(flow_context, indent=2)}")
    else:
        chunks = chunk_by_lines(content, max_tokens=4000)
        prompt = (f"Language: {language or 'detect from code'}\nFile: {file_path}\n\n"
                  + "".join(c["content"] for c in chunks[:2]))

    raw = str(agent(prompt))
    try:
        result = parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        result = {"diagram_type": diagram_type, "mermaid_source": raw,
                  "description": "Generated diagram"}

    write_cache(conn, job_id=job_id, feature=cache_key, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="mermaid", source_ref=file_path,
                language=language, summary=f"{diagram_type} diagram generated.")
    return result
