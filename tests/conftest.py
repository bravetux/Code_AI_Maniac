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

import pytest
import duckdb
from config.settings import get_settings
from db.schema import init_schema


@pytest.fixture(autouse=True)
def reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_settings(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_arena.db")
    monkeypatch.setenv("DB_PATH", db_file)
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    monkeypatch.setenv("BEDROCK_TEMPERATURE", "0.3")
    monkeypatch.setenv("MAX_FILES", "50")
    monkeypatch.setenv("ENABLED_AGENTS", "all")
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def test_db(test_settings):
    conn = duckdb.connect(test_settings.db_path)
    init_schema(conn)
    yield conn
    conn.close()
