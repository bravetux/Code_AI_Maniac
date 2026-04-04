import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a senior engineer explaining how a piece of code works to a new team member.

Trace the execution flow of the code and write a clear, thorough explanation. Write as you would in a
technical wiki or architecture doc — use markdown with headers, bullet points, and inline code references.

Your response should cover:
1. **Entry points** — where execution starts, what triggers it
2. **Execution flow** — step-by-step walkthrough of what happens, in order. Reference actual function
   names, variable names, and line numbers from the code.
3. **Data transformations** — how data changes shape as it moves through the code
4. **Control flow** — key branches, loops, error paths, and what determines which path is taken
5. **Exit points** — what is returned/emitted, under what conditions
6. **Interactions** — external calls, I/O, side effects

Be specific. Name the actual functions and variables. A reader should be able to follow along in the
code while reading your explanation."""


def run_code_flow(conn: duckdb.DuckDBPyConnection, job_id: str,
                  file_path: str, content: str, file_hash: str,
                  language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, "code_flow", language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)
    chunks = chunk_by_lines(content, max_tokens=4000)

    section_docs = []
    for chunk in chunks:
        prompt = (f"Language: {language or 'detect from code'}\nFile: {file_path}\n"
                  f"Lines {chunk['start_line']}-{chunk['end_line']}:\n\n{chunk['content']}")
        section_docs.append(str(agent(prompt)))

    if len(section_docs) > 1:
        synthesis_prompt = (
            f"You have analysed {file_path} in sections. "
            "Synthesise the section-by-section analyses below into one coherent execution flow document. "
            "Remove redundancy, connect the sections into a single narrative, and ensure the overall "
            "flow from start to finish is clear.\n\n"
            + "\n\n---\n\n".join(section_docs)
        )
        markdown = str(agent(synthesis_prompt))
    else:
        markdown = section_docs[0] if section_docs else ""

    # Extract a one-line summary from the first sentence of the markdown
    first_line = markdown.strip().splitlines()[0].lstrip("#").strip() if markdown.strip() else ""
    summary = first_line[:120] if first_line else f"Execution flow traced for {file_path}."

    result = {
        "markdown": markdown,
        "summary": summary,
        # Keep these for mermaid agent compatibility
        "entry_points": [],
        "steps": [],
    }
    write_cache(conn, job_id=job_id, feature="code_flow", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="code_flow", source_ref=file_path,
                language=language, summary=summary)
    return result
