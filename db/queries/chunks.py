import uuid
import duckdb


def store_chunks(conn: duckdb.DuckDBPyConnection, job_id: str,
                 file_path: str, chunks: list[dict]) -> None:
    for chunk in chunks:
        conn.execute(
            """INSERT INTO file_chunks (id, job_id, file_path, chunk_index,
               start_line, end_line, content, token_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [str(uuid.uuid4()), job_id, file_path, chunk.get("chunk_index", 0),
             chunk.get("start_line"), chunk.get("end_line"),
             chunk["content"], chunk.get("token_count", 0)]
        )


def get_chunks(conn: duckdb.DuckDBPyConnection, job_id: str,
               file_path: str) -> list[dict]:
    rows = conn.execute(
        """SELECT chunk_index, start_line, end_line, content, token_count
           FROM file_chunks WHERE job_id = ? AND file_path = ?
           ORDER BY chunk_index""",
        [job_id, file_path]
    ).fetchall()
    cols = ["chunk_index", "start_line", "end_line", "content", "token_count"]
    return [dict(zip(cols, r)) for r in rows]
