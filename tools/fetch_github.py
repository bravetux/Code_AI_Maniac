import hashlib

from github import Github, GithubException

try:
    from strands import tool
except ImportError:
    def tool(f): return f


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


@tool
def fetch_github_file(repo: str, file_path: str, branch: str, token: str,
                      start_line: int | None = None,
                      end_line: int | None = None) -> dict:
    """Fetch a file from a GitHub repository."""
    try:
        g = Github(token)
        r = g.get_repo(repo)
        contents = r.get_contents(file_path, ref=branch)
        content = contents.decoded_content.decode("utf-8", errors="replace")
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
    except GithubException as e:
        return {"error": f"GitHub error: {e.status} {e.data}", "file_path": file_path}
    except Exception as e:
        return {"error": str(e), "file_path": file_path}


@tool
def fetch_github_pr_diff(repo: str, pr_number: int, token: str) -> dict:
    """Fetch the diff of a GitHub pull request."""
    try:
        g = Github(token)
        r = g.get_repo(repo)
        pr = r.get_pull(pr_number)
        files = [
            {"filename": f.filename, "patch": f.patch or "", "status": f.status}
            for f in pr.get_files()
        ]
        return {"repo": repo, "pr_number": pr_number, "files": files}
    except GithubException as e:
        return {"error": f"GitHub error: {e.status} {e.data}"}
    except Exception as e:
        return {"error": str(e)}
