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
                os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
                _connection = duckdb.connect(settings.db_path)
    return _connection


def reset_connection():
    global _connection
    with _lock:
        if _connection:
            _connection.close()
        _connection = None
