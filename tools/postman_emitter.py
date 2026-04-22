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

"""Deterministic Postman 2.1 collection builder.

Subagent for F5 (api_test_generator). Consumes a parsed OpenAPI dict (as
returned by ``tools.openapi_parser.parse``) and emits a Postman v2.1
collection with one request per operation. No LLM involvement.
"""

from __future__ import annotations

import json
from typing import Any

_POSTMAN_SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"

_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


def build_collection(spec: dict, base_url: str | None = None) -> dict:
    """Build a Postman 2.1 collection from a parsed OpenAPI spec dict."""
    info = spec.get("info") or {}
    title = info.get("title") or "API"
    version = str(info.get("version") or "0.1.0")

    resolved_base = base_url or _first_server_url(spec) or "https://api.example.test"

    collection: dict = {
        "info": {
            "name": title,
            "_postman_id": f"wave6a-{_slug(title)}-{version}",
            "description": info.get("description") or f"Generated from OpenAPI spec: {title} v{version}",
            "schema": _POSTMAN_SCHEMA,
        },
        "variable": [
            {"key": "baseUrl", "value": resolved_base, "type": "string"},
        ],
        "item": [],
    }

    paths = spec.get("paths") or {}
    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        for method, op in path_item.items():
            if method.lower() not in _METHODS or not isinstance(op, dict):
                continue
            collection["item"].append(_build_item(path, method.upper(), op, spec))

    return collection


def _first_server_url(spec: dict) -> str | None:
    servers = spec.get("servers") or []
    if servers and isinstance(servers[0], dict):
        return servers[0].get("url")
    return None


def _slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "-" for c in text).strip("-") or "api"


def _build_item(path: str, method: str, op: dict, spec: dict) -> dict:
    postman_path = path
    path_vars: list[dict] = []
    for p in (op.get("parameters") or []):
        if not isinstance(p, dict):
            continue
        if p.get("in") == "path":
            name = p.get("name")
            if name:
                postman_path = postman_path.replace("{" + name + "}", ":" + name)
                path_vars.append({
                    "key": name,
                    "value": "",
                    "description": p.get("description") or f"path parameter `{name}`",
                })

    query = []
    for p in (op.get("parameters") or []):
        if not isinstance(p, dict):
            continue
        if p.get("in") == "query":
            query.append({
                "key": p.get("name"),
                "value": "",
                "description": p.get("description") or "",
                "disabled": not p.get("required", False),
            })

    headers = []
    for p in (op.get("parameters") or []):
        if not isinstance(p, dict):
            continue
        if p.get("in") == "header":
            headers.append({
                "key": p.get("name"),
                "value": "",
                "description": p.get("description") or "",
            })

    body = _build_body(op, spec)
    if body:
        headers.insert(0, {"key": "Content-Type",
                           "value": body.get("content_type", "application/json")})

    raw_path = postman_path.lstrip("/")
    segments = [s for s in raw_path.split("/") if s]

    request: dict = {
        "method": method,
        "header": [{"key": h["key"], "value": h["value"],
                    "description": h.get("description", "")} for h in headers],
        "url": {
            "raw": "{{baseUrl}}/" + raw_path,
            "host": ["{{baseUrl}}"],
            "path": segments,
        },
    }
    if path_vars:
        request["url"]["variable"] = path_vars
    if query:
        request["url"]["query"] = query
    if body and "raw" in body:
        request["body"] = {"mode": "raw", "raw": body["raw"],
                           "options": {"raw": {"language": "json"}}}

    return {
        "name": f"{method} {path}",
        "request": request,
        "event": [_status_2xx_assertion()],
    }


def _build_body(op: dict, spec: dict) -> dict:
    rb = op.get("requestBody")
    if not isinstance(rb, dict):
        return {}
    content = rb.get("content") or {}
    for ctype, meta in content.items():
        if not isinstance(meta, dict):
            continue
        if "example" in meta:
            example = meta["example"]
            return {"content_type": ctype, "raw": json.dumps(example, indent=2)}
        examples = meta.get("examples") or {}
        for ex_val in examples.values():
            if isinstance(ex_val, dict) and "value" in ex_val:
                return {"content_type": ctype,
                        "raw": json.dumps(ex_val["value"], indent=2)}
        schema = meta.get("schema") or {}
        stub = _stub_from_schema(schema, spec)
        return {"content_type": ctype, "raw": json.dumps(stub, indent=2)}
    return {}


def _stub_from_schema(schema: dict, spec: dict, _depth: int = 0) -> Any:
    if _depth > 4:
        return None
    if not isinstance(schema, dict):
        return None
    if "$ref" in schema:
        ref = schema["$ref"]
        resolved = _resolve_ref(ref, spec)
        return _stub_from_schema(resolved or {}, spec, _depth + 1)
    t = schema.get("type")
    if t == "object" or "properties" in schema:
        obj: dict = {}
        for name, child in (schema.get("properties") or {}).items():
            obj[name] = _stub_from_schema(child, spec, _depth + 1)
        return obj
    if t == "array":
        items = schema.get("items") or {}
        return [_stub_from_schema(items, spec, _depth + 1)]
    if t == "integer":
        return 0
    if t == "number":
        return 0.0
    if t == "boolean":
        return False
    if t == "string":
        fmt = schema.get("format") or ""
        if fmt == "date-time":
            return "1970-01-01T00:00:00Z"
        if fmt == "date":
            return "1970-01-01"
        if fmt == "email":
            return "user@example.test"
        if fmt == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        return ""
    return None


def _resolve_ref(ref: str, spec: dict) -> dict | None:
    if not ref.startswith("#/"):
        return None
    parts = ref[2:].split("/")
    node: Any = spec
    for p in parts:
        if isinstance(node, dict) and p in node:
            node = node[p]
        else:
            return None
    return node if isinstance(node, dict) else None


def _status_2xx_assertion() -> dict:
    return {
        "listen": "test",
        "script": {
            "type": "text/javascript",
            "exec": [
                "pm.test(\"status is 2xx\", function () {",
                "    pm.expect(pm.response.code).to.be.within(200, 299);",
                "});",
            ],
        },
    }
