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

import os
import pytest
from unittest.mock import patch, MagicMock


def test_report_generation_called_when_enabled(test_db, monkeypatch, tmp_path):
    """Verify orchestrator calls report generation when settings enable it."""
    monkeypatch.setenv("REPORT_PER_FILE", "true")
    monkeypatch.setenv("REPORT_CONSOLIDATED", "false")
    monkeypatch.setenv("REPORT_FORMAT_MD", "true")
    monkeypatch.setenv("REPORT_FORMAT_HTML", "false")

    from config.settings import get_settings
    get_settings.cache_clear()

    from agents.orchestrator import _generate_reports

    per_file_data = [
        ("src/a.py", {"bug_analysis": {"summary": "ok", "bugs": []}}),
    ]
    features = ["bug_analysis"]
    reports_dir = str(tmp_path / "reports")

    mock_emit = MagicMock()

    written = _generate_reports(
        conn=test_db, job_id="test-123", per_file_data=per_file_data,
        features=features, language="python", reports_dir=reports_dir,
        emit_fn=mock_emit,
    )

    assert len(written) > 0
    assert os.path.isdir(os.path.join(reports_dir, "per_file"))


def test_report_generation_skipped_when_disabled(test_db, monkeypatch, tmp_path):
    monkeypatch.setenv("REPORT_PER_FILE", "false")
    monkeypatch.setenv("REPORT_CONSOLIDATED", "false")

    from config.settings import get_settings
    get_settings.cache_clear()

    from agents.orchestrator import _generate_reports

    per_file_data = [
        ("src/a.py", {"bug_analysis": {"summary": "ok", "bugs": []}}),
    ]
    reports_dir = str(tmp_path / "reports")
    mock_emit = MagicMock()

    written = _generate_reports(
        conn=test_db, job_id="test-123", per_file_data=per_file_data,
        features=["bug_analysis"], language="python", reports_dir=reports_dir,
        emit_fn=mock_emit,
    )

    assert written == []
