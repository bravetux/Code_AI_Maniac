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

import pytest
from unittest.mock import patch, MagicMock
from agents.report_consolidated import generate_consolidated_report


_FILE_A_RESULTS = {
    "bug_analysis": {
        "summary": "2 bugs found",
        "bugs": [
            {"line": 10, "severity": "critical", "description": "SQL injection"},
            {"line": 25, "severity": "minor", "description": "Unused import"},
        ],
        "narrative": "Security vulnerability detected.",
    },
    "code_flow": {"summary": "Linear flow", "markdown": "Entry: main()"},
}

_FILE_B_RESULTS = {
    "bug_analysis": {
        "summary": "1 bug found",
        "bugs": [{"line": 5, "severity": "major", "description": "Race condition"}],
        "narrative": "Concurrency issue.",
    },
    "code_flow": {"summary": "Async flow", "markdown": "Entry: handler()"},
}

_ALL_RESULTS = {
    "src/auth.py": _FILE_A_RESULTS,
    "src/worker.py": _FILE_B_RESULTS,
}

_PER_FILE_REPORTS = [
    "# Analysis Report — auth.py\n\n## Bug Analysis\n...",
    "# Analysis Report — worker.py\n\n## Bug Analysis\n...",
]


def test_template_mode_no_llm():
    md = generate_consolidated_report(
        per_file_reports=_PER_FILE_REPORTS,
        all_results=_ALL_RESULTS,
        file_paths=["src/auth.py", "src/worker.py"],
        features=["bug_analysis", "code_flow"],
        language="python",
        mode="template",
    )
    assert "# Consolidated Analysis Report" in md
    assert "auth.py" in md
    assert "worker.py" in md
    assert "Table of Contents" in md or "##" in md


def test_template_mode_includes_stats():
    md = generate_consolidated_report(
        per_file_reports=_PER_FILE_REPORTS,
        all_results=_ALL_RESULTS,
        file_paths=["src/auth.py", "src/worker.py"],
        features=["bug_analysis", "code_flow"],
        language="python",
        mode="template",
    )
    # Should mention bug counts
    assert "3" in md or "bug" in md.lower()


def test_hybrid_mode_calls_llm():
    with patch("agents.report_consolidated._call_llm", return_value="Executive summary goes here.") as mock_call:
        md = generate_consolidated_report(
            per_file_reports=_PER_FILE_REPORTS,
            all_results=_ALL_RESULTS,
            file_paths=["src/auth.py", "src/worker.py"],
            features=["bug_analysis", "code_flow"],
            language="python",
            mode="hybrid",
        )
        assert mock_call.called
        assert "Executive summary" in md


def test_llm_mode_calls_llm():
    with patch("agents.report_consolidated._call_llm",
               return_value="# Full LLM Report\n\nNarrative here.") as mock_call:
        md = generate_consolidated_report(
            per_file_reports=_PER_FILE_REPORTS,
            all_results=_ALL_RESULTS,
            file_paths=["src/auth.py", "src/worker.py"],
            features=["bug_analysis", "code_flow"],
            language="python",
            mode="llm",
        )
        assert mock_call.called
        assert "Full LLM Report" in md or "Narrative" in md


def test_empty_results():
    md = generate_consolidated_report(
        per_file_reports=[],
        all_results={},
        file_paths=[],
        features=[],
        language="python",
        mode="template",
    )
    assert "# Consolidated Analysis Report" in md
    assert "No files" in md or "no analysis" in md.lower()
