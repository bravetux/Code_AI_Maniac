from unittest.mock import patch
from agents.orchestrator import run_analysis


def test_orchestrator_runs_selected_features(test_db):
    from db.queries.jobs import create_job
    job_id = create_job(test_db, source_type="local", source_ref="test.py",
                        language="Python", features=["bug_analysis", "mermaid"])

    mock_bug_result = {"bugs": [], "summary": "No bugs."}
    mock_mermaid_result = {"diagram_type": "flowchart", "mermaid_source": "flowchart LR\nA-->B", "description": "test"}

    with patch("agents.orchestrator.run_bug_analysis", return_value=mock_bug_result) as mock_bug, \
         patch("agents.orchestrator.run_mermaid", return_value=mock_mermaid_result) as mock_mermaid, \
         patch("agents.orchestrator._fetch_content", return_value=("content", "hash")):
        results = run_analysis(conn=test_db, job_id=job_id)

    mock_bug.assert_called_once()
    mock_mermaid.assert_called_once()
    assert "bug_analysis" in results
    assert "mermaid" in results


def test_orchestrator_updates_job_status(test_db):
    from db.queries.jobs import create_job, get_job
    job_id = create_job(test_db, source_type="local", source_ref="test.py",
                        language="Python", features=["code_design"])

    with patch("agents.orchestrator.run_code_design", return_value={"markdown": "# Doc", "title": "test"}), \
         patch("agents.orchestrator._fetch_content", return_value=("content", "hash")):
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

    with patch("agents.orchestrator.run_bug_analysis") as mock_bug, \
         patch("agents.orchestrator.run_code_design",
               return_value={"markdown": "# Doc", "title": "test"}) as mock_design, \
         patch("agents.orchestrator._fetch_content", return_value=("content", "hash")):
        results = run_analysis(conn=test_db, job_id=job_id)

    mock_bug.assert_not_called()        # disabled — must be skipped
    mock_design.assert_called_once()    # enabled — must run
    assert "code_design" in results
    assert "bug_analysis" not in results

    get_settings.cache_clear()  # restore default for subsequent tests


def test_orchestrator_all_disabled_completes_empty(test_db, monkeypatch):
    """If enabled agents don't overlap with job features, job completes with no results."""
    from config.settings import get_settings
    from db.queries.jobs import create_job, get_job
    monkeypatch.setenv("ENABLED_AGENTS", "commit_analysis")
    get_settings.cache_clear()

    job_id = create_job(test_db, source_type="local", source_ref="test.py",
                        language="Python", features=["bug_analysis", "code_design"])

    with patch("agents.orchestrator._fetch_content", return_value=("content", "hash")):
        results = run_analysis(conn=test_db, job_id=job_id)

    job = get_job(test_db, job_id)
    assert job["status"] == "completed"
    assert "bug_analysis" not in results
    assert "code_design" not in results

    get_settings.cache_clear()
