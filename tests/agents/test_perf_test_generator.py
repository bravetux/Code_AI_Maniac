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
    from db.queries.jobs import create_job
    from agents.orchestrator import run_analysis
    job_id = create_job(test_db, source_type="local",
                        source_ref="tests/fixtures/wave6a/petstore_openapi.yaml",
                        language="java",
                        features=["perf_test_generator"])
    run_analysis(test_db, job_id)
