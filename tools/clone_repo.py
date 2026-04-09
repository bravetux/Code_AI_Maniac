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
