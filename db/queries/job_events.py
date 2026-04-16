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


def add_event(conn: duckdb.DuckDBPyConnection, job_id: str, event_type: str,
              agent: str | None = None, file_path: str | None = None,
              message: str | None = None) -> None:
    """Append a progress event for a job. Called from the background analysis thread."""
    conn.execute(
        """INSERT INTO job_events (id, job_id, event_type, agent, file_path, message)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [str(uuid.uuid4()), job_id, event_type, agent, file_path, message],
    )


def get_events(conn: duckdb.DuckDBPyConnection, job_id: str) -> list[dict]:
    """Return all events for a job in chronological order."""
    rows = conn.execute(
        """SELECT event_type, agent, file_path, message, created_at
           FROM job_events WHERE job_id = ? ORDER BY created_at""",
        [job_id],
    ).fetchall()
    return [
        {"event_type": r[0], "agent": r[1], "file_path": r[2],
         "message": r[3], "created_at": r[4]}
        for r in rows
    ]
