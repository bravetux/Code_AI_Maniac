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
    """Regression: F15 auto-scans the real findings.json sidecar emitted by
    Bug Analysis in the shared JOB_REPORT_TS folder."""
    from agents.bug_analysis import run_bug_analysis
    from agents.auto_fix_agent import run_auto_fix_agent

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JOB_REPORT_TS", "20260422_120000")

    root = _project_root()
    buggy = (root / "tests/fixtures/wave6b/auto_fix/buggy.py").read_text(encoding="utf-8")

    # Step 1: run Bug Analysis with a canned LLM response
    bug_canned = json.dumps({
        "bugs": [
            {"line": 2, "severity": "critical",
             "description": "Division by zero",
             "suggestion": "Add zero-check"},
            {"line": 6, "severity": "critical",
             "description": "Hardcoded secret",
             "suggestion": "Move to env var"},
        ],
        "summary": "2 bugs found"
    })

    with patch("agents.bug_analysis.Agent") as mock_ba:
        mock_agent = MagicMock()
        mock_agent.return_value = bug_canned
        mock_ba.return_value = mock_agent
        run_bug_analysis(
            conn=test_db, job_id="jchain",
            file_path="buggy.py", content=buggy,
            file_hash="hbuggy", language="python", custom_prompt=None,
        )

    # Verify the sidecar landed in the expected location
    sidecar = tmp_path / "Reports" / "20260422_120000" / "bug_analysis" / "buggy.json"
    assert sidecar.exists(), f"bug_analysis did not write sidecar to {sidecar}"

    # Step 2: run F15 with no __findings__ prefix — must auto-scan the sidecar
    f15_canned = '''```diff
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

    with patch("agents.auto_fix_agent.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = f15_canned
        mock_cls.return_value = mock_agent
        result = run_auto_fix_agent(
            conn=test_db, job_id="jchain-f15",
            file_path="buggy.py", content=buggy,
            file_hash="hchain", language="python", custom_prompt=None,
        )

    assert result.get("output_path"), f"F15 produced no output: {result}"
    patched = open(result["output_path"], "r", encoding="utf-8").read()
    assert "raise ValueError" in patched
    assert "os.environ" in patched
    # Findings came from the sidecar, not inline prefix
    assert len(result.get("findings_addressed", [])) >= 1


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
