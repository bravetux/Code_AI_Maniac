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

from unittest.mock import patch
from agents.orchestrator import run_analysis

# Stub returned by the patched _fetch_files — a single-file list
_FAKE_FILES = [{"file_path": "test.py", "content": "content", "file_hash": "hash"}]


def test_orchestrator_runs_selected_features(test_db):
    from db.queries.jobs import create_job
    job_id = create_job(test_db, source_type="local", source_ref="test.py",
                        language="Python", features=["bug_analysis", "mermaid"])

    mock_bug_result     = {"bugs": [], "summary": "No bugs."}
    mock_mermaid_result = {"diagram_type": "flowchart",
                           "mermaid_source": "flowchart LR\nA-->B",
                           "description": "test"}

    with patch("agents.orchestrator._fetch_files", return_value=_FAKE_FILES), \
         patch("agents.orchestrator.run_bug_analysis", return_value=mock_bug_result) as mock_bug, \
         patch("agents.orchestrator.run_mermaid", return_value=mock_mermaid_result) as mock_mermaid:
        results = run_analysis(conn=test_db, job_id=job_id)

    mock_bug.assert_called_once()
    mock_mermaid.assert_called_once()
    assert "bug_analysis" in results
    assert "mermaid" in results


def test_orchestrator_updates_job_status(test_db):
    from db.queries.jobs import create_job, get_job
    job_id = create_job(test_db, source_type="local", source_ref="test.py",
                        language="Python", features=["code_design"])

    with patch("agents.orchestrator._fetch_files", return_value=_FAKE_FILES), \
         patch("agents.orchestrator.run_code_design",
               return_value={"markdown": "# Doc", "title": "test"}):
        run_analysis(conn=test_db, job_id=job_id)

    job = get_job(test_db, job_id)
    assert job["status"] == "completed"


def test_orchestrator_skips_disabled_agents(test_db, monkeypatch):
    """Agents not in ENABLED_AGENTS must never be called, even if in the job."""
    from config.settings import get_settings
    from db.queries.jobs import create_job
    monkeypatch.setenv("ENABLED_AGENTS", "code_design")
    get_settings.cache_clear()

    job_id = create_job(test_db, source_type="local", source_ref="test.py",
                        language="Python", features=["bug_analysis", "code_design"])

    with patch("agents.orchestrator._fetch_files", return_value=_FAKE_FILES), \
         patch("agents.orchestrator.run_bug_analysis") as mock_bug, \
         patch("agents.orchestrator.run_code_design",
               return_value={"markdown": "# Doc", "title": "test"}) as mock_design:
        results = run_analysis(conn=test_db, job_id=job_id)

    mock_bug.assert_not_called()
    mock_design.assert_called_once()
    assert "code_design" in results
    assert "bug_analysis" not in results

    get_settings.cache_clear()


def test_orchestrator_all_disabled_completes_empty(test_db, monkeypatch):
    """If enabled agents don't overlap with job features, job completes with no results."""
    from config.settings import get_settings
    from db.queries.jobs import create_job, get_job
    monkeypatch.setenv("ENABLED_AGENTS", "commit_analysis")
    get_settings.cache_clear()

    job_id = create_job(test_db, source_type="local", source_ref="test.py",
                        language="Python", features=["bug_analysis", "code_design"])

    with patch("agents.orchestrator._fetch_files", return_value=_FAKE_FILES):
        results = run_analysis(conn=test_db, job_id=job_id)

    job = get_job(test_db, job_id)
    assert job["status"] == "completed"
    assert "bug_analysis" not in results
    assert "code_design" not in results

    get_settings.cache_clear()


def test_orchestrator_multi_file(test_db):
    """Multi-file source_ref produces _multi_file results."""
    from db.queries.jobs import create_job
    job_id = create_job(test_db, source_type="local",
                        source_ref="a.py::b.py",
                        language="Python", features=["bug_analysis"])

    fake_files = [
        {"file_path": "a.py", "content": "x=1", "file_hash": "hash_a"},
        {"file_path": "b.py", "content": "y=2", "file_hash": "hash_b"},
    ]
    mock_bug = {"bugs": [], "summary": "No bugs."}

    with patch("agents.orchestrator._fetch_files", return_value=fake_files), \
         patch("agents.orchestrator.run_bug_analysis", return_value=mock_bug):
        results = run_analysis(conn=test_db, job_id=job_id)

    assert results["bug_analysis"]["_multi_file"] is True
    assert "a.py" in results["bug_analysis"]["files"]
    assert "b.py" in results["bug_analysis"]["files"]
