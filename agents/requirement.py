import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a business analyst reverse-engineering a software requirements specification
from existing source code.

Read the code carefully and produce a well-structured requirements document in markdown. Write as a
professional BA would — clear, unambiguous, and traceable to the code.

Your document should include:

## System Overview
A concise description of what this code does and what business problem it solves.

## Functional Requirements
List each requirement as:
**REQ-NNN** `<ComponentName>` — *The system shall <verb> <object>.*
> Rationale: <why this requirement exists, what business rule it encodes>
> Source: lines <N>–<M>

Cover every distinct behaviour, including error handling, edge cases, and configuration points.
Do not skip minor requirements — they often encode important business rules.

## Non-Functional Requirements
Performance, reliability, security, or operational requirements implied by the code.

## Assumptions & Open Questions
List anything unclear or that requires clarification from stakeholders."""


def run_requirement_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                              file_path: str, content: str, file_hash: str,
                              language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, "requirement", language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))
    chunks = chunk_by_lines(content, max_tokens=4000)

    section_docs = []
    for chunk in chunks:
        prompt = (f"Language: {language or 'detect from code'}\nFile: {file_path}\n"
                  f"Lines {chunk['start_line']}-{chunk['end_line']}:\n\n{chunk['content']}")
        section_docs.append(str(agent(prompt)))

    if len(section_docs) > 1:
        synthesis_prompt = (
            f"You have extracted requirements from {file_path} in sections. "
            "Merge the sections below into one coherent requirements document. "
            "Re-number REQ IDs sequentially, remove duplicates, and ensure the document reads "
            "as a single cohesive specification.\n\n"
            + "\n\n---\n\n".join(section_docs)
        )
        markdown = str(agent(synthesis_prompt))
    else:
        markdown = section_docs[0] if section_docs else ""

    req_count = markdown.count("**REQ-")
    summary = f"{req_count} requirement(s) extracted from {file_path}."

    result = {
        "markdown": markdown,
        "summary": summary,
        # Keep for backwards compat with any code that reads requirements list
        "requirements": [],
    }
    write_cache(conn, job_id=job_id, feature="requirement", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="requirement", source_ref=file_path,
                language=language, summary=summary)
    return result
