import duckdb
from config.settings import get_settings
import os

_connection = None

def get_connection():
    global _connection
    if _connection is None:
        s = get_settings()
        os.makedirs(os.path.dirname(s.db_path), exist_ok=True)
        _connection = duckdb.connect(s.db_path)
    return _connection

def reset_connection():
    global _connection
    if _connection:
        _connection.close()
    _connection = None
