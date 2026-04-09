import os
import re
import subprocess


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
