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


def store_chunks(conn: duckdb.DuckDBPyConnection, job_id: str,
                 file_path: str, chunks: list[dict]) -> None:
    for chunk in chunks:
        conn.execute(
            """INSERT INTO file_chunks (id, job_id, file_path, chunk_index,
               start_line, end_line, content, token_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [str(uuid.uuid4()), job_id, file_path, chunk.get("chunk_index", 0),
             chunk.get("start_line"), chunk.get("end_line"),
             chunk.get("content"), chunk.get("token_count", 0)]
        )


def get_chunks(conn: duckdb.DuckDBPyConnection, job_id: str,
               file_path: str) -> list[dict]:
    rows = conn.execute(
        """SELECT chunk_index, start_line, end_line, content, token_count
           FROM file_chunks WHERE job_id = ? AND file_path = ?
           ORDER BY chunk_index""",
        [job_id, file_path]
    ).fetchall()
    cols = ["chunk_index", "start_line", "end_line", "content", "token_count"]
    return [dict(zip(cols, r)) for r in rows]
