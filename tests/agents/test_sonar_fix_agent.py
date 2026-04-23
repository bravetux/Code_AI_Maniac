from agents.sonar_fix_agent import run_sonar_fix_agent


def test_stub_returns_placeholder_markdown(test_db):
    result = run_sonar_fix_agent(
        conn=test_db,
        job_id="test-job-1",
        file_path="sonar_issues.json",
        content='{"issues": []}',
        file_hash="fakehash",
        language=None,
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Sonar" in result["markdown"] or "SonarQube" in result["markdown"]
