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

_CACHE_KEY = "refactoring_advisor"

_SYSTEM_PROMPT = """You are a senior software architect and refactoring expert. You identify code
smells and recommend specific, well-known refactoring patterns from Martin Fowler's refactoring
catalogue and the Gang of Four design patterns.

Produce a thorough markdown report:

## Code Smell Inventory
A table of all detected smells:
| # | Smell | Location | Severity | Refactoring |
Severity: Critical / Major / Minor

### Common Smells to Detect:
- **Long Method**: Functions with too many lines or responsibilities
- **God Class/Module**: Classes or modules doing too much
- **Feature Envy**: Methods that use another class's data more than their own
- **Data Clumps**: Groups of data that travel together and should be a class/struct
- **Primitive Obsession**: Using primitives instead of small objects (e.g., strings for money)
- **Switch/If Chains**: Long conditional chains that should be polymorphism
- **Shotgun Surgery**: A change requires editing many classes
- **Divergent Change**: One class is changed for different reasons
- **Dead Code**: Unused functions, unreachable branches, commented-out code
- **Deep Nesting**: Excessive indentation levels
- **Magic Numbers/Strings**: Unexplained literal values
- **Long Parameter List**: Functions with too many parameters
- **Speculative Generality**: Unused abstractions added "just in case"
- **Message Chains**: Long chains of method calls (a.b().c().d())
- **Inappropriate Intimacy**: Classes that are too tightly coupled

## Detailed Refactoring Recommendations
For each smell (top 5-8 most impactful), provide:

### Smell N: [Name] — Lines X-Y
**What's Wrong:** Explain the problem concretely.
**Why It Matters:** Maintenance cost, bug risk, readability impact.
**Recommended Refactoring:** Name the specific pattern (e.g., Extract Method, Replace Conditional
with Polymorphism, Introduce Parameter Object).
**Before:**
```
[current code snippet]
```
**After:**
```
[refactored code sketch]
```
**Effort:** Low / Medium / High
**Risk:** Low / Medium / High (chance of introducing bugs)

## Design Pattern Opportunities
Where known design patterns would improve the structure:
- Strategy / State for behavioral switching
- Observer for event handling
- Factory for object creation
- Decorator for feature layering
- Repository for data access
- Template Method for algorithm variation

## Quick Wins
Simple refactorings with high impact and low risk:
1. Rename unclear variables/functions
2. Extract obvious helper methods
3. Remove dead code
4. Replace magic numbers with named constants

## Refactoring Roadmap
A prioritised sequence of refactorings:
| Priority | Refactoring | Effort | Impact | Risk |
Order: highest impact-to-effort ratio first.

Guidelines:
- Be specific — include line numbers, function names, and code examples
- Show both before and after code
- Consider the programming language's idioms and conventions
- Distinguish between necessary refactorings and nice-to-haves
- Factor in risk — some refactorings require extensive testing"""


def run_refactoring_advisor(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            complexity_results: dict | None = None,
                            static_results: dict | None = None,
                            duplication_results: dict | None = None,
                            **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""

    # Build context from prior analyses
    context_parts = []
    if complexity_results and complexity_results.get("markdown"):
        context_parts.append(f"## Prior Complexity Analysis:\n{complexity_results['markdown'][:2000]}")
    if static_results and static_results.get("markdown"):
        context_parts.append(f"## Prior Static Analysis:\n{static_results['markdown'][:2000]}")
    if duplication_results and duplication_results.get("markdown"):
        context_parts.append(f"## Prior Duplication Detection:\n{duplication_results['markdown'][:2000]}")

    context_block = ""
    if context_parts:
        context_block = ("\n\nYou also have results from prior analyses to inform your recommendations "
                         "(do not repeat their findings — build on them):\n\n"
                         + "\n\n".join(context_parts) + "\n\n")

    prompt = (f"Identify code smells and recommend refactorings for this code{lang_hint}:\n\n"
              f"File: {file_path}\n\n```\n{content}\n```"
              + context_block)
    markdown = str(agent(prompt))

    summary = f"Refactoring advisor for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
