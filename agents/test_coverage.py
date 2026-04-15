import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "test_coverage"

_SYSTEM_PROMPT = """You are a senior QA engineer and testing expert analysing source code to assess
test coverage gaps and suggest test cases.

You are NOT running tests — you are analysing the code structure to identify what SHOULD be tested.

Produce a thorough markdown report:

## Testability Assessment
- Overall testability rating (High/Medium/Low) with justification
- Dependency injection friendliness
- Side effects and external dependencies that complicate testing
- Suggested test framework/approach for this code

## Functions & Methods Inventory
A table of all public functions/methods:
| Function | Lines | Parameters | Returns | Side Effects | Test Priority |
Test priority: Critical / High / Medium / Low based on complexity and risk.

## Missing Test Cases
For each function/method that needs testing, list specific test cases:

### `function_name` (Priority: Critical/High/Medium)
- **Happy path**: description of normal-case test
- **Edge cases**: empty input, boundary values, null/None, overflow, etc.
- **Error cases**: invalid input, exceptions, failure modes
- **Integration points**: tests needed for external dependencies

## Untestable Code
Identify code that is difficult to test and why:
- Tight coupling to external systems
- Hidden dependencies / global state
- Complex setup requirements
- Suggestions to make it testable (dependency injection, interfaces, etc.)

## Suggested Test Skeleton
Provide a code skeleton (in the same language) for the 3-5 highest-priority test cases.
Use appropriate test framework conventions (pytest for Python, Jest for JS, etc.).

## Recommendations
Prioritised list of testing actions, from highest impact to lowest.

Guidelines:
- Focus on what matters — not everything needs a test
- Critical paths and error handling are highest priority
- Be specific about test inputs and expected outputs
- Consider both unit and integration test needs"""


def run_test_coverage(conn: duckdb.DuckDBPyConnection, job_id: str,
                      file_path: str, content: str, file_hash: str,
                      language: str | None, custom_prompt: str | None,
                      **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""
    prompt = f"Analyse test coverage gaps for this code{lang_hint}:\n\nFile: {file_path}\n\n```\n{content}\n```"
    markdown = str(agent(prompt))

    summary = f"Test coverage analysis for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
