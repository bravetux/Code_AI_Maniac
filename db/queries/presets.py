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


def create_preset(conn: duckdb.DuckDBPyConnection, name: str, feature: str,
                  system_prompt: str, extra_instructions: str = "") -> str:
    preset_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO prompt_presets (id, name, feature, system_prompt, extra_instructions)
           VALUES (?, ?, ?, ?, ?)""",
        [preset_id, name, feature, system_prompt, extra_instructions]
    )
    return preset_id


def list_presets(conn: duckdb.DuckDBPyConnection, feature: str | None = None) -> list[dict]:
    if feature:
        result = conn.execute(
            "SELECT * FROM prompt_presets WHERE feature = ? ORDER BY name", [feature]
        )
    else:
        result = conn.execute("SELECT * FROM prompt_presets ORDER BY feature, name")
    cols = [d[0] for d in result.description]
    rows = result.fetchall()
    return [dict(zip(cols, r)) for r in rows]


def delete_preset(conn: duckdb.DuckDBPyConnection, preset_id: str) -> None:
    conn.execute("DELETE FROM prompt_presets WHERE id = ?", [preset_id])
