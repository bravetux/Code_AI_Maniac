import json
import re
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model
from tools.run_linter import run_linter
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a code quality expert performing deep semantic static analysis.

You will receive linter output (Layer 1 — mechanical checks) and the source code.
Your job is Layer 2: find what linters cannot — semantic problems, design smells, and hidden risks.

For each issue you find, go beyond naming it. Explain:
- **What** the problem is, with reference to the specific lines/functions involved
- **Why** it is a problem — the failure mode, not just the rule being broken
- **What** could go wrong in production (performance degradation, security vulnerability, data loss, etc.)
- **How** to fix it — concrete suggestion, not generic advice

Categories to look for:
- Security anti-patterns (injection, unsafe deserialization, hardcoded secrets, improper validation)
- Performance issues (unnecessary allocations, O(n²) loops, blocking calls in hot paths)
- Logic smells (dead code, unreachable branches, off-by-one, incorrect operator precedence)
- Maintainability problems (magic numbers, deeply nested logic, overly long functions)
- Concurrency issues (race conditions, missing locks, improper shared state)
- Error handling gaps (swallowed exceptions, missing null checks, unhandled edge cases)

Return a JSON object:
{
  "semantic_findings": [
    {
      "line": <integer>,
      "category": "<security|performance|logic|maintainability|concurrency|error_handling>",
      "severity": "<critical|major|minor>",
      "description": "<thorough explanation — what is wrong, why it matters, what breaks at runtime>",
      "suggestion": "<specific fix with example if helpful>"
    }
  ],
  "narrative": "<overall code quality assessment — patterns of concern, what the team should prioritise, any systemic issues you notice>",
  "summary": "<one sentence total count>"
}"""


def run_static_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                        file_path: str, content: str, file_hash: str,
                        language: str | None, custom_prompt: str | None) -> dict:
    cached = check_cache(conn, file_hash, "static_analysis", language, custom_prompt)
    if cached:
        return cached

    # Layer 1: linter
    linter_result = run_linter(file_path, language or "")

    # Layer 2: LLM semantic analysis
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=custom_prompt or _SYSTEM_PROMPT)

    chunks = chunk_by_lines(content, max_tokens=3000)
    all_semantic = []
    narratives = []

    for chunk in chunks:
        linter_context = json.dumps(linter_result.get("findings", []))
        prompt = (f"Language: {language or 'detect from code'}\nFile: {file_path}\n"
                  f"Linter findings (Layer 1): {linter_context}\n\n"
                  f"Source code (lines {chunk['start_line']}-{chunk['end_line']}):\n"
                  f"{chunk['content']}")
        raw = str(agent(prompt))
        text = re.sub(r"^```(?:json)?\n?", "", raw.strip())
        text = re.sub(r"\n?```$", "", text)
        try:
            parsed = json.loads(text)
            all_semantic.extend(parsed.get("semantic_findings", []))
            if parsed.get("narrative"):
                narratives.append(parsed["narrative"])
        except (json.JSONDecodeError, ValueError):
            narratives.append(raw)

    result = {
        "linter_findings": linter_result.get("findings", []),
        "semantic_findings": all_semantic,
        "narrative": "\n\n".join(narratives) if narratives else "",
        "linter_skipped": linter_result.get("skipped", False),
        "summary": (f"{len(linter_result.get('findings', []))} linter issue(s), "
                    f"{len(all_semantic)} semantic issue(s) found."),
    }
    write_cache(conn, job_id=job_id, feature="static_analysis", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="static_analysis", source_ref=file_path,
                language=language, summary=result["summary"])
    return result
