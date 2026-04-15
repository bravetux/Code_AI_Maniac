import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "change_impact"

_SYSTEM_PROMPT = """You are a software engineering expert specialising in change impact analysis.
Given source code, you assess how changes to this code would ripple through the system.

Produce a thorough markdown report:

## Impact Overview
| Metric | Value |
|--------|-------|
| Public API Surface | N functions/classes/exports |
| Internal Coupling Points | N |
| Estimated Blast Radius | Low / Medium / High / Critical |
| Change Confidence | High / Medium / Low |

## Public API Surface
Every symbol this module exposes that other code could depend on:
| Symbol | Type | Stability | Change Risk |
Stability: Stable / Evolving / Experimental
Change Risk: Safe to change / Requires coordination / Breaking change risk

## Dependency Chain Analysis
### Who Depends on This Code (Downstream Impact)
Based on the public API, what types of callers likely exist:
- Direct consumers of exported functions/classes
- Indirect consumers via re-exports
- Configuration consumers
- Test dependencies

### What This Code Depends On (Upstream Risk)
If upstream dependencies change, what breaks here:
- Hard dependencies (will crash if removed)
- Soft dependencies (graceful degradation possible)
- Version-sensitive dependencies

## Change Scenarios
Analyse common modification scenarios:

### Scenario 1: Adding a New Parameter to [key function]
- What callers would break?
- Backward-compatible approach?
- Test impact?

### Scenario 2: Changing the Return Type of [key function]
- Downstream impact?
- Migration path?

### Scenario 3: Removing/Renaming [key function]
- Blast radius estimate
- Deprecation strategy

(Generate 2-4 scenarios based on the most important/risky functions in the code.)

## Side Effect Map
Identify functions with side effects:
| Function | Side Effects | Impact if Changed |
Side effects: DB writes, file I/O, network calls, global state mutation, logging, etc.

## Safe Change Zones
Areas of the code that can be modified with low risk:
- Private/internal functions with no external callers
- Pure functions with no side effects
- Well-isolated utility code

## Test Impact Assessment
If this code changes:
- Which test categories are affected? (unit, integration, e2e)
- Are there likely untested change paths?
- Suggested regression test focus areas

## Recommendations
- High-risk areas to add tests before modifying
- Interfaces to stabilise before refactoring
- Decoupling opportunities to reduce blast radius

Guidelines:
- Be specific about function names and line numbers
- Think about both compile-time and runtime breakage
- Consider backwards compatibility implications
- Focus on realistic change scenarios, not hypothetical ones"""


def run_change_impact(conn: duckdb.DuckDBPyConnection, job_id: str,
                      file_path: str, content: str, file_hash: str,
                      language: str | None, custom_prompt: str | None,
                      **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""
    prompt = f"Analyse the change impact and blast radius for this code{lang_hint}:\n\nFile: {file_path}\n\n```\n{content}\n```"
    markdown = str(agent(prompt))

    summary = f"Change impact analysis for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
