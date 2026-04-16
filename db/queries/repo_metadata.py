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
from datetime import datetime, timezone


def upsert_repo(conn: duckdb.DuckDBPyConnection, source_type: str,
                repo_url: str, branch: str, commit_count: int,
                file_tree: dict) -> str:
    existing = conn.execute(
        "SELECT id FROM repo_metadata WHERE repo_url = ? AND branch = ?",
        [repo_url, branch]
    ).fetchone()
    if existing:
        repo_id = existing[0]
        conn.execute(
            """UPDATE repo_metadata SET last_synced = ?, commit_count = ?, file_tree = ?
               WHERE id = ?""",
            [datetime.now(timezone.utc), commit_count, json.dumps(file_tree), repo_id]
        )
    else:
        repo_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO repo_metadata (id, source_type, repo_url, branch,
               last_synced, commit_count, file_tree)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [repo_id, source_type, repo_url, branch,
             datetime.now(timezone.utc), commit_count, json.dumps(file_tree)]
        )
    return repo_id


def store_commit(conn: duckdb.DuckDBPyConnection, repo_id: str,
                 commit_sha: str, author: str, message: str,
                 diff_summary: str, files_changed: list[str]) -> str:
    commit_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO commit_snapshots
           (id, repo_id, commit_sha, author, message, diff_summary, files_changed)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT (repo_id, commit_sha) DO NOTHING""",
        [commit_id, repo_id, commit_sha, author, message, diff_summary, files_changed]
    )
    return commit_id


def list_commits(conn: duckdb.DuckDBPyConnection, repo_id: str,
                 limit: int = 100) -> list[dict]:
    result = conn.execute(
        """SELECT * FROM commit_snapshots WHERE repo_id = ?
           ORDER BY created_at DESC LIMIT ?""",
        [repo_id, limit]
    )
    cols = [d[0] for d in result.description]
    rows = result.fetchall()
    return [dict(zip(cols, r)) for r in rows]
