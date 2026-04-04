import duckdb
import os
import threading
from config.settings import get_settings

_connection: duckdb.DuckDBPyConnection | None = None
_lock = threading.Lock()


def get_connection() -> duckdb.DuckDBPyConnection:
    global _connection
    if _connection is None:
        with _lock:
            if _connection is None:  # double-checked locking
                settings = get_settings()
                db_path = settings.db_path
                os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
                try:
                    _connection = duckdb.connect(db_path)
                except duckdb.IOException as exc:
                    raise RuntimeError(
                        f"Cannot open database '{db_path}'. "
                        "Another process already has it open — stop the other Streamlit "
                        "instance (or other Python process) and restart the app."
                    ) from exc
    return _connection


def reset_connection():
    global _connection
    with _lock:
        if _connection:
            _connection.close()
        _connection = None
