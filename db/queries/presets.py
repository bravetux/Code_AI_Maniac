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
