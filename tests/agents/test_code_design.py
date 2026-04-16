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
from unittest.mock import patch, MagicMock, call
from agents.code_design import run_code_design

SAMPLE_CODE = """
def fetch_user(user_id):
    conn = get_db()
    return conn.execute(f"SELECT * FROM users WHERE id = {user_id}").fetchone()
"""

MOCK_ANALYSIS = {
    "title": "UserFetcher",
    "purpose": "Fetches a user record from the database by ID.",
    "design_assessment": "Functional but contains a critical SQL injection vulnerability.",
    "responsibilities": ["Fetch user by ID"],
    "design_issues": [
        {
            "issue": "SQL Injection",
            "root_cause": "String interpolation used in SQL query",
            "impact": "Arbitrary SQL execution by attacker",
            "recommendation": "Use parameterised queries",
            "priority": "high",
        }
    ],
    "public_api": [{"name": "fetch_user", "signature": "fetch_user(user_id)", "description": "Returns user row"}],
    "dependencies": ["get_db"],
    "data_contracts": "user_id: int → dict | None",
    "improvements": ["Parameterise SQL query", "Add type hints"],
}

MOCK_DESIGN_DOC = """# UserFetcher — Design Document

## Executive Summary
The UserFetcher module retrieves user records from the database by primary key.

## Architecture Overview
Single function `fetch_user()` that obtains a DB connection and executes a SELECT query.

## Known Issues & Technical Debt
- [HIGH] **SQL Injection**: Use parameterised queries.
"""


def _make_agent_mock(side_effects):
    """Return a patched Agent class whose instance returns side_effects in sequence."""
    mock_instance = MagicMock()
    mock_instance.side_effect = side_effects
    mock_cls = MagicMock(return_value=mock_instance)
    return mock_cls, mock_instance


def test_run_code_design_happy_path(test_db):
    """Three turns complete successfully — design_document and structured fields both present."""
    mock_cls, mock_instance = _make_agent_mock([
        "Structural notes about the code.",          # Turn 1
        json.dumps(MOCK_ANALYSIS),                   # Turn 2
        MOCK_DESIGN_DOC,                             # Turn 3
    ])
    with patch("agents.code_design.Agent", mock_cls):
        result = run_code_design(
            conn=test_db, job_id="job-1",
            file_path="fetch_user.py", content=SAMPLE_CODE,
            file_hash="hash1", language="Python", custom_prompt=None,
        )

    assert mock_instance.call_count == 3
    assert result["design_document"] == MOCK_DESIGN_DOC
    assert result["markdown"] == MOCK_DESIGN_DOC        # backwards compat
    assert result["title"] == "UserFetcher"
    assert isinstance(result["design_issues"], list)
    assert len(result["design_issues"]) == 1
    assert result["improvements"] == ["Parameterise SQL query", "Add type hints"]


def test_run_code_design_with_bug_and_static_context(test_db):
    """Bug and static results are threaded into Turn 2 prompt."""
    mock_cls, mock_instance = _make_agent_mock([
        "Structural notes.",
        json.dumps(MOCK_ANALYSIS),
        MOCK_DESIGN_DOC,
    ])
    bug_results = {
        "bugs": [{"line": 3, "severity": "critical", "description": "SQL injection",
                  "suggestion": "Use params", "github_comment": ""}],
        "narrative": "Critical injection found.",
    }
    static_results = {
        "linter_findings": [],
        "semantic_findings": [{"line": 3, "category": "security", "severity": "critical",
                                "description": "Unsafe query", "suggestion": "Parameterise"}],
    }
    with patch("agents.code_design.Agent", mock_cls):
        result = run_code_design(
            conn=test_db, job_id="job-2",
            file_path="fetch_user.py", content=SAMPLE_CODE,
            file_hash="hash2", language="Python", custom_prompt=None,
            bug_results=bug_results, static_results=static_results,
        )

    # Turn 2 call (index 1) should contain the bug findings
    turn2_prompt = str(mock_instance.call_args_list[1])
    assert "SQL injection" in turn2_prompt or "Critical injection" in turn2_prompt
    assert result["design_document"] == MOCK_DESIGN_DOC


def test_run_code_design_turn2_parse_failure(test_db):
    """If Turn 2 returns non-JSON, Turn 3 is skipped and raw response stored in markdown."""
    mock_cls, mock_instance = _make_agent_mock([
        "Structural notes.",
        "This is NOT valid JSON at all.",   # Turn 2 failure
    ])
    with patch("agents.code_design.Agent", mock_cls):
        result = run_code_design(
            conn=test_db, job_id="job-3",
            file_path="fetch_user.py", content=SAMPLE_CODE,
            file_hash="hash3", language="Python", custom_prompt=None,
        )

    assert mock_instance.call_count == 2    # Turn 3 never called
    assert result["markdown"] == "This is NOT valid JSON at all."
    assert result["design_document"] == ""
    assert result["design_issues"] == []


def test_run_code_design_turn3_failure(test_db):
    """If Turn 3 raises, structured analysis is still present and cache is written."""
    mock_cls, mock_instance = _make_agent_mock([
        "Structural notes.",
        json.dumps(MOCK_ANALYSIS),
        Exception("Bedrock timeout"),       # Turn 3 raises
    ])
    with patch("agents.code_design.Agent", mock_cls):
        result = run_code_design(
            conn=test_db, job_id="job-4",
            file_path="fetch_user.py", content=SAMPLE_CODE,
            file_hash="hash4", language="Python", custom_prompt=None,
        )

    assert result["design_document"] == ""
    assert result["markdown"] == ""
    # Structured fields from Turn 2 still present
    assert result["title"] == "UserFetcher"
    assert len(result["design_issues"]) == 1

    # Cache was written (re-calling with same hash should hit cache, no agent calls)
    mock_cls2, mock_instance2 = _make_agent_mock([])
    with patch("agents.code_design.Agent", mock_cls2):
        cached = run_code_design(
            conn=test_db, job_id="job-4",
            file_path="fetch_user.py", content=SAMPLE_CODE,
            file_hash="hash4", language="Python", custom_prompt=None,
        )
    mock_instance2.assert_not_called()
    assert cached["title"] == "UserFetcher"


def test_run_code_design_uses_cache(test_db):
    """Cache hit — Agent is never instantiated."""
    from tools.cache import write_cache
    from db.queries.jobs import create_job
    job_id = create_job(test_db, source_type="local", source_ref="f.py",
                        language="Python", features=["code_design"])
    cached_result = {
        "title": "Cached", "purpose": "From cache.", "design_assessment": "",
        "responsibilities": [], "design_issues": [], "public_api": [],
        "dependencies": [], "data_contracts": "", "improvements": [],
        "design_document": "# Cached doc", "markdown": "# Cached doc",
    }
    write_cache(test_db, job_id=job_id, feature="code_design",
                file_hash="cached_hash", language="Python",
                custom_prompt=None, result=cached_result)

    mock_cls = MagicMock()
    with patch("agents.code_design.Agent", mock_cls):
        result = run_code_design(
            conn=test_db, job_id=job_id,
            file_path="f.py", content="x = 1",
            file_hash="cached_hash", language="Python", custom_prompt=None,
        )

    mock_cls.assert_not_called()
    assert result["title"] == "Cached"
    assert result["design_document"] == "# Cached doc"
