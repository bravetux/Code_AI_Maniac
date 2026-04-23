from agents.auto_fix_agent import run_auto_fix_agent


def test_stub_returns_placeholder_markdown(test_db):
    result = run_auto_fix_agent(
        conn=test_db,
        job_id="test-job-1",
        file_path="buggy.py",
        content="def foo():\n    pass\n",
        file_hash="fakehash",
        language="python",
        custom_prompt=None,
    )
    assert "markdown" in result
    assert "summary" in result
    assert "Auto-Fix" in result["markdown"]
