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

_CACHE_KEY = "api_doc_generator"

_SYSTEM_PROMPT = """You are a technical documentation expert who generates comprehensive API
documentation from source code.

Analyse the code and produce polished API documentation in markdown:

## Module Overview
- **Module**: module name / file path
- **Purpose**: One-paragraph description of what this module does
- **Language**: detected language and version conventions
- **Dependencies**: Key external dependencies required

## Quick Start
A minimal usage example showing the most common use case:
```
[language-appropriate code example]
```

## API Reference

### Classes
For each public class:

#### `ClassName`
**Description**: What this class represents and when to use it.

**Constructor**:
```
ClassName(param1: Type, param2: Type = default) -> ClassName
```
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|

**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|

**Methods**:

##### `method_name(params) -> ReturnType`
Description of what the method does.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|

**Returns**: Description of return value.
**Raises**: List of exceptions that can be raised.

**Example**:
```
[usage example]
```

### Functions
For each public function:

#### `function_name(params) -> ReturnType`
Description.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|

**Returns**: Description.
**Raises**: Exceptions.
**Example**: Usage example.

### Constants & Configuration
| Name | Type | Value | Description |

### Type Definitions
Any custom types, enums, TypedDicts, dataclasses, interfaces:
```
[type definition]
```

## Error Handling
- What exceptions does this module raise?
- Error codes or error types
- Recovery strategies

## Usage Examples
3-5 complete examples covering:
1. Basic usage
2. Advanced usage with options
3. Error handling
4. Integration with other modules (if apparent)

## Notes & Caveats
- Thread safety considerations
- Performance characteristics
- Known limitations
- Version compatibility notes

Guidelines:
- Write as if this is the official documentation someone would read to use this module
- Include realistic, runnable code examples
- Use the language's documentation conventions (docstring style, JSDoc, etc.)
- Be precise about types, defaults, and edge cases
- Document both the happy path and error cases
- If a function has side effects, document them prominently"""


def run_api_doc_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                          file_path: str, content: str, file_hash: str,
                          language: str | None, custom_prompt: str | None,
                          flow_context: dict | None = None,
                          **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    lang_hint = f" (language: {language})" if language else ""

    context_block = ""
    if flow_context and flow_context.get("markdown"):
        context_block = (f"\n\nYou also have a code flow analysis to help understand execution order "
                         f"(do not repeat it — use it for context):\n\n{flow_context['markdown'][:2000]}\n\n")

    prompt = (f"Generate comprehensive API documentation for this code{lang_hint}:\n\n"
              f"File: {file_path}\n\n```\n{content}\n```"
              + context_block)
    markdown = str(agent(prompt))

    summary = f"API documentation for {file_path}."
    result = {"markdown": markdown, "summary": summary}

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
