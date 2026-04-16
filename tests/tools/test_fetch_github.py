# AI Code Maniac - Multi-Agent Code Analysis Platform
# Copyright (C) 2026 B.Vignesh Kumar (Bravetux) <ic19939@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Author: B.Vignesh Kumar aka Bravetux
# Email:  ic19939@gmail.com
# Developed: 12th April 2026

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
