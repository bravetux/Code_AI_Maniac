import pytest
from pydantic import ValidationError


def test_settings_defaults(test_settings):
    assert test_settings.aws_region == "us-east-1"
    assert test_settings.bedrock_temperature == 0.3
    assert test_settings.bedrock_model_id == "anthropic.claude-3-5-sonnet-20241022-v2:0"


def test_settings_temperature_valid_range(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("BEDROCK_TEMPERATURE", "0.7")
    get_settings.cache_clear()
    s = get_settings()
    assert s.bedrock_temperature == 0.7


def test_settings_temperature_out_of_range(monkeypatch):
    from config.settings import get_settings, Settings
    with pytest.raises(ValidationError):
        Settings(bedrock_temperature=1.5)


def test_settings_temperature_negative(monkeypatch):
    from config.settings import Settings
    with pytest.raises(ValidationError):
        Settings(bedrock_temperature=-0.1)


def test_settings_max_files_default(test_settings):
    assert test_settings.max_files == 50


def test_settings_max_files_custom(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("MAX_FILES", "10")
    get_settings.cache_clear()
    s = get_settings()
    assert s.max_files == 10


def test_settings_max_files_out_of_range():
    from config.settings import Settings
    with pytest.raises(ValidationError):
        Settings(max_files=0)
    with pytest.raises(ValidationError):
        Settings(max_files=101)


def test_enabled_agents_default_is_all(test_settings):
    from config.settings import ALL_AGENTS
    assert test_settings.enabled_agent_set == ALL_AGENTS


def test_enabled_agents_all_keyword(monkeypatch):
    from config.settings import get_settings, ALL_AGENTS
    for val in ("all", "ALL", "*", ""):
        monkeypatch.setenv("ENABLED_AGENTS", val)
        get_settings.cache_clear()
        assert get_settings().enabled_agent_set == ALL_AGENTS
    get_settings.cache_clear()


def test_enabled_agents_subset(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("ENABLED_AGENTS", "bug_analysis,static_analysis,comment_generator")
    get_settings.cache_clear()
    s = get_settings()
    assert s.enabled_agent_set == frozenset({"bug_analysis", "static_analysis", "comment_generator"})
    get_settings.cache_clear()


def test_enabled_agents_unknown_keys_silently_dropped(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("ENABLED_AGENTS", "bug_analysis,nonexistent_agent")
    get_settings.cache_clear()
    s = get_settings()
    assert s.enabled_agent_set == frozenset({"bug_analysis"})
    get_settings.cache_clear()


def test_enabled_agents_whitespace_tolerant(monkeypatch):
    from config.settings import get_settings
    monkeypatch.setenv("ENABLED_AGENTS", " bug_analysis , code_design ")
    get_settings.cache_clear()
    s = get_settings()
    assert "bug_analysis" in s.enabled_agent_set
    assert "code_design" in s.enabled_agent_set
    get_settings.cache_clear()
