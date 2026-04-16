# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 12th April 2026

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
