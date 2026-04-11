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
