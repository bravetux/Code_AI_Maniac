import os as _os_lib
import pathlib
from unittest.mock import patch, MagicMock

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


from agents.sql_generator import _resolve_schema, _build_schema_summary, _pick_dialect


def _project_root():
    cur = pathlib.Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            return parent
    return pathlib.Path.cwd()


def test_pick_dialect_postgres_aliases():
    for lang in ("postgres", "postgresql", "pgsql", "POSTGRES"):
        assert _pick_dialect(lang) == "postgres"


def test_pick_dialect_fallback():
    for lang in (None, "", "mysql", "oracle", "anything"):
        assert _pick_dialect(lang) == "generic"


def test_resolve_schema_from_prefix():
    prompt = "__db_schema__\nCREATE TABLE t (id INT PRIMARY KEY);"
    schema = _resolve_schema(file_path="ignored", content="", custom_prompt=prompt)
    assert len(schema["tables"]) == 1


def test_resolve_schema_from_source_sql_file():
    content = "CREATE TABLE t (id INT PRIMARY KEY);"
    schema = _resolve_schema(file_path="schema.sql", content=content, custom_prompt=None)
    assert len(schema["tables"]) == 1


def test_build_schema_summary_includes_tables_and_rls():
    schema = {
        "tables": [
            {"name": "users", "columns": [
                {"name": "id", "type": "INT", "nullable": False, "default": None,
                 "pk": True, "fk": None},
                {"name": "tenant_id", "type": "INT", "nullable": False, "default": None,
                 "pk": False, "fk": {"ref_table": "tenants", "ref_col": "id"}},
            ]},
        ],
        "views": [],
        "policies": [{"name": "iso", "table": "users", "command": "SELECT",
                      "using": "tenant_id = current_setting('x')::int", "check": ""}],
    }
    summary = _build_schema_summary(schema)
    assert "users" in summary
    assert "tenant_id" in summary
    assert "FK→tenants.id" in summary or "tenants(id)" in summary
    assert "iso" in summary and "SELECT" in summary


def test_f14_writes_sql_with_rls(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = _project_root()
    schema_sql = (root / "tests/fixtures/wave6b/sql/multi_tenant_schema.sql").read_text(encoding="utf-8")
    prompt_text = (root / "tests/fixtures/wave6b/sql/order_report_prompt.txt").read_text(encoding="utf-8")
    canned = (root / "tests/fixtures/wave6b/sql/canned_llm.txt").read_text(encoding="utf-8")

    with patch("agents.sql_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = canned
        mock_cls.return_value = mock_agent
        result = run_sql_generator(
            conn=test_db, job_id="j1",
            file_path="multi_tenant_schema.sql",
            content=schema_sql,
            file_hash="h1", language="postgres",
            custom_prompt=f"__prompt__\n{prompt_text}",
        )

    assert result.get("output_path") and result["output_path"].endswith("query.sql")
    sql = open(result["output_path"], "r", encoding="utf-8").read()
    assert "current_setting" in sql
    assert "orders" in sql.lower()


def test_f14_errors_without_prompt(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("agents.sql_generator.Agent") as mock_cls:
        result = run_sql_generator(
            conn=test_db, job_id="j2",
            file_path="schema.sql",
            content="CREATE TABLE t (id INT);",
            file_hash="h2", language="postgres", custom_prompt=None,
        )
        mock_cls.assert_not_called()
    assert result.get("output_path") is None
    assert "error" in result["summary"].lower() or "prompt" in result["summary"].lower()


def test_f14_errors_without_schema(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("agents.sql_generator.Agent") as mock_cls:
        result = run_sql_generator(
            conn=test_db, job_id="j3",
            file_path="plain.txt",
            content="no schema here",
            file_hash="h3", language="postgres",
            custom_prompt="__prompt__\nselect something",
        )
        mock_cls.assert_not_called()
    assert result.get("output_path") is None


def test_f14_non_postgres_emits_generic_note(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    canned = "```sql\nSELECT 1;\n```"
    with patch("agents.sql_generator.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = canned
        mock_cls.return_value = mock_agent
        result = run_sql_generator(
            conn=test_db, job_id="j4",
            file_path="schema.sql",
            content="CREATE TABLE t (id INT PRIMARY KEY);",
            file_hash="h4", language="mysql",
            custom_prompt="__prompt__\nget everything",
        )
    assert result.get("output_path")
    assert "generic" in result["markdown"].lower() or "review" in result["markdown"].lower()
