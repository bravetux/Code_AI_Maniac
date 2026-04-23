from agents.self_healing_agent import run_self_healing_agent


def test_stub_returns_placeholder_markdown(test_db):
    result = run_self_healing_agent(
        conn=test_db,
        job_id="test-job-1",
        file_path="tests/login_test.py",
        content="# pretend selenium test",
        file_hash="fakehash",
        language="python",
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Self-Healing" in result["markdown"]
