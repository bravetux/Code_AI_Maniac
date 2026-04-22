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

"""Tiny, dependency-light OpenAPI / Swagger parser.

Used by F24 (API-Contract Conformance Checker). Accepts OpenAPI 2.x or 3.x in
either YAML or JSON and returns a flat list of ``{method, path, request, response}``
records for easy comparison against code-extracted routes.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

try:
    import yaml  # type: ignore
    _HAS_YAML = True
except ImportError:
    yaml = None
    _HAS_YAML = False


_METHODS = {"get", "post", "put", "delete", "patch", "head", "options", "trace"}


class OpenAPIParseError(RuntimeError):
    pass


def parse(text: str) -> dict:
    """Parse YAML or JSON into a Python dict."""
    text = (text or "").strip()
    if not text:
        raise OpenAPIParseError("empty spec")
    # JSON is valid YAML, so try JSON first for speed and clearer errors.
    try:
        return json.loads(text)
    except ValueError:
        pass
    if not _HAS_YAML:
        raise OpenAPIParseError(
            "Spec is not JSON and PyYAML is not installed. "
            "Install with: pip install pyyaml"
        )
    try:
        return yaml.safe_load(text)  # type: ignore[union-attr]
    except Exception as e:
        raise OpenAPIParseError(f"YAML parse failed: {e}")


def _version(spec: dict) -> str:
    if spec.get("openapi"):
        return str(spec["openapi"])
    if spec.get("swagger"):
        return str(spec["swagger"])
    return "unknown"


def extract_endpoints(spec: dict) -> list[dict]:
    """Return a flat list of endpoint records."""
    paths = spec.get("paths") or {}
    out: list[dict] = []
    for path, item in paths.items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method.lower() not in _METHODS or not isinstance(op, dict):
                continue
            out.append({
                "method": method.upper(),
                "path": path,
                "operation_id": op.get("operationId"),
                "summary": op.get("summary") or "",
                "parameters": _normalise_params(op.get("parameters") or []),
                "request_body": _normalise_request_body(op.get("requestBody") or {}),
                "responses": _normalise_responses(op.get("responses") or {}),
            })
    return out


def _normalise_params(params: Iterable[Any]) -> list[dict]:
    out = []
    for p in params or []:
        if not isinstance(p, dict):
            continue
        schema = p.get("schema") or {}
        out.append({
            "name": p.get("name"),
            "in": p.get("in"),
            "required": bool(p.get("required")),
            "type": schema.get("type") or p.get("type"),
        })
    return out


def _normalise_request_body(body: dict) -> dict:
    if not body:
        return {}
    content = body.get("content") or {}
    # Pick the first content-type's schema for the signature summary.
    for ctype, meta in content.items():
        schema = (meta or {}).get("schema") or {}
        return {"content_type": ctype, "schema_ref": schema.get("$ref"),
                "schema_type": schema.get("type")}
    return {"content_type": None}


def _normalise_responses(resp: dict) -> list[dict]:
    out = []
    for code, meta in (resp or {}).items():
        if not isinstance(meta, dict):
            continue
        out.append({"status": str(code), "description": meta.get("description", "")})
    return out


def summarise(spec: dict) -> dict:
    """Return a high-level summary of the parsed spec."""
    endpoints = extract_endpoints(spec)
    return {
        "version": _version(spec),
        "title": ((spec.get("info") or {}).get("title")) or "",
        "endpoint_count": len(endpoints),
        "endpoints": endpoints,
    }
