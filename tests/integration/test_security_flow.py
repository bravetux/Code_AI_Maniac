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

"""Smoke test for the security testing pipeline."""

import json
from unittest.mock import patch, MagicMock
from db.queries.jobs import create_job, get_job
from agents.orchestrator import run_analysis


SAMPLE_CODE_WITH_SECRET = '''
import os
AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
password = os.getenv("DB_PASS", "fallback_secret_123")

def connect():
    return {"host": "db.example.com", "password": password}
'''


def test_full_security_pipeline_warn_mode(test_db, monkeypatch):
    """Full pipeline: Phase 0 warn -> Phase 3 deep secret scan -> Phase 4 threat model."""
    monkeypatch.setenv("SECRET_SCAN_MODE", "warn")
    monkeypatch.setenv("ENABLED_AGENTS", "all")

    from config.settings import get_settings
    get_settings.cache_clear()

    job_id = create_job(
        test_db,
        source_type="local",
        source_ref="app.py",
        language="Python",
        features=["secret_scan", "threat_model"],
    )

    mock_secret_response = json.dumps({
        "secrets": [{"line": 4, "type": "hardcoded_fallback", "severity": "major",
                      "description": "Hardcoded fallback in getenv",
                      "evidence": "os.getenv(..., 'fallback_secret_123')",
                      "recommendation": "Remove fallback", "false_positive_risk": "low"}],
        "phase0_validation": [{"line": 3, "phase0_type": "aws_access_key",
                               "verdict": "confirmed", "reason": "Real AWS key format"}],
        "narrative": "Secrets found.", "summary": "1 secret, 1 confirmed.",
    })

    mock_threat_response = json.dumps({
        "mode": "formal",
        "trust_boundaries": [],
        "attack_surface": [{"entry_point": "connect()", "exposure": "internal",
                            "data_handled": "credentials"}],
        "stride_analysis": [{"id": "T-001", "category": "Information Disclosure",
                             "asset": "database password", "threat": "Credential exposure",
                             "attack_vector": "Source code access",
                             "likelihood": "high", "impact": "high",
                             "risk_score": "critical",
                             "existing_mitigation": "None",
                             "recommended_mitigation": "Use secrets manager",
                             "related_findings": ["secret_scan:line_3"]}],
        "data_flow_mermaid": "",
        "summary": "1 critical threat.",
    })

    # Create separate mock agents for each agent call
    mock_secret_agent = MagicMock()
    mock_secret_agent.return_value = mock_secret_response

    mock_threat_agent = MagicMock()
    mock_threat_agent.return_value = mock_threat_response

    agent_calls = iter([mock_secret_agent, mock_threat_agent])

    with patch("agents.secret_scan.Agent", side_effect=lambda **kwargs: next(agent_calls)), \
         patch("agents.threat_model.Agent", side_effect=lambda **kwargs: next(agent_calls, mock_threat_agent)), \
         patch("agents.orchestrator.fetch_local_file",
               return_value={"content": SAMPLE_CODE_WITH_SECRET, "file_hash": "test123"}):
        results = run_analysis(test_db, job_id)

    job = get_job(test_db, job_id)
    assert job["status"] == "completed"
    # At minimum, the job should complete without error
    assert "error" not in results or results.get("error") is None
