from agents.sql_generator import run_sql_generator


def test_stub_returns_placeholder_markdown(test_db):
    result = run_sql_generator(
        conn=test_db,
        job_id="test-job-1",
        file_path="schema.sql",
        content="CREATE TABLE t (id int);",
        file_hash="fakehash",
        language="postgres",
        custom_prompt="__prompt__\nselect all rows",
    )
    assert "markdown" in result
    assert "summary" in result
    assert "SQL" in result["markdown"]
