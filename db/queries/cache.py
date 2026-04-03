import uuid
import json
import duckdb


def get_cached_result(conn: duckdb.DuckDBPyConnection, file_hash: str,
                      feature: str, language: str | None) -> dict | None:
    row = conn.execute(
        """SELECT result_json FROM results_cache
           WHERE file_hash = ? AND feature = ? AND language IS NOT DISTINCT FROM ?
           ORDER BY created_at DESC LIMIT 1""",
        [file_hash, feature, language]
    ).fetchone()
    if not row:
        return None
    val = row[0]
    return json.loads(val) if isinstance(val, str) else val


def store_result(conn: duckdb.DuckDBPyConnection, job_id: str, feature: str,
                 file_hash: str, language: str | None, result: dict) -> str:
    cache_id = str(uuid.uuid4())
    conn.execute(
        """INSERT INTO results_cache (id, job_id, feature, file_hash, language, result_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [cache_id, job_id, feature, file_hash, language, json.dumps(result)]
    )
    return cache_id
