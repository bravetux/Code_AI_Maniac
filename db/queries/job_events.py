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
