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

import base64
import binascii
import hashlib
import os

import httpx

try:
    from strands import tool
except ImportError:
    def tool(f): return f


def _file_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


@tool
def fetch_gitea_file(gitea_url: str, repo: str, file_path: str, branch: str,
                     token: str, start_line: int | None = None,
                     end_line: int | None = None) -> dict:
    """Fetch a file from a Gitea repository."""
    url = f"{gitea_url.rstrip('/')}/api/v1/repos/{repo}/contents/{file_path}"
    headers = {"Authorization": f"token {token}"}
    params = {"ref": branch}
    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code == 404:
            return {"error": f"File not found: {file_path}", "file_path": file_path}
        if resp.status_code != 200:
            return {"error": f"Gitea returned {resp.status_code}", "file_path": file_path}
        try:
            data = resp.json()
            raw_b64 = data["content"]
            full_content = base64.b64decode(raw_b64).decode("utf-8", errors="replace")
        except (KeyError, ValueError, binascii.Error) as e:
            return {"error": f"Failed to decode response: {e}", "file_path": file_path}
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
    except httpx.RequestError as e:
        return {"error": f"Connection error: {e}", "file_path": file_path}


@tool
def fetch_gitea_commits(gitea_url: str, repo: str, branch: str,
                        token: str, limit: int = 50) -> dict:
    """Fetch recent commits from a Gitea repository."""
    url = f"{gitea_url.rstrip('/')}/api/v1/repos/{repo}/commits"
    headers = {"Authorization": f"token {token}"}
    params = {"sha": branch, "limit": limit}
    try:
        resp = httpx.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 200:
            return {"error": f"Gitea returned {resp.status_code}"}
        commits = [
            {"sha": c["sha"], "message": c["commit"]["message"],
             "author": c["commit"]["author"]["name"]}
            for c in resp.json()
        ]
        return {"repo": repo, "branch": branch, "commits": commits}
    except httpx.RequestError as e:
        return {"error": f"Connection error: {e}"}
