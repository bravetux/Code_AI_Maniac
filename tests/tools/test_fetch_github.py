from unittest.mock import MagicMock, patch
from tools.fetch_github import fetch_github_file, fetch_github_pr_diff


def test_fetch_github_file_success():
    mock_repo = MagicMock()
    mock_file = MagicMock()
    mock_file.decoded_content = b"def hello():\n    pass\n"
    mock_file.path = "src/hello.py"
    mock_file.size = 22
    mock_repo.get_contents.return_value = mock_file

    with patch("tools.fetch_github.Github") as mock_gh:
        mock_gh.return_value.get_repo.return_value = mock_repo
        result = fetch_github_file(
            repo="owner/repo", file_path="src/hello.py",
            branch="main", token="fake-token"
        )

    assert result["content"] == "def hello():\n    pass\n"
    assert result["file_path"] == "src/hello.py"
    assert "file_hash" in result


def test_fetch_github_file_not_found():
    from github import GithubException
    with patch("tools.fetch_github.Github") as mock_gh:
        mock_gh.return_value.get_repo.side_effect = GithubException(404, "Not found")
        result = fetch_github_file(
            repo="owner/repo", file_path="missing.py",
            branch="main", token="fake-token"
        )
    assert "error" in result


def test_fetch_github_pr_diff():
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_file = MagicMock()
    mock_file.filename = "src/main.py"
    mock_file.patch = "@@ -1,3 +1,4 @@\n def foo():\n-    pass\n+    return 1\n"
    mock_file.status = "modified"
    mock_pr.get_files.return_value = [mock_file]
    mock_repo.get_pull.return_value = mock_pr

    with patch("tools.fetch_github.Github") as mock_gh:
        mock_gh.return_value.get_repo.return_value = mock_repo
        result = fetch_github_pr_diff(repo="owner/repo", pr_number=42, token="fake-token")

    assert len(result["files"]) == 1
    assert result["files"][0]["filename"] == "src/main.py"


def test_fetch_public_repo_no_token():
    """Public repo should work without a token."""
    result = fetch_github_file(
        repo="octocat/Hello-World",
        file_path="README",
        branch="master",
        token=None,
    )
    assert "error" not in result
    assert "content" in result
    assert len(result["content"]) > 0


def test_fetch_private_repo_no_token():
    """Private repo without token should give helpful error."""
    result = fetch_github_file(
        repo="bravetux/some-private-repo-that-doesnt-exist",
        file_path="README.md",
        branch="main",
        token=None,
    )
    assert "error" in result
    assert "private" in result["error"].lower() or "GitHub error" in result["error"]
