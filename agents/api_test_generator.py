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

"""F5 — API Test Generator from OpenAPI/Swagger.

Spec resolution: inline prefix wins, else source file when it sniffs as a
spec, else a sibling openapi.yaml/yml/json next to the source. Framework
auto-pick drives one Strands LLM call for the code tests, and
tools.postman_emitter produces a deterministic Postman 2.1 collection as
the second artifact.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.openapi_parser import parse, extract_endpoints, OpenAPIParseError
from tools.postman_emitter import build_collection
from db.queries.history import add_history

_CACHE_KEY = "api_test_generator"

_SIBLING_NAMES = ("openapi.yaml", "openapi.yml", "openapi.json",
                  "swagger.yaml", "swagger.yml", "swagger.json")

_YAML_SNIFF = re.compile(r"^\s*(openapi|swagger)\s*:", re.IGNORECASE | re.MULTILINE)


def _report_ts() -> str:
    """Return the current job's report timestamp.
    Prefers JOB_REPORT_TS (generalised); falls back to WAVE6A_REPORT_TS
    (deprecated alias) and then datetime.now()."""
    return (os.environ.get("JOB_REPORT_TS")
            or os.environ.get("WAVE6A_REPORT_TS")
            or datetime.now().strftime("%Y%m%d_%H%M%S"))


@dataclass
class _SpecResolution:
    spec: dict
    raw: str
    source: str  # one of: prefix, source, sibling


def _resolve_spec(file_path: str, content: str, custom_prompt: str | None) -> _SpecResolution:
    """Resolve the OpenAPI spec body. Raises on failure."""
    if custom_prompt:
        marker = "__openapi_spec__\n"
        if marker in custom_prompt:
            body = custom_prompt.split(marker, 1)[1]
            spec = parse(body)
            return _SpecResolution(spec=spec, raw=body, source="prefix")

    ext = os.path.splitext(file_path)[1].lower()
    head = (content or "")[:1024]
    if ext in (".yaml", ".yml") and _YAML_SNIFF.search(head):
        spec = parse(content)
        return _SpecResolution(spec=spec, raw=content, source="source")
    if ext == ".json" and ('"openapi"' in head or '"swagger"' in head):
        spec = parse(content)
        return _SpecResolution(spec=spec, raw=content, source="source")

    parent = os.path.dirname(os.path.abspath(file_path))
    for name in _SIBLING_NAMES:
        cand = os.path.join(parent, name)
        if os.path.isfile(cand):
            with open(cand, "r", encoding="utf-8") as fh:
                body = fh.read()
            spec = parse(body)
            return _SpecResolution(spec=spec, raw=body, source="sibling")

    raise RuntimeError(
        f"No OpenAPI spec resolvable for {file_path}. "
        f"Provide an inline __openapi_spec__ prefix, pass a yaml/json source, "
        f"or place openapi.yaml next to the source."
    )


_FRAMEWORK_MAP: dict[str, dict] = {
    "python":     {"framework": "pytest + requests",
                   "suffix": "test_api.py", "fence": "python",
                   "mock": "responses / httpx_mock"},
    "java":       {"framework": "REST Assured + JUnit 5",
                   "suffix": "ApiTests.java", "fence": "java",
                   "mock": "WireMock"},
    "kotlin":     {"framework": "REST Assured + JUnit 5",
                   "suffix": "ApiTests.java", "fence": "java",
                   "mock": "WireMock"},
    "csharp":     {"framework": "xUnit + HttpClient",
                   "suffix": "ApiTests.cs", "fence": "csharp",
                   "mock": "WireMock.Net"},
    "c#":         {"framework": "xUnit + HttpClient",
                   "suffix": "ApiTests.cs", "fence": "csharp",
                   "mock": "WireMock.Net"},
    ".net":       {"framework": "xUnit + HttpClient",
                   "suffix": "ApiTests.cs", "fence": "csharp",
                   "mock": "WireMock.Net"},
    "typescript": {"framework": "supertest + Jest",
                   "suffix": "api.test.ts", "fence": "typescript",
                   "mock": "nock"},
    "javascript": {"framework": "supertest + Jest",
                   "suffix": "api.test.ts", "fence": "typescript",
                   "mock": "nock"},
}


def _pick_framework(language: str | None) -> dict | None:
    """Return framework meta dict or None if language is blank/unknown."""
    if not language:
        return None
    return _FRAMEWORK_MAP.get(language.strip().lower())


_SYSTEM_PROMPT_TEMPLATE = """You are a senior API test engineer specialising in {framework}.

Generate a COMPLETE, runnable {framework} test file that exercises every endpoint listed below. Rules:

1. One test per endpoint for the happy path (2xx).
2. For endpoints that declare a 4xx response, add a negative test that triggers it (e.g. missing required body, invalid path parameter type).
3. For endpoints that declare a 5xx response, add a resilience test asserting the client handles the error cleanly.
4. Use a base URL variable so the suite runs against any environment — default it to ``https://api.example.test``.
5. Mock HTTP with {mock_lib} so tests are hermetic (no real network).
6. If the spec declares components.securitySchemes, include one test that exercises a valid auth header and one that exercises a missing/invalid header.
7. Return ONLY the complete test file wrapped in a single fenced code block:

```{fence}
<complete test file>
```

Endpoints:
{endpoint_table}

Title: {title}
Version: {version}
"""


def _format_endpoint_table(endpoints: list[dict]) -> str:
    lines = []
    for ep in endpoints:
        params = ", ".join(
            f"{p['name']}({p['in']}:{p.get('type') or 'string'})"
            for p in ep.get("parameters", [])
        ) or "-"
        statuses = ", ".join(r["status"] for r in ep.get("responses", [])) or "-"
        lines.append(f"- {ep['method']} {ep['path']} — params: {params}; responses: {statuses}")
    return "\n".join(lines) or "(no endpoints)"


def _extract_code_block(text: str, fence: str) -> str:
    pat = rf"```{re.escape(fence)}\s*\n(.*?)```"
    m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\w*\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def run_api_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, content: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    try:
        res = _resolve_spec(file_path, content, custom_prompt)
    except (RuntimeError, OpenAPIParseError) as exc:
        error_md = f"## API Test Generator — error\n\n{exc}"
        return {"markdown": error_md,
                "summary": f"F5 error: {exc}",
                "output_path": None}

    endpoints = extract_endpoints(res.spec)
    title = (res.spec.get("info") or {}).get("title") or "API"
    version = str((res.spec.get("info") or {}).get("version") or "0.1.0")

    ts = _report_ts()
    out_dir = os.path.join("Reports", ts, "api_tests")
    os.makedirs(out_dir, exist_ok=True)

    # Deterministic Postman subagent (always)
    collection = build_collection(res.spec)
    postman_path = os.path.join(out_dir, "api_collection.json")
    import json as _json
    with open(postman_path, "w", encoding="utf-8") as fh:
        fh.write(_json.dumps(collection, indent=2))

    # LLM framework-aware test generation (only if language maps)
    meta = _pick_framework(language)
    output_path: str | None = None
    framework_label = "Postman only (language blank or unmapped)"
    code_body = ""
    if meta is not None:
        prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            framework=meta["framework"],
            mock_lib=meta["mock"],
            fence=meta["fence"],
            endpoint_table=_format_endpoint_table(endpoints),
            title=title,
            version=version,
        )
        model = make_bedrock_model()
        agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, prompt))
        raw = str(agent(f"Generate the complete {meta['framework']} test file now."))
        code_body = _extract_code_block(raw, meta["fence"])

        if code_body:
            output_path = os.path.join(out_dir, meta["suffix"])
            with open(output_path, "w", encoding="utf-8") as fh:
                fh.write(code_body)
            framework_label = meta["framework"]

    md_parts = [
        f"## API Test Generator — `{title}` v{version}",
        f"- **Spec source:** {res.source}",
        f"- **Endpoints:** {len(endpoints)}",
        f"- **Framework:** {framework_label}",
        f"- **Postman collection:** `{postman_path}` ({len(collection['item'])} requests)",
    ]
    if output_path:
        md_parts.append(f"- **Code file:** `{output_path}`")
        md_parts.append(f"\n### Generated code\n\n```{meta['fence']}\n{code_body}\n```")
    markdown = "\n".join(md_parts)
    summary = (f"Generated {len(endpoints)} API tests "
               f"({framework_label}) + Postman collection.")

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": output_path,
        "postman_path": postman_path,
        "framework": framework_label,
        "endpoint_count": len(endpoints),
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
