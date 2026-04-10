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
