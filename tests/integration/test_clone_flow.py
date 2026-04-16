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
