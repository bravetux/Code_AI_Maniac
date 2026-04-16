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
import json
import duckdb


def get_cached_result(conn: duckdb.DuckDBPyConnection, file_hash: str,
                      feature: str, language: str | None) -> dict | None:
    row = conn.execute(
        """SELECT result_json FROM results_cache
           WHERE file_hash = ? AND feature = ? AND language IS NOT DISTINCT FROM ?
           ORDER BY created_at DESC LIMIT 1""",
        [file_hash, feature, language]
    ).fetchone()
    if not row:
        return None
    val = row[0]
    return json.loads(val) if isinstance(val, str) else val


def store_result(conn: duckdb.DuckDBPyConnection, job_id: str, feature: str,
                 file_hash: str, language: str | None, result: dict) -> str:
    cache_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO results_cache (id, job_id, feature, file_hash, language, result_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [cache_id, job_id, feature, file_hash, language, json.dumps(result)]
    )
    return cache_id
