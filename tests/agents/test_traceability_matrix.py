from agents.traceability_matrix import run_traceability_matrix


def test_stub_returns_placeholder_markdown(test_db):
    result = run_traceability_matrix(
        conn=test_db,
        job_id="test-job-1",
        file_path="story.txt",
        content="As a user I want to reset my password.",
        file_hash="fakehash",
        language=None,
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Traceability" in result["markdown"]


def test_orchestrator_dispatches_traceability_matrix(test_db, tmp_path):
    from db.queries.jobs import create_job, get_job, get_job_results
    from db.queries.job_events import get_events
    from agents.orchestrator import run_analysis
    story = tmp_path / "story.txt"
    story.write_text("As a user I want to reset my password.", encoding="utf-8")
    job_id = create_job(test_db, source_type="local",
                        source_ref=str(story),
                        language=None,
                        features=["traceability_matrix"])
    run_analysis(test_db, job_id)
    job = get_job(test_db, job_id)
    assert job is not None
    assert job["status"] in ("completed", "failed"), f"unexpected status: {job['status']}"
    results = get_job_results(test_db, job_id) or {}
    events = get_events(test_db, job_id)
    assert len(events) > 0, "expected at least one job_events row for the dispatch"
    dispatch_trace = str(results) + " " + " ".join(str(e) for e in events)
    assert "traceability_matrix" in dispatch_trace, \
        f"dispatch did not produce a result for traceability_matrix: results={results!r} events={events!r}"
