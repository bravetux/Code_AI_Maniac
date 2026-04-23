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

"""F8 — Test Data Generator.

Generates synthetic, rule-based, boundary, negative, and PII-safe rows from a
schema inferred from the source code (model / DDL / DTO / Pydantic / JPA /
protobuf, etc.) OR supplied directly.

Outputs CSV + JSON + a single INSERT-style SQL snippet.
"""

import csv
import io
import json
import os
import re
from datetime import datetime
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "test_data_generator"


_SYSTEM_PROMPT = """You are a test-data engineer generating synthetic datasets.

Given source code (a model / DTO / Pydantic class / JPA entity / TypeScript
interface / SQL DDL / protobuf, etc.) OR an explicit schema, produce a JSON
document with this exact shape:

{
  "entity": "<best guess at the entity name>",
  "fields": [
    {"name": "...", "type": "string|int|float|bool|date|datetime|uuid|enum|json", "pii": false, "notes": "..."}
  ],
  "rows": [
    {"<field>": <value>, ...}
  ]
}

Rules:
- Emit between 20 and 40 rows total, spread across buckets: typical (~50%),
  boundary (min/max/empty/zero, ~25%), negative/invalid (~15%), unicode / edge
  charsets (~10%).
- Mark any field that could hold personally identifiable information with
  `"pii": true`. For PII fields, ALWAYS use fake-but-plausible values. Never
  reuse real names, emails, phone numbers, SSNs, addresses, or card numbers.
  Use obvious fakes: `jane.doe+{i}@example.test`, `+1-555-0199`, `TEST-SSN-###`.
- Use ISO-8601 for dates and datetimes.
- For enum fields, respect the declared enum members exactly.
- For invalid rows, include at least one per validation rule you can identify
  (required-but-null, wrong type, out-of-range, pattern violation).

Return STRICT JSON only. No code fences, no commentary.
"""


def _rows_to_csv(rows: list[dict], fields: list[dict]) -> str:
    if not rows:
        return ""
    field_names = [f["name"] for f in fields] if fields else list(rows[0].keys())
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=field_names, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                    for k, v in r.items()})
    return buf.getvalue()


def _rows_to_sql(entity: str, rows: list[dict], fields: list[dict]) -> str:
    if not rows:
        return ""
    table = re.sub(r"[^\w]+", "_", (entity or "test_table")).strip("_").lower() or "test_table"
    cols = [f["name"] for f in fields] if fields else list(rows[0].keys())
    out = [f"-- Generated synthetic rows for {table}"]
    for r in rows:
        vals = []
        for c in cols:
            v = r.get(c)
            if v is None:
                vals.append("NULL")
            elif isinstance(v, bool):
                vals.append("TRUE" if v else "FALSE")
            elif isinstance(v, (int, float)):
                vals.append(str(v))
            else:
                esc = str(v).replace("'", "''")
                vals.append(f"'{esc}'")
        out.append(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(vals)});")
    return "\n".join(out)


def run_test_data_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    prompt = (f"Generate synthetic test data for the schema defined in this "
              f"source. Infer the entity and fields.\n\n"
              f"File: {file_path}\nLanguage: {language or 'auto'}\n\n"
              f"```\n{content}\n```")
    raw = str(agent(prompt))
    try:
        payload = parse_json_response(raw)
    except Exception:
        payload = {"entity": "unknown", "fields": [], "rows": [], "_raw": raw}

    entity = payload.get("entity") or os.path.splitext(os.path.basename(file_path))[0]
    fields = payload.get("fields") or []
    rows = payload.get("rows") or []

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "test_data")
    os.makedirs(out_dir, exist_ok=True)
    safe_entity = re.sub(r"[^\w\-]+", "_", entity) or "data"

    csv_text = _rows_to_csv(rows, fields)
    sql_text = _rows_to_sql(entity, rows, fields)

    csv_path = os.path.join(out_dir, f"{safe_entity}.csv")
    json_path = os.path.join(out_dir, f"{safe_entity}.json")
    sql_path = os.path.join(out_dir, f"{safe_entity}.sql")

    if csv_text:
        with open(csv_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(csv_text)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, default=str)
    if sql_text:
        with open(sql_path, "w", encoding="utf-8") as fh:
            fh.write(sql_text)

    pii_fields = [f["name"] for f in fields if f.get("pii")]

    md_parts = [
        f"## Test Data Generator — `{os.path.basename(file_path)}`",
        f"- **Entity:** `{entity}`",
        f"- **Fields:** {len(fields)}" + (f" (PII: {', '.join(pii_fields)})" if pii_fields else ""),
        f"- **Rows generated:** {len(rows)}",
        f"- **Saved:** `{csv_path}`, `{json_path}`, `{sql_path}`\n",
    ]
    if fields:
        md_parts.append("### Schema")
        md_parts.append("| Field | Type | PII | Notes |")
        md_parts.append("|---|---|---|---|")
        for f in fields:
            md_parts.append(
                f"| {f.get('name', '')} | {f.get('type', '')} | "
                f"{'yes' if f.get('pii') else ''} | {(f.get('notes') or '').replace('|', '\\|')} |"
            )
    if csv_text:
        md_parts.append("\n### CSV preview")
        md_parts.append(f"```csv\n{csv_text[:4000]}\n```")
    if sql_text:
        md_parts.append("\n### SQL snippet")
        md_parts.append(f"```sql\n{sql_text[:4000]}\n```")

    markdown = "\n".join(md_parts)
    summary = f"Generated {len(rows)} synthetic row(s) for entity `{entity}`."

    result = {
        "markdown": markdown,
        "summary": summary,
        "entity": entity,
        "fields": fields,
        "rows": rows,
        "csv_path": csv_path,
        "json_path": json_path,
        "sql_path": sql_path,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
