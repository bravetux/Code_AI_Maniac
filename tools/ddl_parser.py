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

"""Deterministic DDL parser (regex-based — not a full SQL AST).

Subagent for F14 (sql_generator). Extracts tables, views, and RLS policies
from PostgreSQL-flavoured DDL. Unsupported statements are silently skipped.
"""

from __future__ import annotations

import re

_CREATE_TABLE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?"
    r"([A-Za-z_][A-Za-z0-9_\.]*)\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)
_CREATE_VIEW_RE = re.compile(
    r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+([A-Za-z_][A-Za-z0-9_\.]*)"
    r"\s+AS\s+(.+?);",
    re.IGNORECASE | re.DOTALL,
)
_CREATE_POLICY_RE = re.compile(
    r"CREATE\s+POLICY\s+([A-Za-z_][A-Za-z0-9_]*)\s+ON\s+"
    r"([A-Za-z_][A-Za-z0-9_\.]*)\s+"
    r"(?:AS\s+(?:PERMISSIVE|RESTRICTIVE)\s+)?"
    r"FOR\s+(\w+)\s*"
    r"(?:TO\s+[^U]+?\s+)?"
    r"(?:USING\s*\((.+?)\)\s*)?"
    r"(?:WITH\s+CHECK\s*\((.+?)\)\s*)?;",
    re.IGNORECASE | re.DOTALL,
)

_COL_RE = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s+"
    r"([A-Za-z][A-Za-z0-9_\(\)\s]*?)"
    r"(?:\s+(.*))?$",
)
_FK_INLINE_RE = re.compile(
    r"REFERENCES\s+([A-Za-z_][A-Za-z0-9_\.]*)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)",
    re.IGNORECASE,
)


def parse_ddl(text: str) -> dict:
    if not text or not text.strip():
        return {"tables": [], "views": [], "policies": []}

    tables: list[dict] = []
    for m in _CREATE_TABLE_RE.finditer(text):
        try:
            table = _parse_table(m.group(1), m.group(2))
            tables.append(table)
        except Exception:
            continue

    views: list[dict] = []
    for m in _CREATE_VIEW_RE.finditer(text):
        views.append({"name": m.group(1), "definition": m.group(2).strip()})

    policies: list[dict] = []
    for m in _CREATE_POLICY_RE.finditer(text):
        policies.append({
            "name": m.group(1),
            "table": m.group(2),
            "command": m.group(3),
            "using": (m.group(4) or "").strip(),
            "check": (m.group(5) or "").strip(),
        })

    return {"tables": tables, "views": views, "policies": policies}


def _parse_table(name: str, body: str) -> dict:
    columns: list[dict] = []
    for raw_col in _split_columns(body):
        col = _parse_column(raw_col)
        if col:
            columns.append(col)
    return {"name": name, "columns": columns}


def _split_columns(body: str) -> list[str]:
    """Split a CREATE TABLE body on commas, respecting parenthesis depth."""
    out: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == "," and depth == 0:
            if current:
                out.append("".join(current).strip())
                current = []
        else:
            current.append(ch)
    if current:
        tail = "".join(current).strip()
        if tail:
            out.append(tail)
    return out


def _parse_column(raw: str) -> dict | None:
    text = raw.strip()
    up = text.upper()
    if up.startswith(("PRIMARY KEY", "FOREIGN KEY", "CONSTRAINT",
                      "UNIQUE", "CHECK")):
        return None
    m = _COL_RE.match(text)
    if not m:
        return None
    name = m.group(1)
    type_ = m.group(2).strip()
    rest = (m.group(3) or "").upper()
    nullable = "NOT NULL" not in rest
    pk = "PRIMARY KEY" in rest
    default_m = re.search(r"DEFAULT\s+([^,]+)", m.group(3) or "", re.IGNORECASE)
    default = default_m.group(1).strip() if default_m else None
    fk_m = _FK_INLINE_RE.search(m.group(3) or "")
    fk = {"ref_table": fk_m.group(1), "ref_col": fk_m.group(2)} if fk_m else None
    return {
        "name": name,
        "type": type_,
        "nullable": nullable,
        "default": default,
        "pk": pk,
        "fk": fk,
    }
