import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "architecture_mapper"

_SYSTEM_PROMPT = """You are a software architect expert at reverse-engineering module structure,
dependencies, and architectural patterns from source code.

Analyse the code and produce a thorough markdown report:

## Module Overview
- What is this module's responsibility?
- Where does it sit in the application architecture? (e.g., data layer, service layer, API layer, UI)
- What architectural patterns does it implement? (MVC, Repository, Service, Factory, etc.)

## Dependency Map
### Imports & External Dependencies
A table of all imports/dependencies:
| Import | Type | Category | Coupling |
Type: stdlib / third-party / internal
Category: data / networking / logging / config / business-logic / testing / etc.
Coupling: Tight / Loose / Interface-based

### Exports & Public API
What this module exposes to others:
| Symbol | Type | Used By (inferred) |

## Dependency Analysis
- **Afferent coupling (Ca)**: How many modules likely depend on this one?
- **Efferent coupling (Ce)**: How many modules does this depend on?
- **Instability (I = Ce/(Ca+Ce))**: 0 = stable, 1 = unstable
- **Abstractness**: Ratio of abstract types to concrete types

## Layer Violations
Identify any architectural anti-patterns:
- Circular dependencies (even potential ones based on import structure)
- Layer skipping (e.g., UI code directly accessing database)
- Upward dependencies (lower layers importing from higher layers)
- God modules (too many responsibilities)

## Component Diagram
Provide a Mermaid diagram showing this module's relationships:
```mermaid
graph TD
    ...
```

## Cohesion Assessment
- Is the module cohesive (all parts related to one purpose)?
- Are there functions/classes that don't belong here?
- Should this module be split?

## Recommendations
- Dependency reduction opportunities
- Interface extraction candidates
- Module split suggestions
- Coupling reduction strategies

Guidelines:
- Be precise about import paths and symbol names
- Distinguish between compile-time and runtime dependencies
- Consider both direct and transitive dependencies
- Focus on actionable architectural improvements"""


def run_architecture_mapper(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""
    prompt = f"Map the architecture and dependencies of this code{lang_hint}:\n\nFile: {file_path}\n\n```\n{content}\n```"
    markdown = str(agent(prompt))

    summary = f"Architecture mapping for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
