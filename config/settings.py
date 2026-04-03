from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    aws_region: str = "us-east-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_temperature: float = Field(default=0.3, ge=0.0, le=1.0)

    github_token: Optional[str] = None

    gitea_url: str = "http://localhost:3000"
    gitea_token: Optional[str] = None

    db_path: str = "data/arena.db"
    max_files: int = Field(default=50, ge=1, le=100)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
