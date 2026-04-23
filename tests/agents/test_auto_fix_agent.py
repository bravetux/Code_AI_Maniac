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


import json as _json_lib
import os as _os_lib
import pathlib
from unittest.mock import patch, MagicMock
from agents.auto_fix_agent import _resolve_findings


def _project_root():
    cur = pathlib.Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            return parent
    return pathlib.Path.cwd()


def test_resolve_findings_prefix_wins():
    body = '{"findings": [{"id": "B-1", "line": 10, "description": "x"}]}'
    prefix = f"__findings__\n{body}"
    findings = _resolve_findings(file_path="foo.py", custom_prompt=prefix,
                                 reports_root=None)
    assert len(findings) == 1
    assert findings[0]["id"] == "B-1"


def test_resolve_findings_auto_scan_from_reports(tmp_path):
    bug_dir = tmp_path / "bug_analysis"
    bug_dir.mkdir()
    (bug_dir / "buggy.md").write_text(
        '{"findings": [{"id": "B-A", "description": "auto"}]}',
        encoding="utf-8")
    findings = _resolve_findings(file_path="buggy.py", custom_prompt=None,
                                 reports_root=str(tmp_path))
    assert any(f.get("id") == "B-A" for f in findings)


def test_resolve_findings_returns_empty_when_nothing():
    findings = _resolve_findings(file_path="foo.py", custom_prompt=None,
                                 reports_root=None)
    assert findings == []


def test_f15_auto_fix_writes_patch(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = _project_root()
    buggy = (root / "tests/fixtures/wave6b/auto_fix/buggy.py").read_text(encoding="utf-8")
    findings_body = (root / "tests/fixtures/wave6b/auto_fix/bug_analysis_findings.json").read_text(encoding="utf-8")
    canned = (root / "tests/fixtures/wave6b/auto_fix/canned_llm.txt").read_text(encoding="utf-8")

    with patch("agents.auto_fix_agent.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = canned
        mock_cls.return_value = mock_agent
        result = run_auto_fix_agent(
            conn=test_db, job_id="j1",
            file_path="buggy.py", content=buggy,
            file_hash="h1", language="python",
            custom_prompt=f"__findings__\n{findings_body}",
        )

    assert result.get("output_path")
    patched = open(result["output_path"], "r", encoding="utf-8").read()
    assert "raise ValueError" in patched
    assert "os.environ" in patched


def test_f15_no_findings_errors(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("agents.auto_fix_agent.Agent") as mock_cls:
        result = run_auto_fix_agent(
            conn=test_db, job_id="j2",
            file_path="buggy.py", content="def foo(): pass",
            file_hash="h2", language="python", custom_prompt=None,
        )
        mock_cls.assert_not_called()
    assert result.get("output_path") is None
    assert "error" in result["summary"].lower() or "finding" in result["summary"].lower()


def test_f15_rejected_diff_marks_applied_false(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    bad_canned = ("```diff\n"
                  "--- a/buggy.py\n"
                  "+++ b/buggy.py\n"
                  "@@ -1,3 +1,3 @@\n"
                  "-this line does not exist\n"
                  "+replaced\n"
                  " another\n"
                  "```")
    findings = '{"findings": [{"id": "B-1", "description": "x"}]}'
    with patch("agents.auto_fix_agent.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = bad_canned
        mock_cls.return_value = mock_agent
        result = run_auto_fix_agent(
            conn=test_db, job_id="j3",
            file_path="buggy.py", content="def foo(): pass\n",
            file_hash="h3", language="python",
            custom_prompt=f"__findings__\n{findings}",
        )
    assert result.get("applied") is False or "reject" in result["summary"].lower()
