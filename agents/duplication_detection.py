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

_CACHE_KEY = "duplication_detection"

_SYSTEM_PROMPT = """You are a code quality expert specialising in detecting code duplication and
DRY (Don't Repeat Yourself) violations.

Analyse the code and produce a thorough markdown report:

## Duplication Summary
| Metric | Value |
|--------|-------|
| Duplicate Blocks Found | N |
| Near-Duplicate Blocks | N |
| Total Duplicated Lines | N |
| Duplication Percentage | X% |
| DRY Score | Good/Fair/Poor |

## Exact Duplicates
Code blocks that are identical or nearly identical (copy-pasted). For each:
- **Location**: Lines X-Y and Lines A-B
- **Code**: Show the duplicated block
- **Impact**: Why this duplication is problematic

## Near-Duplicates (Clones)
Code blocks that are structurally similar but differ in variable names, constants, or
minor logic. For each:
- **Location**: Lines X-Y and Lines A-B
- **Similarity**: approximate percentage
- **Differences**: What varies between the copies
- **Pattern**: The underlying shared logic

## Repeated Patterns
Higher-level patterns of repetition:
- Similar error handling blocks
- Repeated validation logic
- Boilerplate patterns that could be abstracted
- Similar data transformation pipelines

## Refactoring Suggestions
For each duplication found, provide a concrete refactoring:
- **Extract Function**: common logic → shared function with parameters for differences
- **Extract Base Class/Mixin**: repeated methods → shared base
- **Template Method**: similar algorithms with varying steps
- **Strategy Pattern**: similar structure with different behavior
- Include a code sketch of the proposed extraction

## Recommendations
Prioritised list of extractions ordered by:
1. Lines of code saved
2. Maintenance risk reduced
3. Ease of refactoring

Guidelines:
- Be precise — include line numbers
- Distinguish between harmful duplication and acceptable repetition (sometimes repeating
  2-3 lines is clearer than abstracting)
- Focus on duplication that increases maintenance burden
- Show concrete refactored code, not just advice"""


def run_duplication_detection(conn: duckdb.DuckDBPyConnection, job_id: str,
                              file_path: str, content: str, file_hash: str,
                              language: str | None, custom_prompt: str | None,
                              **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""
    prompt = f"Detect code duplication in this file{lang_hint}:\n\nFile: {file_path}\n\n```\n{content}\n```"
    markdown = str(agent(prompt))

    summary = f"Duplication detection for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
