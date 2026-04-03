import base64
import hashlib

import httpx

try:
    from strands import tool
except ImportError:
    def tool(f): return f


def _hash(content: str) -> str:
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
        data = resp.json()
        content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        lines = content.splitlines(keepends=True)
        total_lines = len(lines)
        if start_line and end_line:
            content = "".join(lines[start_line - 1:end_line])
        return {
            "file_path": file_path,
            "repo": repo,
            "branch": branch,
            "content": content,
            "total_lines": total_lines,
            "start_line": start_line or 1,
            "end_line": end_line or total_lines,
            "file_hash": _hash(content),
            "extension": file_path.rsplit(".", 1)[-1] if "." in file_path else "",
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
