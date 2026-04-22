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
    "code_complexity",
    "test_coverage",
    "duplication_detection",
    "performance_analysis",
    "type_safety",
    "architecture_mapper",
    "license_compliance",
    "change_impact",
    "refactoring_advisor",
    "api_doc_generator",
    "doxygen",
    "c_test_generator",
    "commit_analysis",
    "release_notes",
    "developer_activity",
    "commit_hygiene",
    "churn_analysis",
    "secret_scan",
    "dependency_analysis",
    "threat_model",
    # Phase 5 — Quick wins
    "unit_test_generator",      # F1
    "story_test_generator",     # F2
    "gherkin_generator",        # F3
    "test_data_generator",      # F8
    "dead_code_detector",       # F17
    "api_contract_checker",     # F24
    "openapi_generator",        # F37
    # F20 (CI/CD webhook) and F21 (pre-commit reviewer) are CLI/server tools
    # — they do not run as per-file agents in the orchestrator.
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

    # ── Report generation ────────────────────────────────────────────────────
    report_per_file: bool = True
    report_consolidated: bool = True
    report_format_md: bool = True
    report_format_html: bool = True
    consolidated_mode: str = Field(default="hybrid", pattern=r"^(hybrid|llm|template)$")

    # ── Security testing ─────────────────────────────────────────────────────
    secret_scan_mode: str = Field(default="warn", pattern=r"^(block|redact|warn)$")
    sca_cve_backend: str = Field(default="osv_llm", pattern=r"^(osv|nvd|github|llm|osv_llm)$")
    sca_auto_discover: bool = True
    nvd_api_key: str = ""

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
