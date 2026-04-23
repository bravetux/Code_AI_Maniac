import json
from unittest.mock import patch, MagicMock
import pytest
from tools.sonar_fetcher import fetch_issues, SonarFetchError


def _mock_response(body: dict, status: int = 200, headers: dict | None = None):
    m = MagicMock()
    m.read.return_value = json.dumps(body).encode("utf-8")
    m.status = status
    m.getcode.return_value = status
    m.__enter__ = lambda s: s
    m.__exit__ = lambda *a, **kw: None
    m.headers = headers or {}
    return m


def test_fetch_issues_single_page():
    body = {
        "issues": [
            {"rule": "S100", "severity": "MAJOR", "component": "app.py",
             "line": 10, "message": "msg", "effort": "5min",
             "textRange": {"startLine": 10, "endLine": 10}},
        ],
        "total": 1,
        "p": 1,
        "ps": 100,
    }
    with patch("urllib.request.urlopen",
               return_value=_mock_response(body)) as _mock:
        issues = fetch_issues("https://sonar.test", "myproj", "token123")
    assert len(issues) == 1
    assert issues[0]["rule"] == "S100"


def test_fetch_issues_pagination_until_max_total():
    page1 = {"issues": [{"rule": f"R{i}", "severity": "MAJOR",
                         "component": "f.py"} for i in range(100)],
             "total": 250, "p": 1, "ps": 100}
    page2 = {"issues": [{"rule": f"R{i+100}", "severity": "MAJOR",
                         "component": "f.py"} for i in range(50)],
             "total": 250, "p": 2, "ps": 100}
    responses = [_mock_response(page1), _mock_response(page2)]
    with patch("urllib.request.urlopen", side_effect=responses):
        issues = fetch_issues("https://sonar.test", "myproj", "token",
                              page_size=100, max_total=150)
    assert len(issues) == 150


def test_fetch_issues_honours_retry_after_on_429():
    body = {"issues": [], "total": 0, "p": 1, "ps": 100}
    err_resp = _mock_response({}, status=429,
                              headers={"Retry-After": "0"})
    ok_resp = _mock_response(body)
    with patch("urllib.request.urlopen", side_effect=[err_resp, ok_resp]), \
         patch("time.sleep") as mock_sleep:
        issues = fetch_issues("https://sonar.test", "myproj", "token")
    assert issues == []
    assert mock_sleep.called


def test_fetch_issues_auth_error_raises():
    err_resp = _mock_response({"errors": ["unauthorized"]}, status=401)
    with patch("urllib.request.urlopen", return_value=err_resp):
        with pytest.raises(SonarFetchError):
            fetch_issues("https://sonar.test", "myproj", "bad-token")


def test_fetch_issues_empty_response_returns_empty_list():
    body = {"issues": [], "total": 0, "p": 1, "ps": 100}
    with patch("urllib.request.urlopen", return_value=_mock_response(body)):
        assert fetch_issues("https://sonar.test", "myproj", "token") == []
