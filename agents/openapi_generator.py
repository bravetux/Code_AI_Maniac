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
# Developed: 22nd April 2026

"""F37 — Swagger / OpenAPI Generator.

Bidirectional:
- **Code mode** (default when the input looks like source): extract routes and
  emit an OpenAPI 3.1 spec.
- **Requirements mode**: when the input is a user-story blob or a Jira / ADO /
  Qase URL (via ``tools.spec_fetcher``), synthesise a plausible OpenAPI spec
  that implements the described API.

The mode is chosen by looking at the first few lines of ``content`` — if it
contains HTTP verbs followed by quoted paths, treat it as code; otherwise
treat it as requirements. Callers can force the mode by prefixing
``custom_prompt`` with ``__mode__code\\n`` or ``__mode__requirements\\n``.
"""

import json
import os
import re
from datetime import datetime
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.openapi_parser import parse as parse_spec, OpenAPIParseError
from tools.spec_fetcher import fetch_spec, SpecFetchError
from db.queries.history import add_history

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    yaml = None
    _HAS_YAML = False

_CACHE_KEY = "openapi_generator"
_MODE_CODE_PREFIX = "__mode__code\n"
_MODE_REQ_PREFIX = "__mode__requirements\n"


_SYSTEM_PROMPT_CODE = """You are an API documentation specialist.

Given a source file that defines HTTP endpoints, produce a COMPLETE OpenAPI 3.1
specification in **YAML**. Cover:

- `info` block with title, version (derive from package manifest hints if
  present, otherwise "0.1.0"), and a short description.
- `servers` — use `http://localhost` as a placeholder when unknown.
- `paths` — one entry per implemented route, with `summary`, `parameters`,
  `requestBody` (when the handler reads a body), and explicit `responses`
  including at minimum `200` and one error status (`4xx` or `5xx`).
- `components.schemas` — inline data-transfer objects for request and response
  bodies inferred from the code.

Return ONLY a single YAML fence:

```yaml
<complete OpenAPI 3.1 spec>
```
"""

_SYSTEM_PROMPT_REQ = """You are an API designer.

Given a user story / requirement / specification narrative, design the API
that fulfils it and return a COMPLETE OpenAPI 3.1 spec in **YAML**.

Guidelines:
- Pick resource-oriented paths (`/orders`, `/orders/{id}`) unless the story
  clearly calls for RPC-style verbs.
- Default to JSON (`application/json`) for request and response bodies.
- For every endpoint include at least `200` success and a `4xx` failure case.
- Include reusable `components.schemas` for every entity mentioned in the story.
- Include `securitySchemes` for bearer auth when the story implies protected
  resources.

Return ONLY a single YAML fence:

```yaml
<complete OpenAPI 3.1 spec>
```
"""


def _detect_mode(content: str, custom_prompt: str | None) -> tuple[str, str]:
    """Return ``(mode, forwarded_prompt)``."""
    if custom_prompt and custom_prompt.startswith(_MODE_CODE_PREFIX):
        return "code", custom_prompt[len(_MODE_CODE_PREFIX):]
    if custom_prompt and custom_prompt.startswith(_MODE_REQ_PREFIX):
        return "requirements", custom_prompt[len(_MODE_REQ_PREFIX):]

    head = (content or "")[:4000]
    # Strong code signals: route decorators / registration DSLs.
    code_signals = [
        r"@app\.(get|post|put|delete|patch)\b",
        r"@router\.(get|post|put|delete|patch)\b",
        r"app\.(get|post|put|delete|patch)\s*\(",
        r"router\.(get|post|put|delete|patch)\s*\(",
        r"@RequestMapping\b|@GetMapping\b|@PostMapping\b",
        r"\[Http(Get|Post|Put|Delete|Patch)\]",
        r"^\s*(GET|POST|PUT|DELETE|PATCH)\s+/",  # Ruby/Rails-like route tables
    ]
    for pat in code_signals:
        if re.search(pat, head, re.MULTILINE):
            return "code", custom_prompt or ""
    return "requirements", custom_prompt or ""


def _extract_yaml(text: str) -> str:
    m = re.search(r"```ya?ml\s*\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def _yaml_to_json(yaml_text: str) -> str | None:
    """Best-effort YAML → JSON conversion."""
    if not _HAS_YAML:
        return None
    try:
        doc = yaml.safe_load(yaml_text)  # type: ignore[union-attr]
        return json.dumps(doc, indent=2)
    except Exception:
        return None


def run_openapi_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                          file_path: str, content: str, file_hash: str,
                          language: str | None, custom_prompt: str | None,
                          **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    mode, forwarded_prompt = _detect_mode(content, custom_prompt)

    # Requirements mode: route through the spec-fetcher so Jira/ADO URLs resolve.
    if mode == "requirements":
        try:
            spec = fetch_spec(content)
            source_body = spec["body"]
            title_hint = spec["title"]
        except SpecFetchError:
            source_body = content
            title_hint = os.path.basename(file_path) or "API"
    else:
        source_body = content
        title_hint = os.path.basename(file_path) or "API"

    base_prompt = _SYSTEM_PROMPT_CODE if mode == "code" else _SYSTEM_PROMPT_REQ
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(forwarded_prompt or None, base_prompt))

    prompt = (f"Mode: {mode}\nTitle hint: {title_hint}\n"
              f"Language: {language or 'auto'}\n\n"
              f"```\n{source_body}\n```")
    raw = str(agent(prompt))
    yaml_text = _extract_yaml(raw)
    json_text = _yaml_to_json(yaml_text)

    # Validate by parsing — if broken, surface it in the result.
    endpoint_count = 0
    parse_error = None
    try:
        doc = parse_spec(yaml_text)
        endpoint_count = len(((doc.get("paths") or {}).keys()) if isinstance(doc, dict) else [])
    except OpenAPIParseError as e:
        parse_error = str(e)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "openapi")
    os.makedirs(out_dir, exist_ok=True)
    label = re.sub(r"[^\w\-]+", "_",
                    os.path.splitext(os.path.basename(file_path))[0] or "api")
    yaml_path = os.path.join(out_dir, f"{label}.yaml")
    json_path = os.path.join(out_dir, f"{label}.json")
    with open(yaml_path, "w", encoding="utf-8") as fh:
        fh.write(yaml_text)
    if json_text:
        with open(json_path, "w", encoding="utf-8") as fh:
            fh.write(json_text)

    md_parts = [
        f"## OpenAPI Generator — `{os.path.basename(file_path)}`",
        f"- **Mode:** {mode}",
        f"- **Paths detected:** {endpoint_count}",
        f"- **YAML:** `{yaml_path}`",
    ]
    if json_text:
        md_parts.append(f"- **JSON:** `{json_path}`")
    if parse_error:
        md_parts.append(f"- ⚠ Spec parse warning: `{parse_error}`")
    md_parts += ["\n### YAML spec", f"```yaml\n{yaml_text}\n```"]

    markdown = "\n".join(md_parts)
    summary = f"OpenAPI {mode}-mode: {endpoint_count} path(s)."

    result = {
        "markdown": markdown,
        "summary": summary,
        "mode": mode,
        "yaml": yaml_text,
        "json": json_text,
        "yaml_path": yaml_path,
        "json_path": json_path if json_text else None,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
