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

"""F14 — NL → SQL / Stored-Procedure Generator.

Schema-aware: parses DDL via tools.ddl_parser to build a compact summary
fed to the LLM. PostgreSQL-first dialect with ANSI-generic fallback.
RLS-aware when parsing PG policies.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.ddl_parser import parse_ddl
from tools.patch_emitter import emit as emit_patch
from db.queries.history import add_history

_CACHE_KEY = "sql_generator"
_POSTGRES_ALIASES = {"postgres", "postgresql", "pgsql"}


def _report_ts() -> str:
    return (os.environ.get("JOB_REPORT_TS")
            or os.environ.get("WAVE6A_REPORT_TS")
            or datetime.now().strftime("%Y%m%d_%H%M%S"))


def _pick_dialect(language: str | None) -> str:
    if language and language.strip().lower() in _POSTGRES_ALIASES:
        return "postgres"
    return "generic"


def _resolve_schema(file_path: str, content: str,
                    custom_prompt: str | None) -> dict:
    # Strip _APPEND_PREFIX wrap if present (F10 UI helper convention)
    working = custom_prompt or ""
    from agents._bedrock import _APPEND_PREFIX
    if working.startswith(_APPEND_PREFIX):
        working = working[len(_APPEND_PREFIX):]

    # 1. Prefix
    if "__db_schema__\n" in working:
        body = working.split("__db_schema__\n", 1)[1]
        body = re.split(r"^__\w+__", body, flags=re.MULTILINE)[0]
        return parse_ddl(body)

    # 2. Source is DDL
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".sql", ".ddl"):
        return parse_ddl(content)

    # 3. Sibling file
    parent = os.path.dirname(os.path.abspath(file_path))
    for name in ("schema.sql", "schema.ddl"):
        cand = os.path.join(parent, name)
        if os.path.isfile(cand):
            with open(cand, "r", encoding="utf-8") as fh:
                return parse_ddl(fh.read())

    return {"tables": [], "views": [], "policies": []}


def _resolve_prompt_text(custom_prompt: str | None) -> str:
    if not custom_prompt:
        return ""
    working = custom_prompt
    from agents._bedrock import _APPEND_PREFIX
    if working.startswith(_APPEND_PREFIX):
        working = working[len(_APPEND_PREFIX):]
    m = re.search(r"__prompt__\n(.+?)(?=^__\w+__|\Z)",
                  working, re.DOTALL | re.MULTILINE)
    return m.group(1).strip() if m else ""


def _build_schema_summary(schema: dict) -> str:
    lines: list[str] = []
    for tbl in schema.get("tables", []):
        cols = []
        for c in tbl["columns"]:
            bits = [c["name"], c.get("type", "")]
            if c.get("pk"):
                bits.append("PK")
            if not c.get("nullable", True):
                bits.append("NOT NULL")
            if c.get("fk"):
                fk = c["fk"]
                bits.append(f"FK→{fk['ref_table']}.{fk['ref_col']}")
            cols.append(" ".join(b for b in bits if b))
        lines.append(f"- {tbl['name']}({', '.join(cols)})")
    for view in schema.get("views", []):
        lines.append(f"- view {view['name']}")
    if schema.get("policies"):
        lines.append("\nRLS policies:")
        for p in schema["policies"]:
            lines.append(f"  - {p['name']} on {p['table']} "
                         f"FOR {p['command']} USING ({p['using']})")
    return "\n".join(lines) or "(empty schema)"


_SYSTEM_PROMPT = """You are a senior database engineer generating SQL from natural language.

Dialect: {dialect}
Given the schema below and the user's request, emit ONE complete SQL statement
(SELECT / INSERT / UPDATE / DELETE / CREATE / CALL as appropriate).

Rules:
1. Return the SQL wrapped in a single fenced ```sql block. No explanation.
2. Reference only tables and columns from the schema. Never hallucinate names.
3. Respect RLS policies when present — include appropriate WHERE filters or
   session setting references.
4. In postgres mode, prefer dialect features (CTEs, jsonb, arrays, generate_series,
   current_setting for RLS). In generic mode, stick to ANSI SQL.

Schema:
{schema_summary}
"""


def _extract_sql(raw: str) -> str:
    m = re.search(r"```sql\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\w*\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    return raw.strip()


_SQL_KEYWORDS_RE = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|CALL|WITH)\b",
                              re.IGNORECASE)


def run_sql_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                      file_path: str, content: str, file_hash: str,
                      language: str | None, custom_prompt: str | None,
                      **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    nl_prompt = _resolve_prompt_text(custom_prompt)
    if not nl_prompt:
        return {
            "markdown": "## NL → SQL Generator — error\n\n"
                        "No prompt supplied. Provide the natural-language request "
                        "via `__prompt__\\n<description>` in the fine-tune prompt.",
            "summary": "F14 error: no prompt",
            "output_path": None,
        }

    schema = _resolve_schema(file_path, content, custom_prompt)
    if not schema["tables"] and not schema["views"]:
        return {
            "markdown": "## NL → SQL Generator — error\n\n"
                        "No schema resolvable. Provide DDL via `__db_schema__\\n<DDL>`, "
                        "a `.sql`/`.ddl` source file, or sibling `schema.sql`.",
            "summary": "F14 error: no schema",
            "output_path": None,
        }

    dialect = _pick_dialect(language)
    schema_summary = _build_schema_summary(schema)
    system = _SYSTEM_PROMPT.format(dialect=dialect, schema_summary=schema_summary)

    try:
        model = make_bedrock_model()
        agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, system))
        raw = str(agent(f"Request: {nl_prompt}\n\nEmit the SQL now."))
    except Exception as exc:  # pragma: no cover
        return {
            "markdown": f"## NL → SQL Generator — LLM call failed\n\n{exc}",
            "summary": f"F14 error: LLM call failed ({exc.__class__.__name__})",
            "output_path": None,
        }

    sql = _extract_sql(raw)
    if not sql or not _SQL_KEYWORDS_RE.search(sql):
        return {
            "markdown": f"## NL → SQL Generator — LLM returned non-SQL\n\n"
                        f"```\n{raw[:500]}\n```",
            "summary": "F14 error: LLM returned non-SQL content",
            "output_path": None,
        }

    ts = _report_ts()
    reports_root = os.path.join("Reports", ts)

    dialect_note = ("PostgreSQL dialect" if dialect == "postgres"
                    else "ANSI generic dialect — review before use on your target DB")

    emit_result = emit_patch(
        agent_key="sql_generator",
        reports_root=reports_root,
        file_path="query.sql",
        new_content=sql.rstrip() + "\n",
        description=f"NL → SQL ({dialect_note}): {nl_prompt[:120]}",
        summary_extras={
            "dialect": dialect,
            "tables_referenced": [t["name"] for t in schema["tables"]
                                  if t["name"].lower() in sql.lower()],
            "rls_policies_applied": [p["name"] for p in schema["policies"]
                                     if p["using"] and
                                     any(tok in sql.lower()
                                         for tok in p["using"].lower().split()
                                         if len(tok) > 3)],
        },
    )

    md_parts = [
        f"## NL → SQL Generator — `query.sql`",
        f"- **Dialect:** {dialect_note}",
        f"- **Prompt:** {nl_prompt[:200]}",
        f"- **Tables referenced:** {len(schema['tables'])}",
        f"- **RLS policies present:** {len(schema['policies'])}",
        f"- **Output:** `{emit_result['paths']['content']}`",
        f"\n### Generated SQL\n\n```sql\n{sql.rstrip()}\n```",
    ]
    if dialect != "postgres":
        md_parts.append("\n> **Note:** non-PostgreSQL dialect — verify syntax "
                        "against your target database before use.")

    markdown = "\n".join(md_parts)
    summary = f"F14 generated {dialect} SQL for prompt of {len(nl_prompt)} chars."

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": emit_result["paths"]["content"],
        "dialect": dialect,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
