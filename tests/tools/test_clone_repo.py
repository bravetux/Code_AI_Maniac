import os
import shutil
from pathlib import Path
import pytest
from tools.clone_repo import clone_or_pull, parse_github_url


@pytest.mark.parametrize("url,expected_owner,expected_repo", [
    ("https://github.com/bravetux/Code_AI_Maniac.git", "bravetux", "Code_AI_Maniac"),
    ("https://github.com/bravetux/Code_AI_Maniac", "bravetux", "Code_AI_Maniac"),
    ("github.com/bravetux/Code_AI_Maniac", "bravetux", "Code_AI_Maniac"),
    ("bravetux/Code_AI_Maniac", "bravetux", "Code_AI_Maniac"),
    ("https://github.com/octocat/Hello-World.git", "octocat", "Hello-World"),
])
def test_parse_github_url(url, expected_owner, expected_repo):
    result = parse_github_url(url)
    assert result["owner"] == expected_owner
    assert result["repo"] == expected_repo
    assert result["slug"] == f"{expected_owner}/{expected_repo}"


def test_parse_github_url_invalid():
    with pytest.raises(ValueError):
        parse_github_url("")
    with pytest.raises(ValueError):
        parse_github_url("not-a-url")


def test_clone_public_repo(tmp_path, monkeypatch):
    """Clone a small public repo without a token."""
    monkeypatch.setattr("tools.clone_repo.REPOS_BASE", str(tmp_path / "repos"))
    result = clone_or_pull("bravetux/Code_AI_Maniac", branch="main")
    assert result["status"] in ("cloned", "pulled")
    assert "error" not in result
    assert os.path.isdir(result["path"])
    assert os.path.isdir(os.path.join(result["path"], ".git"))


def test_pull_existing_repo(tmp_path, monkeypatch):
    """Second call should pull, not clone."""
    monkeypatch.setattr("tools.clone_repo.REPOS_BASE", str(tmp_path / "repos"))
    r1 = clone_or_pull("bravetux/Code_AI_Maniac", branch="main")
    assert r1["status"] == "cloned"
    r2 = clone_or_pull("bravetux/Code_AI_Maniac", branch="main")
    assert r2["status"] == "pulled"


def test_clone_invalid_repo(tmp_path, monkeypatch):
    """Non-existent repo should return error."""
    monkeypatch.setattr("tools.clone_repo.REPOS_BASE", str(tmp_path / "repos"))
    result = clone_or_pull("nonexistent-user-xyz/no-such-repo-999", branch="main")
    assert "error" in result
