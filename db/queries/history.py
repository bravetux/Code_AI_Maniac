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

import uuid
import duckdb


def add_history(conn: duckdb.DuckDBPyConnection, job_id: str, feature: str,
                source_ref: str, language: str | None, summary: str) -> str:
    hist_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO analysis_history (id, job_id, feature, source_ref, language, summary)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [hist_id, job_id, feature, source_ref, language, summary]
    )
    return hist_id


def list_history(conn: duckdb.DuckDBPyConnection, limit: int = 100) -> list[dict]:
    result = conn.execute(
        "SELECT * FROM analysis_history ORDER BY created_at DESC LIMIT ?", [limit]
    )
    cols = [d[0] for d in result.description]
    rows = result.fetchall()
    return [dict(zip(cols, r)) for r in rows]


def get_history_with_results(conn: duckdb.DuckDBPyConnection,
                             history_ids: list[str]) -> list[dict]:
    """Fetch history rows joined with their job's full result_json."""
    if not history_ids:
        return []
    placeholders = ", ".join("?" for _ in history_ids)
    result = conn.execute(
        f"""SELECT h.id, h.job_id, h.feature, h.source_ref, h.language,
                   h.summary, h.created_at, j.result_json
            FROM analysis_history h
            JOIN jobs j ON j.id = h.job_id
            WHERE h.id IN ({placeholders})
            ORDER BY h.created_at DESC""",
        history_ids,
    )
    cols = [d[0] for d in result.description]
    rows = result.fetchall()
    return [dict(zip(cols, r)) for r in rows]
