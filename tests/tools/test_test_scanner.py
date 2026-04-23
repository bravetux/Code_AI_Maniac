from tools.test_scanner import scan_tests


def test_scans_python_pytest_tests():
    tests = scan_tests("tests/fixtures/wave6a/reset_password_tests")
    names = [t["test_name"] for t in tests]
    assert "test_reset_link_visible_on_login_page" in names
    assert "test_known_email_triggers_reset_mail" in names
    assert "test_unknown_email_returns_generic_200" in names
    assert "test_admin_audit_log_flush" in names
    assert len(tests) >= 4


def test_returns_kind_and_path():
    tests = scan_tests("tests/fixtures/wave6a/reset_password_tests")
    for t in tests:
        assert "kind" in t
        assert "file" in t
        assert t["kind"] == "pytest"
        assert t["file"].endswith(".py")


def test_returns_snippet_with_docstring():
    tests = scan_tests("tests/fixtures/wave6a/reset_password_tests")
    link_test = next(t for t in tests if t["test_name"] == "test_reset_link_visible_on_login_page")
    assert "Forgot password" in link_test.get("snippet", "")


def test_picks_up_feature_files(tmp_path):
    (tmp_path / "auth.feature").write_text(
        "Feature: Password reset\n"
        "  Scenario: User resets password\n"
        "    Given I am on the login page\n"
        "    When I click 'Forgot password'\n"
        "    Then I receive a reset email\n"
        "  Scenario Outline: Invalid email handling\n"
        "    Given email <email>\n"
        "    When I submit\n"
        "    Then I see <msg>\n",
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    scenarios = [t for t in tests if t["kind"] == "gherkin"]
    assert len(scenarios) >= 2


def test_picks_up_java_junit(tmp_path):
    (tmp_path / "LoginTests.java").write_text(
        "import org.junit.jupiter.api.Test;\n"
        "class LoginTests {\n"
        "  @Test void testForgotPasswordLinkVisible() {}\n"
        "  @Test void testResetEmailSent() {}\n"
        "}\n",
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    names = {t["test_name"] for t in tests if t["kind"] == "junit"}
    assert "testForgotPasswordLinkVisible" in names
    assert "testResetEmailSent" in names


def test_picks_up_jest_ts(tmp_path):
    (tmp_path / "login.test.ts").write_text(
        'describe("login", () => {\n'
        '  it("shows forgot password link", () => {});\n'
        '  test("sends reset email within 30s", () => {});\n'
        '});\n',
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    names = {t["test_name"] for t in tests if t["kind"] == "jest"}
    assert "shows forgot password link" in names
    assert "sends reset email within 30s" in names


def test_picks_up_jmx_transactions(tmp_path):
    (tmp_path / "plan.jmx").write_text(
        '<jmeterTestPlan><hashTree>'
        '<TransactionController testname="reset password flow"/>'
        '<TransactionController testname="login flow"/>'
        '</hashTree></jmeterTestPlan>',
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    names = {t["test_name"] for t in tests if t["kind"] == "jmeter"}
    assert "reset password flow" in names


def test_picks_up_postman_items(tmp_path):
    import json as _json
    (tmp_path / "api_collection.json").write_text(
        _json.dumps({
            "info": {"name": "x", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
            "item": [{"name": "POST /reset"}, {"name": "GET /login"}],
        }),
        encoding="utf-8",
    )
    tests = scan_tests(str(tmp_path))
    names = {t["test_name"] for t in tests if t["kind"] == "postman"}
    assert "POST /reset" in names


def test_nonexistent_path_returns_empty():
    assert scan_tests("tests/fixtures/wave6a/does_not_exist") == []
