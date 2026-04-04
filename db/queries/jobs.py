import json
import uuid
from datetime import datetime, timezone
import duckdb


def create_job(conn: duckdb.DuckDBPyConnection, source_type: str, source_ref: str,
               language: str | None, features: list[str],
               custom_prompt: str | None = None) -> str:
    job_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO jobs (id, source_type, source_ref, language, features, custom_prompt)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [job_id, source_type, source_ref, language, features, custom_prompt]
    )
    return job_id


def get_job(conn: duckdb.DuckDBPyConnection, job_id: str) -> dict | None:
    result = conn.execute("SELECT * FROM jobs WHERE id = ?", [job_id])
    cols = [d[0] for d in result.description]
    row = result.fetchone()
    if not row:
        return None
    return dict(zip(cols, row))


def update_job_status(conn: duckdb.DuckDBPyConnection, job_id: str, status: str) -> None:
    completed_at = datetime.now(timezone.utc) if status in ("completed", "failed") else None
    conn.execute(
        "UPDATE jobs SET status = ?, completed_at = ? WHERE id = ?",
        [status, completed_at, job_id]
    )


def save_job_results(conn: duckdb.DuckDBPyConnection, job_id: str, results: dict) -> None:
    conn.execute(
        "UPDATE jobs SET result_json = ? WHERE id = ?",
        [json.dumps(results), job_id]
    )


def get_job_results(conn: duckdb.DuckDBPyConnection, job_id: str) -> dict | None:
    row = conn.execute("SELECT result_json FROM jobs WHERE id = ?", [job_id]).fetchone()
    if not row or row[0] is None:
        return None
    data = row[0]
    if isinstance(data, str):
        return json.loads(data)
    return data


def list_jobs(conn: duckdb.DuckDBPyConnection, limit: int = 50) -> list[dict]:
    result = conn.execute(
        "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", [limit]
    )
    cols = [d[0] for d in result.description]
    rows = result.fetchall()
    return [dict(zip(cols, r)) for r in rows]
