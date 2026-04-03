import duckdb
import os
from config.settings import get_settings

_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    global _connection
    if _connection is None:
        settings = get_settings()
        os.makedirs(os.path.dirname(settings.db_path), exist_ok=True)
        _connection = duckdb.connect(settings.db_path)
    return _connection


def reset_connection():
    global _connection
    if _connection:
        _connection.close()
    _connection = None
