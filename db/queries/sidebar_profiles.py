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


def save_profile(conn: duckdb.DuckDBPyConnection, name: str,
                 source_type: str | None, features: list[str],
                 language: str | None, custom_prompt: str | None,
                 extra_instructions: str | None,
                 mermaid_type: str = "flowchart") -> str:
    """Insert or replace a sidebar profile by name. Returns the profile id."""
    # Check if a profile with this name already exists
    row = conn.execute(
        "SELECT id FROM sidebar_profiles WHERE name = ?", [name]
    ).fetchone()

    if row:
        profile_id = row[0]
        conn.execute(
            """UPDATE sidebar_profiles
               SET source_type=?, features=?, language=?, custom_prompt=?,
                   extra_instructions=?, mermaid_type=?, updated_at=now()
               WHERE id=?""",
            [source_type, features, language, custom_prompt,
             extra_instructions, mermaid_type, profile_id],
        )
    else:
        profile_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO sidebar_profiles
               (id, name, source_type, features, language,
                custom_prompt, extra_instructions, mermaid_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [profile_id, name, source_type, features, language,
             custom_prompt, extra_instructions, mermaid_type],
        )
    return profile_id


def list_profiles(conn: duckdb.DuckDBPyConnection) -> list[dict]:
    """Return all sidebar profiles ordered by name."""
    result = conn.execute(
        "SELECT * FROM sidebar_profiles ORDER BY name"
    )
    cols = [d[0] for d in result.description]
    return [dict(zip(cols, row)) for row in result.fetchall()]


def get_profile(conn: duckdb.DuckDBPyConnection, name: str) -> dict | None:
    """Return a single profile by name, or None if not found."""
    result = conn.execute(
        "SELECT * FROM sidebar_profiles WHERE name = ?", [name]
    )
    cols = [d[0] for d in result.description]
    row = result.fetchone()
    return dict(zip(cols, row)) if row else None


def delete_profile(conn: duckdb.DuckDBPyConnection, profile_id: str) -> None:
    """Delete a profile by id."""
    conn.execute("DELETE FROM sidebar_profiles WHERE id = ?", [profile_id])
