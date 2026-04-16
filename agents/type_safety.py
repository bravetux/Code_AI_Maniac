# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 12th April 2026

import json
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "type_safety"

_SYSTEM_PROMPT = """You are a type system expert analysing code for type safety, type hints,
and type-related issues.

Produce a thorough markdown report:

## Type Coverage Summary
| Metric | Value |
|--------|-------|
| Functions with full type hints | N / Total (X%) |
| Functions with partial hints | N |
| Functions with no hints | N |
| Type Safety Grade | A/B/C/D |

Grade: A (>90% typed), B (70-90%), C (40-70%), D (<40%)

## Untyped Functions
List all functions/methods missing type annotations:
| Function | Line | Parameters Missing | Return Missing | Priority |
Priority based on: public API = Critical, internal but complex = High, simple/private = Low

## Type Issues
For each issue found:
### Issue N: [Title]
- **Location**: Line X
- **Problem**: What is wrong or risky
- **Suggestion**: Concrete fix with type annotation

Issues to look for:
- Missing return type annotations
- `Any` types that should be more specific
- Implicit `None` returns (should be `-> None` or `-> Optional[T]`)
- Union types that are too broad
- Mutable default arguments
- Type narrowing opportunities (isinstance checks without type guard)
- Inconsistent types (e.g., sometimes returns str, sometimes int)
- Container types without element types (list vs list[str])

## Type Improvement Suggestions
For each function, provide the recommended full signature:
```python
def function_name(param1: Type1, param2: Type2 = default) -> ReturnType:
```

## Advanced Type Patterns
Suggest where advanced typing features would help:
- TypeVar for generic functions
- Protocol for structural subtyping
- TypedDict for dictionary structures
- Literal types for constrained values
- Overload for functions with multiple signatures
- TypeGuard for type narrowing

## Recommendations
Prioritised list of type safety improvements.

Guidelines:
- Adapt to the language (Python typing, TypeScript strict mode, Java generics, etc.)
- For Python, follow PEP 484/526/544/612 conventions
- For TypeScript, consider strict mode implications
- Focus on public APIs first, then internal code
- Don't suggest types where they add noise without value (obvious one-liners)"""


def run_type_safety(conn: duckdb.DuckDBPyConnection, job_id: str,
                    file_path: str, content: str, file_hash: str,
                    language: str | None, custom_prompt: str | None,
                    **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""
    prompt = f"Analyse type safety and type coverage of this code{lang_hint}:\n\nFile: {file_path}\n\n```\n{content}\n```"
    markdown = str(agent(prompt))

    summary = f"Type safety analysis for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
