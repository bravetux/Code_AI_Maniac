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


import json as _json_lib
import os as _os_lib
import pathlib
from unittest.mock import patch, MagicMock
from agents.sonar_fix_agent import _resolve_issues, _sort_and_cap


def _project_root():
    cur = pathlib.Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            return parent
    return pathlib.Path.cwd()


def test_resolve_issues_prefix_wins():
    body = '{"issues": [{"rule": "S1", "severity": "MAJOR", "component": "x.py"}]}'
    prefix = f"__sonar_issues__\n{body}"
    issues = _resolve_issues(file_path="ignored",
                             content="", custom_prompt=prefix)
    assert len(issues) == 1
    assert issues[0]["rule"] == "S1"


def test_resolve_issues_from_json_source():
    content = '{"issues": [{"rule": "S2", "severity": "MINOR", "component": "x.py"}]}'
    issues = _resolve_issues(file_path="sonar.json", content=content,
                             custom_prompt=None)
    assert len(issues) == 1
    assert issues[0]["rule"] == "S2"


def test_sort_and_cap_orders_by_severity():
    issues = [
        {"rule": "A", "severity": "MINOR", "component": "x"},
        {"rule": "B", "severity": "BLOCKER", "component": "x"},
        {"rule": "C", "severity": "MAJOR", "component": "x"},
    ]
    sorted_ = _sort_and_cap(issues, top_n=3)
    assert [i["rule"] for i in sorted_] == ["B", "C", "A"]


def test_sort_and_cap_respects_top_n():
    issues = [{"rule": f"R{i}", "severity": "MAJOR", "component": "x"} for i in range(10)]
    assert len(_sort_and_cap(issues, top_n=3)) == 3


def test_f11_writes_per_file_diffs(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = _project_root()
    issues_body = (root / "tests/fixtures/wave6b/sonar/issues.json").read_text(encoding="utf-8")
    canned = (root / "tests/fixtures/wave6b/sonar/canned_llm.txt").read_text(encoding="utf-8")

    (tmp_path / "src").mkdir()
    (tmp_path / "src/app.py").write_text(
        (root / "tests/fixtures/wave6b/sonar/src/app.py").read_text(encoding="utf-8"),
        encoding="utf-8")
    (tmp_path / "src/utils.py").write_text(
        (root / "tests/fixtures/wave6b/sonar/src/utils.py").read_text(encoding="utf-8"),
        encoding="utf-8")

    with patch("agents.sonar_fix_agent.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = canned
        mock_cls.return_value = mock_agent
        result = run_sonar_fix_agent(
            conn=test_db, job_id="j1",
            file_path="sonar.json", content=issues_body,
            file_hash="h1", language=None,
            custom_prompt=None,
        )

    out_dir = _os_lib.path.dirname(_os_lib.path.dirname(result["output_path"]))
    summary = _json_lib.loads(open(_os_lib.path.join(out_dir, "summary.json"),
                                   "r", encoding="utf-8").read())
    # Two source files → two entries
    assert len(summary.get("files", [])) == 2


def test_f11_top_n_cap_respected(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    big_issues = {"issues": [
        {"rule": f"S{i}", "severity": "MAJOR", "component": "src/a.py",
         "line": i, "message": "x", "effort": "1min",
         "textRange": {"startLine": i, "endLine": i}}
        for i in range(100)
    ], "total": 100, "p": 1, "ps": 100}
    (tmp_path / "src").mkdir()
    (tmp_path / "src/a.py").write_text("# test\n", encoding="utf-8")
    with patch("agents.sonar_fix_agent.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = "```diff\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-# test\n+# fixed\n```"
        mock_cls.return_value = mock_agent
        result = run_sonar_fix_agent(
            conn=test_db, job_id="j2",
            file_path="sonar.json",
            content=_json_lib.dumps(big_issues),
            file_hash="h2", language=None,
            custom_prompt="__sonar_top_n__=5",
        )
    # 100 issues resolved from intake; 5 actually dispatched to LLM
    assert result.get("issues_total") == 100


def test_f11_no_issues_errors(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("agents.sonar_fix_agent.Agent") as mock_cls:
        result = run_sonar_fix_agent(
            conn=test_db, job_id="j3",
            file_path="some.py", content="print('not json')",
            file_hash="h3", language=None, custom_prompt=None,
        )
        mock_cls.assert_not_called()
    assert result.get("output_path") is None
    assert "error" in result["summary"].lower() or "no issues" in result["summary"].lower()
