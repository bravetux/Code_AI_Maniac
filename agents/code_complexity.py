import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "code_complexity"

_SYSTEM_PROMPT = """You are a software metrics expert analysing code complexity.

Examine the code and produce a thorough complexity report in markdown:

## Summary Metrics
A table of overall file-level metrics:
| Metric | Value | Rating |
|--------|-------|--------|
| Cyclomatic Complexity (total) | N | Good/Moderate/High/Very High |
| Cognitive Complexity (total) | N | Good/Moderate/High/Very High |
| Max Nesting Depth | N | ... |
| Number of Functions/Methods | N | ... |
| Average Function Length (lines) | N | ... |
| Maintainability Index (0-100) | N | A/B/C/D |

Rating thresholds:
- Cyclomatic: 1-10 Good, 11-20 Moderate, 21-50 High, >50 Very High
- Cognitive: 1-8 Good, 9-15 Moderate, 16-30 High, >30 Very High
- Maintainability: 85-100 A, 65-84 B, 40-64 C, <40 D

## Per-Function Breakdown
For each function/method, a table:
| Function | Lines | Cyclomatic | Cognitive | Nesting | Rating |
Present the most complex functions first.

## Complexity Hotspots
Identify the top 3-5 most complex functions and for each:
- Why it is complex (deep nesting, many branches, long parameter lists, etc.)
- Specific simplification suggestions (extract method, replace conditional with polymorphism, etc.)
- Estimated complexity reduction from the suggested refactoring

## Patterns of Concern
- Deeply nested conditionals
- God functions (too many responsibilities)
- Long parameter lists
- Complex boolean expressions
- Excessive branching

## Recommendations
Prioritised list of actions to reduce complexity, ordered by impact.

Guidelines:
- Be precise with numbers — count actual branches, nesting levels, and lines
- Focus on actionable insights, not just metrics
- Include line numbers when referencing specific code"""


def run_code_complexity(conn: duckdb.DuckDBPyConnection, job_id: str,
                        file_path: str, content: str, file_hash: str,
                        language: str | None, custom_prompt: str | None,
                        **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""
    prompt = f"Analyse the complexity of this code{lang_hint}:\n\nFile: {file_path}\n\n```\n{content}\n```"
    markdown = str(agent(prompt))

    summary = f"Complexity analysis for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
