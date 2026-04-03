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
