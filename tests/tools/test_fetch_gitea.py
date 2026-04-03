from unittest.mock import patch, MagicMock
from tools.fetch_gitea import fetch_gitea_file


def test_fetch_gitea_file_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "content": "ZGVmIGhlbGxvKCk6CiAgICBwYXNzCg==",  # base64 of "def hello():\n    pass\n"
        "name": "hello.py",
        "size": 22,
    }
    with patch("tools.fetch_gitea.httpx.get", return_value=mock_response):
        result = fetch_gitea_file(
            gitea_url="http://localhost:3000",
            repo="owner/repo",
            file_path="src/hello.py",
            branch="main",
            token="fake-token"
        )
    assert "def hello" in result["content"]
    assert result["file_path"] == "src/hello.py"


def test_fetch_gitea_file_not_found():
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch("tools.fetch_gitea.httpx.get", return_value=mock_response):
        result = fetch_gitea_file(
            gitea_url="http://localhost:3000",
            repo="owner/repo",
            file_path="missing.py",
            branch="main",
            token="fake-token"
        )
    assert "error" in result
