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
