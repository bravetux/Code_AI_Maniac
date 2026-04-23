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


from agents.self_healing_agent import _detect_framework, _extract_selectors


def test_detect_framework_selenium():
    assert _detect_framework("from selenium import webdriver\nBy.ID(...)") == "selenium"


def test_detect_framework_playwright():
    assert _detect_framework("from playwright.sync_api import sync_playwright\npage.locator('x')") == "playwright"


def test_detect_framework_cypress_by_calls():
    assert _detect_framework("describe('login', () => { cy.get('#x'); })") == "cypress"


def test_detect_framework_cypress_by_filename():
    assert _detect_framework("some test", file_name="login.cy.js") == "cypress"


def test_detect_framework_unknown():
    assert _detect_framework("def test_foo(): pass") is None


def test_extract_selectors_selenium():
    code = """
    driver.find_element(By.ID, "login-btn")
    driver.find_element(By.XPATH, "//input[@name='email']")
    driver.find_element(By.CSS_SELECTOR, "#password")
    """
    sels = _extract_selectors(code, framework="selenium")
    assert "login-btn" in sels
    assert any("//input" in s for s in sels)
    assert "#password" in sels


def test_extract_selectors_playwright():
    code = 'page.locator("#login")\npage.get_by_test_id("email")'
    sels = _extract_selectors(code, framework="playwright")
    assert "#login" in sels
    assert "email" in sels


def test_extract_selectors_cypress():
    code = 'cy.get("#btn").click()\ncy.get("[data-testid=submit]")'
    sels = _extract_selectors(code, framework="cypress")
    assert "#btn" in sels
    assert "[data-testid=submit]" in sels


def test_extract_selectors_empty_when_unknown_framework():
    assert _extract_selectors("foo", framework=None) == []


import os as _os_lib
import pathlib
from unittest.mock import patch, MagicMock


def _project_root():
    cur = pathlib.Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "pytest.ini").exists():
            return parent
    return pathlib.Path.cwd()


def test_f9_writes_patch_for_selenium_test(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    root = _project_root()
    old_test = (root / "tests/fixtures/wave6b/login_selectors/old_test.py").read_text(encoding="utf-8")
    dom = (root / "tests/fixtures/wave6b/login_selectors/dom.html").read_text(encoding="utf-8")
    canned = (root / "tests/fixtures/wave6b/login_selectors/canned_llm.txt").read_text(encoding="utf-8")

    with patch("agents.self_healing_agent.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = canned
        mock_cls.return_value = mock_agent
        result = run_self_healing_agent(
            conn=test_db, job_id="j1",
            file_path="old_test.py", content=old_test,
            file_hash="h1", language="python",
            custom_prompt=f"__page_html__\n{dom}",
        )

    assert result.get("output_path")
    out_dir = _os_lib.path.dirname(_os_lib.path.dirname(result["output_path"]))
    assert _os_lib.path.isfile(_os_lib.path.join(out_dir, "patches", "old_test.py"))
    assert _os_lib.path.isfile(_os_lib.path.join(out_dir, "patches", "old_test.py.diff"))
    assert _os_lib.path.isfile(_os_lib.path.join(out_dir, "pr_comment.md"))
    import json as _json
    summary = _json.loads(open(_os_lib.path.join(out_dir, "summary.json"),
                               "r", encoding="utf-8").read())
    assert any(f.get("framework") == "selenium" for f in summary.get("files", [])) \
        or summary.get("framework") == "selenium"


def test_f9_errors_when_no_dom_supplied(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with patch("agents.self_healing_agent.Agent") as mock_cls:
        result = run_self_healing_agent(
            conn=test_db, job_id="j2",
            file_path="old_test.py",
            content="from selenium import webdriver\ndriver.find_element(By.ID, 'x')",
            file_hash="h2", language="python",
            custom_prompt=None,
        )
        mock_cls.assert_not_called()
    assert "error" in result["summary"].lower() or "dom" in result["summary"].lower()
    assert result.get("output_path") is None


def test_f9_reads_sibling_dom_html(test_db, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test_file = tmp_path / "old_test.py"
    test_file.write_text("from selenium import webdriver\n"
                         "driver.find_element(By.ID, 'x')\n", encoding="utf-8")
    dom_file = tmp_path / "dom.html"
    dom_file.write_text("<html><body><button data-testid='x'></button></body></html>",
                        encoding="utf-8")
    canned = "```diff\n--- a/old_test.py\n+++ b/old_test.py\n@@ -1,2 +1,2 @@\n from selenium import webdriver\n-driver.find_element(By.ID, 'x')\n+driver.find_element(By.CSS_SELECTOR, \"[data-testid='x']\")\n```"
    with patch("agents.self_healing_agent.Agent") as mock_cls:
        mock_agent = MagicMock()
        mock_agent.return_value = canned
        mock_cls.return_value = mock_agent
        result = run_self_healing_agent(
            conn=test_db, job_id="j4",
            file_path=str(test_file), content=test_file.read_text(encoding="utf-8"),
            file_hash="h4", language="python", custom_prompt=None,
        )
    assert result.get("output_path")
