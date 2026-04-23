import json
import os
import pathlib
from unittest.mock import patch, MagicMock


def _project_root():
    cur = pathlib.Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            return parent
    return pathlib.Path.cwd()


_CANNED_DIFF = '''```diff
--- a/buggy.py
+++ b/buggy.py
@@ -1,7 +1,11 @@
+import os
+
+
 def divide(a, b):
+    if b == 0:
+        raise ValueError("b must not be zero")
     return a / b


 def login(password):
-    secret = "hunter2"
+    secret = os.environ.get("APP_SECRET", "")
     return password == secret
```'''


def test_f15_auto_scans_bug_analysis_output_in_same_reports_ts(test_db, tmp_path, monkeypatch):
    """Regression: F15 should auto-scan the same JOB_REPORT_TS folder for
    Bug Analysis + Refactoring Advisor output when ticked alongside them."""
    from agents.auto_fix_agent import run_auto_fix_agent

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JOB_REPORT_TS", "20260422_120000")
    reports_root = tmp_path / "Reports" / "20260422_120000"
    (reports_root / "bug_analysis").mkdir(parents=True)
    (reports_root / "bug_analysis" / "buggy.md").write_text(json.dumps({
        "findings": [
            {"id": "B-1", "line": 2, "severity": "critical",
             "description": "Division by zero"},
            {"id": "B-2", "line": 6, "severity": "critical",
             "description": "Hardcoded secret"},
        ]
    }), encoding="utf-8")

    root = _project_root()
    buggy = (root / "tests/fixtures/wave6b/auto_fix/buggy.py").read_text(encoding="utf-8")

    with patch("agents.auto_fix_agent.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = _CANNED_DIFF
        mock_cls.return_value = mock_agent
        result = run_auto_fix_agent(
            conn=test_db, job_id="jchain",
            file_path="buggy.py", content=buggy,
            file_hash="hchain", language="python", custom_prompt=None,
        )

    assert result.get("output_path"), f"no output: {result}"
    patched = open(result["output_path"], "r", encoding="utf-8").read()
    assert "raise ValueError" in patched
    assert "os.environ" in patched
    assert "B-1" in str(result.get("findings_addressed", []))


def test_job_report_ts_is_shared_across_waves(test_db, tmp_path, monkeypatch):
    """Regression: orchestrator sets JOB_REPORT_TS once; F9/F11/F14/F15 all read it."""
    monkeypatch.setenv("JOB_REPORT_TS", "99999999_999999")
    from agents.self_healing_agent import _report_ts as f9
    from agents.sonar_fix_agent import _report_ts as f11
    from agents.sql_generator import _report_ts as f14
    from agents.auto_fix_agent import _report_ts as f15
    assert f9() == "99999999_999999"
    assert f11() == "99999999_999999"
    assert f14() == "99999999_999999"
    assert f15() == "99999999_999999"
