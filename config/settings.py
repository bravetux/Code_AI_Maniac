from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import Optional

# Canonical set of all available agent keys
ALL_AGENTS: frozenset[str] = frozenset({
    "bug_analysis",
    "code_design",
    "code_flow",
    "mermaid",
    "requirement",
    "static_analysis",
    "comment_generator",
    "commit_analysis",
})


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
    bug_context_lines: int = Field(default=5, ge=0, le=20)

    # Comma-separated agent keys, or "all" / "*" / "" to enable everything.
    # Examples:
    #   ENABLED_AGENTS=all
    #   ENABLED_AGENTS=bug_analysis,static_analysis,comment_generator
    #   ENABLED_AGENTS=code_design,requirement,code_flow,mermaid
    enabled_agents: str = "all"

    @property
    def enabled_agent_set(self) -> frozenset[str]:
        """Return the set of enabled agent keys.

        "all", "*", or an empty string → every agent.
        Otherwise parse as a comma-separated list and intersect with ALL_AGENTS
        so typos are silently dropped rather than crashing at runtime.
        """
        val = self.enabled_agents.strip().lower()
        if val in ("all", "*", ""):
            return ALL_AGENTS
        parsed = frozenset(a.strip() for a in val.split(",") if a.strip())
        return parsed & ALL_AGENTS


@lru_cache()
def get_settings() -> Settings:
    return Settings()
