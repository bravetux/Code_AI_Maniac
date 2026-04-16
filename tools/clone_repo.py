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
import re
import subprocess


REPOS_BASE = os.path.join("data", "repos")


def parse_github_url(url_or_slug: str) -> dict:
    """Parse a GitHub URL or owner/repo slug into components.

    Accepts:
        https://github.com/owner/repo.git
        https://github.com/owner/repo
        github.com/owner/repo
        owner/repo

    Returns: {"owner": str, "repo": str, "slug": "owner/repo"}
    Raises: ValueError if the input cannot be parsed.
    """
    text = url_or_slug.strip().rstrip("/")

    # Strip scheme
    text = re.sub(r"^https?://", "", text)
    # Strip github.com prefix
    text = re.sub(r"^github\.com/", "", text)
    # Strip .git suffix
    text = re.sub(r"\.git$", "", text)

    parts = text.split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        raise ValueError(f"Cannot parse GitHub reference: {url_or_slug!r}")

    owner, repo = parts[0], parts[1]
    return {"owner": owner, "repo": repo, "slug": f"{owner}/{repo}"}


def clone_or_pull(repo_slug: str, branch: str = "main",
                  token: str | None = None) -> dict:
    """Clone a GitHub repo or pull if already cloned.

    Args:
        repo_slug: "owner/repo" format (use parse_github_url first if needed)
        branch: Git branch to clone/checkout
        token: Optional GitHub token for private repos

    Returns: {"path": str, "status": "cloned"|"pulled", "error": str (if failed)}
    """
    parsed = parse_github_url(repo_slug)
    dest = os.path.join(REPOS_BASE, parsed["owner"], parsed["repo"])

    if token:
        clone_url = f"https://{token}@github.com/{parsed['slug']}.git"
    else:
        clone_url = f"https://github.com/{parsed['slug']}.git"

    git_dir = os.path.join(dest, ".git")

    try:
        if os.path.isdir(git_dir):
            # Pull latest
            subprocess.run(
                ["git", "-C", dest, "fetch", "origin", branch],
                capture_output=True, text=True, check=True, timeout=120,
            )
            subprocess.run(
                ["git", "-C", dest, "checkout", branch],
                capture_output=True, text=True, check=True, timeout=30,
            )
            subprocess.run(
                ["git", "-C", dest, "reset", "--hard", f"origin/{branch}"],
                capture_output=True, text=True, check=True, timeout=30,
            )
            return {"path": dest, "status": "pulled"}
        else:
            os.makedirs(dest, exist_ok=True)
            subprocess.run(
                ["git", "clone", "--branch", branch, clone_url, dest],
                capture_output=True, text=True, check=True, timeout=300,
            )
            return {"path": dest, "status": "cloned"}

    except subprocess.CalledProcessError as e:
        return {"path": dest, "status": "error",
                "error": f"Git error: {e.stderr.strip() or e.stdout.strip()}"}
    except subprocess.TimeoutExpired:
        return {"path": dest, "status": "error",
                "error": "Git operation timed out (clone may be too large)"}


_LOG_SEP = "---COMMIT_SEP---"
_FIELD_SEP = "---FIELD_SEP---"


def get_git_log(repo_path: str, limit: int | None = None) -> list[dict]:
    """Extract commit history from a local git repo.

    Args:
        repo_path: Path to the cloned repo
        limit: Max commits to return. None = all commits.

    Returns: List of {"sha", "message", "author", "date", "files_changed"}
    """
    # Use tformat (terminator) so each commit ends with the separator on its own line
    fmt = _FIELD_SEP.join(["%H", "%s", "%an", "%aI"])
    cmd = [
        "git", "-C", repo_path, "log",
        f"--pretty=tformat:{_LOG_SEP}{fmt}",
        "--name-only",
    ]
    if limit is not None:
        cmd.extend(["-n", str(limit)])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return []

    raw = result.stdout.strip()
    if not raw:
        return []

    commits = []
    current_commit: dict | None = None

    for line in raw.splitlines():
        if line.startswith(_LOG_SEP):
            # Save previous commit
            if current_commit is not None:
                commits.append(current_commit)
            # Parse header: ---COMMIT_SEP---SHA---FIELD_SEP---msg---FIELD_SEP---author---FIELD_SEP---date
            header = line[len(_LOG_SEP):]
            parts = header.split(_FIELD_SEP)
            current_commit = {
                "sha": parts[0][:8] if len(parts) > 0 else "",
                "message": parts[1] if len(parts) > 1 else "",
                "author": parts[2] if len(parts) > 2 else "",
                "date": parts[3] if len(parts) > 3 else "",
                "files_changed": [],
            }
        elif current_commit is not None:
            stripped = line.strip()
            if stripped:
                current_commit["files_changed"].append(stripped)

    if current_commit is not None:
        commits.append(current_commit)

    return commits
