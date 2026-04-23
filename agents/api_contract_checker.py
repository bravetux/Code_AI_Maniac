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

"""F24 — API-Contract Conformance Checker.

Compares a declared OpenAPI / Swagger specification against the routes that
are actually implemented in the submitted source file. Flags:

- endpoints declared but not implemented
- endpoints implemented but not declared
- method / parameter / status mismatches

The caller passes the OpenAPI spec via the ``custom_prompt`` channel using
the sentinel prefix ``__openapi_spec__\\n<spec body>``. Everything after the
newline is treated as the literal spec body (YAML or JSON). If that prefix is
absent, the agent attempts to locate a sibling ``openapi.yaml`` / ``.json`` /
``swagger.json`` in the same directory as ``file_path``.
"""

import os
from datetime import datetime
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.cache import check_cache, write_cache
from tools.openapi_parser import parse as parse_spec, summarise, OpenAPIParseError
from db.queries.history import add_history

_CACHE_KEY = "api_contract_checker"
_SPEC_PREFIX = "__openapi_spec__\n"


_SYSTEM_PROMPT = """You are an API governance reviewer. You receive:

- A declared OpenAPI / Swagger contract (parsed into a list of endpoints)
- A source file that implements an HTTP API (any framework: Flask, FastAPI,
  Express, Spring, ASP.NET, Gin, Rails, Koa, etc.)

First, extract every route the code actually exposes — capture HTTP method,
URL template, required query / path / body parameters, and declared response
statuses. Treat route decorators, router registrations, and attribute routing
equally.

Then produce STRICT JSON:

{
  "implemented": [
    {"method": "GET", "path": "/users/{id}", "line": 42, "params": ["id"], "responses": ["200", "404"]}
  ],
  "declared": [...],
  "missing": [
    {"method": "DELETE", "path": "/users/{id}", "reason": "declared in spec but not implemented"}
  ],
  "extra": [
    {"method": "POST", "path": "/internal/debug", "reason": "implemented but not in spec"}
  ],
  "mismatches": [
    {"method": "GET", "path": "/users", "issue": "param 'page' required in spec but optional in code"}
  ],
  "score": 0.0,
  "notes": "..."
}

Rules:
- `score` is a float in [0, 1] representing contract conformance (1.0 = perfect).
- Compare paths after normalising path parameters: `/users/{id}` == `/users/:id` == `/users/<int:id>`.
- Be conservative with mismatches — prefer missing/extra when uncertain.
- Ignore health, metrics, and docs endpoints (`/health`, `/metrics`, `/docs`, `/openapi.json`).

Return JSON only. No fences.
"""


def _extract_spec_body(custom_prompt: str | None, file_path: str) -> tuple[str, str]:
    """Return ``(spec_text, effective_prompt)``.

    The OpenAPI blob is removed from ``custom_prompt`` before it is forwarded
    as the system-prompt override.
    """
    if custom_prompt and custom_prompt.startswith(_SPEC_PREFIX):
        body = custom_prompt[len(_SPEC_PREFIX):]
        return body, ""

    # Look for a sibling spec file.
    dir_ = os.path.dirname(os.path.abspath(file_path))
    for name in ("openapi.yaml", "openapi.yml", "openapi.json",
                 "swagger.yaml", "swagger.yml", "swagger.json"):
        candidate = os.path.join(dir_, name)
        if os.path.isfile(candidate):
            try:
                with open(candidate, "r", encoding="utf-8") as fh:
                    return fh.read(), custom_prompt or ""
            except OSError:
                continue
    return "", custom_prompt or ""


def run_api_contract_checker(conn: duckdb.DuckDBPyConnection, job_id: str,
                             file_path: str, content: str, file_hash: str,
                             language: str | None, custom_prompt: str | None,
                             **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    spec_text, forwarded_prompt = _extract_spec_body(custom_prompt, file_path)
    if not spec_text.strip():
        result = {
            "markdown": (f"## API-Contract Checker — `{os.path.basename(file_path)}`\n\n"
                          f"_No OpenAPI / Swagger spec was supplied and none was "
                          f"found next to the source file._\n\n"
                          f"Provide the spec by prefixing the custom prompt with "
                          f"`{_SPEC_PREFIX}` followed by the YAML/JSON body, or "
                          f"drop an `openapi.yaml` next to the source."),
            "summary": "No spec supplied; skipped.",
            "skipped": True,
        }
        write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                    language=language, custom_prompt=custom_prompt, result=result)
        return result

    try:
        spec_doc = parse_spec(spec_text)
        spec_summary = summarise(spec_doc)
    except OpenAPIParseError as e:
        raise RuntimeError(f"OpenAPI parse failed: {e}")

    declared = spec_summary["endpoints"]

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(forwarded_prompt or None, _SYSTEM_PROMPT))

    # Compact the declared endpoints for the prompt — keep the model focused.
    declared_compact = "\n".join(
        f"- {e['method']} {e['path']} "
        f"params=[{', '.join(p.get('name') or '?' for p in e['parameters'])}] "
        f"responses=[{', '.join(r['status'] for r in e['responses'])}]"
        for e in declared
    ) or "(none)"

    prompt = (
        f"File: {file_path}\nLanguage: {language or 'auto'}\n\n"
        f"Declared endpoints (from spec v{spec_summary['version']}, "
        f"{spec_summary['endpoint_count']} total):\n{declared_compact}\n\n"
        f"Implementation source:\n```\n{content}\n```"
    )
    raw = str(agent(prompt))
    try:
        payload = parse_json_response(raw)
    except Exception:
        payload = {
            "implemented": [], "declared": declared, "missing": [],
            "extra": [], "mismatches": [], "score": 0.0,
            "notes": "LLM response was not valid JSON.",
        }

    missing = payload.get("missing") or []
    extra = payload.get("extra") or []
    mismatches = payload.get("mismatches") or []
    score = float(payload.get("score") or 0.0)

    lines = [
        f"## API-Contract Checker — `{os.path.basename(file_path)}`",
        f"- **Spec:** {spec_summary.get('title') or 'untitled'} (v{spec_summary['version']})",
        f"- **Declared endpoints:** {len(declared)}",
        f"- **Implemented endpoints:** {len(payload.get('implemented') or [])}",
        f"- **Conformance score:** {score:.2f}\n",
    ]
    if missing:
        lines.append(f"### Missing ({len(missing)}) — declared but not implemented")
        lines.extend(f"- `{m.get('method','?')} {m.get('path','?')}` — {m.get('reason','')}"
                     for m in missing)
    if extra:
        lines.append(f"\n### Extra ({len(extra)}) — implemented but not declared")
        lines.extend(f"- `{e.get('method','?')} {e.get('path','?')}` — {e.get('reason','')}"
                     for e in extra)
    if mismatches:
        lines.append(f"\n### Mismatches ({len(mismatches)})")
        lines.extend(f"- `{m.get('method','?')} {m.get('path','?')}` — {m.get('issue','')}"
                     for m in mismatches)
    if payload.get("notes"):
        lines.append(f"\n> {payload['notes']}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "api_contract")
    os.makedirs(out_dir, exist_ok=True)
    label = os.path.splitext(os.path.basename(file_path))[0] or "report"
    report_path = os.path.join(out_dir, f"{label}.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    summary = (f"score={score:.2f} missing={len(missing)} "
               f"extra={len(extra)} mismatches={len(mismatches)}")

    result = {
        "markdown": "\n".join(lines),
        "summary": summary,
        "missing": missing,
        "extra": extra,
        "mismatches": mismatches,
        "score": score,
        "output_path": report_path,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
