from agents.perf_test_generator import run_perf_test_generator


def test_stub_returns_placeholder_markdown(test_db):
    result = run_perf_test_generator(
        conn=test_db,
        job_id="test-job-1",
        file_path="openapi.yaml",
        content="openapi: 3.0.0\ninfo: {title: t, version: '0.1'}\npaths: {}\n",
        file_hash="fakehash",
        language="java",
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Perf" in result["markdown"] or "Performance" in result["markdown"]


def test_orchestrator_dispatches_perf_test_generator(test_db):
    from db.queries.jobs import create_job, get_job, get_job_results
    from db.queries.job_events import get_events
    from agents.orchestrator import run_analysis
    job_id = create_job(test_db, source_type="local",
                        source_ref="tests/fixtures/wave6a/petstore_openapi.yaml",
                        language="java",
                        features=["perf_test_generator"])
    run_analysis(test_db, job_id)
    job = get_job(test_db, job_id)
    assert job is not None
    assert job["status"] in ("completed", "failed"), f"unexpected status: {job['status']}"
    results = get_job_results(test_db, job_id) or {}
    events = get_events(test_db, job_id)
    assert len(events) > 0, "expected at least one job_events row for the dispatch"
    dispatch_trace = str(results) + " " + " ".join(str(e) for e in events)
    assert "perf_test_generator" in dispatch_trace, \
        f"dispatch did not produce a result for perf_test_generator: results={results!r} events={events!r}"
