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

import hashlib
import os

from github import Github, GithubException

try:
    from strands import tool
except ImportError:
    def tool(f): return f


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


@tool
def fetch_github_file(repo: str, file_path: str, branch: str, token: str,
                      start_line: int | None = None,
                      end_line: int | None = None) -> dict:
    """Fetch a file from a GitHub repository."""
    try:
        g = Github(token) if token else Github()
        r = g.get_repo(repo)
        contents = r.get_contents(file_path, ref=branch)
        full_content = contents.decoded_content.decode("utf-8", errors="replace")
        file_hash = _file_hash(full_content)
        lines = full_content.splitlines(keepends=True)
        total_lines = len(lines)
        if start_line is not None and end_line is not None:
            content = "".join(lines[start_line - 1:end_line])
        else:
            content = full_content
            start_line = 1
            end_line = total_lines
        return {
            "file_path": file_path,
            "repo": repo,
            "branch": branch,
            "content": content,
            "total_lines": total_lines,
            "start_line": start_line,
            "end_line": end_line,
            "file_hash": file_hash,
            "extension": os.path.splitext(file_path)[1].lstrip("."),
        }
    except GithubException as e:
        msg = f"GitHub error: {e.status} {e.data}"
        if e.status in (401, 403, 404) and not token:
            msg += " — this repository may be private. Provide a GitHub token to access it."
        return {"error": msg, "file_path": file_path}


@tool
def fetch_github_pr_diff(repo: str, pr_number: int, token: str) -> dict:
    """Fetch the diff of a GitHub pull request."""
    try:
        g = Github(token) if token else Github()
        r = g.get_repo(repo)
        pr = r.get_pull(pr_number)
        files = [
            {"filename": f.filename, "patch": f.patch or "", "status": f.status}
            for f in pr.get_files()
        ]
        return {"repo": repo, "pr_number": pr_number, "files": files}
    except GithubException as e:
        msg = f"GitHub error: {e.status} {e.data}"
        if e.status in (401, 403, 404) and not token:
            msg += " — this repository may be private. Provide a GitHub token to access it."
        return {"error": msg}
    except Exception as e:
        return {"error": str(e)}
