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
from agents.bug_analysis import run_bug_analysis

SAMPLE_CODE = '''
def divide(a, b):
    return a / b  # no zero check

password = "hardcoded_secret_123"
'''

MOCK_BEDROCK_RESPONSE = {
    "bugs": [
        {
            "line": 3,
            "severity": "major",
            "description": "Division by zero not handled",
            "suggestion": "Add 'if b == 0: raise ValueError' before division",
            "github_comment": "**[Major Bug]** Line 3: Division by zero not handled. Suggestion: Add zero check."
        },
        {
            "line": 5,
            "severity": "critical",
            "description": "Hardcoded secret in source code",
            "suggestion": "Move to environment variable",
            "github_comment": "**[Critical Bug]** Line 5: Hardcoded secret. Move to env var."
        }
    ],
    "summary": "2 bugs found: 1 major, 1 critical."
}


def test_run_bug_analysis_returns_structured_result(test_db):
    with patch("agents.bug_analysis.Agent") as mock_agent_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = json.dumps(MOCK_BEDROCK_RESPONSE)
        mock_agent_cls.return_value = mock_agent

        result = run_bug_analysis(
            conn=test_db,
            job_id="test-job-1",
            file_path="test.py",
            content=SAMPLE_CODE,
            file_hash="fakehash123",
            language="Python",
            custom_prompt=None
        )

    assert "bugs" in result
    assert len(result["bugs"]) == 2
    assert result["bugs"][0]["severity"] == "major"


def test_run_bug_analysis_uses_cache(test_db):
    from db.queries.jobs import create_job
    from tools.cache import write_cache
    job_id = create_job(test_db, source_type="local", source_ref="f.py",
                        language="Python", features=["bug_analysis"])
    cached_result = {"bugs": [{"line": 1, "severity": "minor",
                                "description": "cached", "suggestion": "",
                                "github_comment": ""}],
                     "summary": "from cache"}
    write_cache(test_db, job_id=job_id, feature="bug_analysis",
                file_hash="cached_hash", language="Python",
                custom_prompt=None, result=cached_result)

    with patch("agents.bug_analysis.Agent") as mock_agent_cls:
        result = run_bug_analysis(
            conn=test_db, job_id=job_id,
            file_path="f.py", content="x = 1",
            file_hash="cached_hash", language="Python",
            custom_prompt=None
        )
        mock_agent_cls.assert_not_called()  # no Bedrock call

    assert result["summary"] == "from cache"
