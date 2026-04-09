import os
import pytest
from tools.clone_repo import parse_github_url, clone_or_pull, get_git_log
from tools.fetch_local import scan_folder_recursive


def test_full_clone_and_file_scan(tmp_path, monkeypatch):
    """End-to-end: parse URL → clone → scan files → get commits."""
    monkeypatch.setattr("tools.clone_repo.REPOS_BASE", str(tmp_path / "repos"))

    # Parse
    parsed = parse_github_url("https://github.com/bravetux/Code_AI_Maniac.git")
    assert parsed["slug"] == "bravetux/Code_AI_Maniac"

    # Clone
    result = clone_or_pull(parsed["slug"], branch="main")
    assert result["status"] == "cloned"
    repo_path = result["path"]

    # Scan files
    files = scan_folder_recursive(repo_path, extensions=["py", "md"])
    assert len(files) > 0

    # Get commits
    commits = get_git_log(repo_path, limit=10)
    assert len(commits) > 0
    assert all(k in commits[0] for k in ("sha", "message", "author", "date"))

    # Pull (idempotent)
    result2 = clone_or_pull(parsed["slug"], branch="main")
    assert result2["status"] == "pulled"
