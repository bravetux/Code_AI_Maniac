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
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture
def test_db(test_settings):
    conn = duckdb.connect(test_settings.db_path)
    init_schema(conn)
    yield conn
    conn.close()
