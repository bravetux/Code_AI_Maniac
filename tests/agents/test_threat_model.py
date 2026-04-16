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

import json
from unittest.mock import patch, MagicMock
from agents.threat_model import run_threat_model

SAMPLE_CODE = '''
from flask import Flask, request
app = Flask(__name__)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]
    token = create_jwt(username)
    return {"token": token}
'''

MOCK_FORMAL_RESPONSE = json.dumps({
    "mode": "formal",
    "trust_boundaries": [
        {"id": "TB-1", "description": "User input to login handler",
         "components": ["login()"]}
    ],
    "attack_surface": [
        {"entry_point": "POST /login", "exposure": "public",
         "data_handled": "credentials"}
    ],
    "stride_analysis": [
        {
            "id": "T-001",
            "category": "Spoofing",
            "asset": "user session",
            "threat": "Credential stuffing attack",
            "attack_vector": "Automated POST to /login",
            "likelihood": "high",
            "impact": "high",
            "risk_score": "critical",
            "existing_mitigation": "None observed",
            "recommended_mitigation": "Add rate limiting and CAPTCHA",
            "related_findings": [],
        }
    ],
    "data_flow_mermaid": "flowchart LR\n  User-->|POST /login|Server",
    "summary": "1 threat identified: 1 critical",
})

MOCK_ATTACKER_RESPONSE = json.dumps({
    "mode": "attacker",
    "executive_summary": "Login endpoint is vulnerable to credential attacks.",
    "attack_scenarios": [
        {
            "id": "A-001",
            "title": "Credential stuffing via /login",
            "stride_category": "Spoofing",
            "risk_score": "critical",
            "narrative": "Attacker uses leaked credential lists...",
            "prerequisites": "Public endpoint access",
            "impact": "Full account takeover",
            "proof_of_concept": "for cred in leaked_list: post('/login', cred)",
            "mitigation": "Rate limiting, account lockout, CAPTCHA",
            "related_findings": [],
        }
    ],
    "priority_ranking": ["A-001"],
    "summary": "1 attack scenario identified, 1 critical.",
})


def test_run_threat_model_formal_mode(test_db):
    with patch("agents.threat_model.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_FORMAL_RESPONSE
        mock_cls.return_value = mock_agent

        result = run_threat_model(
            conn=test_db, job_id="test-job-1",
            file_path="app.py", content=SAMPLE_CODE,
            file_hash="fakehash", language="Python",
            custom_prompt=None, threat_model_mode="formal",
            bug_results=None, static_results=None,
            secret_results=None, dependency_results=None,
        )

    assert result["mode"] == "formal"
    assert "stride_analysis" in result
    assert len(result["stride_analysis"]) == 1
    assert result["stride_analysis"][0]["category"] == "Spoofing"


def test_run_threat_model_attacker_mode(test_db):
    with patch("agents.threat_model.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_ATTACKER_RESPONSE
        mock_cls.return_value = mock_agent

        result = run_threat_model(
            conn=test_db, job_id="test-job-1",
            file_path="app.py", content=SAMPLE_CODE,
            file_hash="fakehash", language="Python",
            custom_prompt=None, threat_model_mode="attacker",
            bug_results=None, static_results=None,
            secret_results=None, dependency_results=None,
        )

    assert result["mode"] == "attacker"
    assert "attack_scenarios" in result
    assert len(result["attack_scenarios"]) == 1


def test_run_threat_model_uses_cache(test_db):
    from db.queries.jobs import create_job
    from tools.cache import write_cache
    job_id = create_job(test_db, source_type="local", source_ref="f.py",
                        language="Python", features=["threat_model"])
    cached = {"mode": "formal", "stride_analysis": [],
              "summary": "from cache"}
    write_cache(test_db, job_id=job_id, feature="threat_model:v1",
                file_hash="cached_hash", language="Python",
                custom_prompt=None, result=cached)

    with patch("agents.threat_model.Agent") as mock_cls:
        result = run_threat_model(
            conn=test_db, job_id=job_id,
            file_path="f.py", content="x=1",
            file_hash="cached_hash", language="Python",
            custom_prompt=None, threat_model_mode="formal",
            bug_results=None, static_results=None,
            secret_results=None, dependency_results=None,
        )
        mock_cls.assert_not_called()

    assert result["summary"] == "from cache"


def test_run_threat_model_default_mode_is_formal(test_db):
    with patch("agents.threat_model.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = MOCK_FORMAL_RESPONSE
        mock_cls.return_value = mock_agent

        result = run_threat_model(
            conn=test_db, job_id="test-job-1",
            file_path="app.py", content=SAMPLE_CODE,
            file_hash="fakehash2", language="Python",
            custom_prompt=None, threat_model_mode=None,
            bug_results=None, static_results=None,
            secret_results=None, dependency_results=None,
        )

    assert result["mode"] == "formal"
