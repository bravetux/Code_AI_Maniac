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
