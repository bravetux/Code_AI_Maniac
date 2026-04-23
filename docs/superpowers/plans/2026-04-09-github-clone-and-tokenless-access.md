# GitHub Clone & Token-Optional Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to paste a GitHub URL, clone public repos without a token, and analyze both files and full commit history from the clone.

**Architecture:** New `tools/clone_repo.py` provides URL parsing, git clone/pull, and local git log extraction. The source selector UI adds clone+browse flow for the GitHub option. The Commits page adds a "GitHub (Clone)" source that uses local git log. Token becomes optional everywhere for public repos.

**Tech Stack:** Python 3.11+, subprocess (git CLI), Streamlit, PyGithub, DuckDB

---

### Task 1: Create `tools/clone_repo.py` — URL Parser

**Files:**
- Create: `tools/clone_repo.py`
- Create: `tests/tools/test_clone_repo.py`

- [ ] **Step 1: Write failing test for URL parsing**

```python
# tests/tools/test_clone_repo.py
import pytest
from tools.clone_repo import parse_github_url


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_clone_repo.py::test_parse_github_url -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.clone_repo'`

- [ ] **Step 3: Implement `parse_github_url`**

```python
# tools/clone_repo.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_clone_repo.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tools/clone_repo.py tests/tools/test_clone_repo.py
git commit -m "feat: add GitHub URL parser in tools/clone_repo.py"
```

---

### Task 2: Add `clone_or_pull` to `tools/clone_repo.py`

**Files:**
- Modify: `tools/clone_repo.py`
- Modify: `tests/tools/test_clone_repo.py`

- [ ] **Step 1: Write failing test for clone_or_pull**

Append to `tests/tools/test_clone_repo.py`:

```python
import shutil
from pathlib import Path
from tools.clone_repo import clone_or_pull, parse_github_url

REPOS_DIR = Path("data/repos")


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_clone_repo.py::test_clone_public_repo -v`
Expected: FAIL — `ImportError: cannot import name 'clone_or_pull'`

- [ ] **Step 3: Implement `clone_or_pull`**

Add to `tools/clone_repo.py`:

```python
REPOS_BASE = os.path.join("data", "repos")


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_clone_repo.py -v`
Expected: All PASS (clone test requires network; may take 10-30s)

- [ ] **Step 5: Commit**

```bash
git add tools/clone_repo.py tests/tools/test_clone_repo.py
git commit -m "feat: add clone_or_pull for GitHub repos"
```

---

### Task 3: Add `get_git_log` to `tools/clone_repo.py`

**Files:**
- Modify: `tools/clone_repo.py`
- Modify: `tests/tools/test_clone_repo.py`

- [ ] **Step 1: Write failing test for get_git_log**

Append to `tests/tools/test_clone_repo.py`:

```python
from tools.clone_repo import get_git_log


def test_get_git_log_with_limit(tmp_path, monkeypatch):
    """Get limited commits from a cloned repo."""
    monkeypatch.setattr("tools.clone_repo.REPOS_BASE", str(tmp_path / "repos"))
    clone_or_pull("bravetux/Code_AI_Maniac", branch="main")
    path = os.path.join(str(tmp_path / "repos"), "bravetux", "Code_AI_Maniac")
    commits = get_git_log(path, limit=5)
    assert len(commits) == 5
    assert "sha" in commits[0]
    assert "message" in commits[0]
    assert "author" in commits[0]
    assert "date" in commits[0]
    assert "files_changed" in commits[0]


def test_get_git_log_all(tmp_path, monkeypatch):
    """Get all commits (limit=None)."""
    monkeypatch.setattr("tools.clone_repo.REPOS_BASE", str(tmp_path / "repos"))
    clone_or_pull("bravetux/Code_AI_Maniac", branch="main")
    path = os.path.join(str(tmp_path / "repos"), "bravetux", "Code_AI_Maniac")
    commits = get_git_log(path, limit=None)
    assert len(commits) >= 1
    assert all("sha" in c for c in commits)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_clone_repo.py::test_get_git_log_with_limit -v`
Expected: FAIL — `ImportError: cannot import name 'get_git_log'`

- [ ] **Step 3: Implement `get_git_log`**

Add to `tools/clone_repo.py`:

```python
_LOG_SEP = "---COMMIT_SEP---"
_FIELD_SEP = "---FIELD_SEP---"


def get_git_log(repo_path: str, limit: int | None = None) -> list[dict]:
    """Extract commit history from a local git repo.

    Args:
        repo_path: Path to the cloned repo
        limit: Max commits to return. None = all commits.

    Returns: List of {"sha", "message", "author", "date", "files_changed"}
    """
    fmt = _FIELD_SEP.join(["%H", "%s", "%an", "%aI", ""])
    cmd = [
        "git", "-C", repo_path, "log",
        f"--pretty=format:{fmt}",
        "--stat",
    ]
    if limit is not None:
        cmd.extend(["-n", str(limit)])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        return []

    commits = []
    raw = result.stdout.strip()
    if not raw:
        return []

    # Split output into per-commit blocks by detecting the field separator pattern
    # Each commit starts with a hash (40 hex chars) preceded by our field sep in the format
    entries = raw.split(f"\n\n")

    current_commit = None
    for block in entries:
        block = block.strip()
        if not block:
            continue
        if _FIELD_SEP in block:
            # This block contains commit header
            if current_commit:
                commits.append(current_commit)
            parts = block.split(_FIELD_SEP)
            files_section = parts[4] if len(parts) > 4 else ""
            files = [
                line.strip().split("|")[0].strip()
                for line in files_section.strip().splitlines()
                if "|" in line
            ]
            current_commit = {
                "sha": parts[0][:8],
                "message": parts[1],
                "author": parts[2],
                "date": parts[3],
                "files_changed": files,
            }
        elif current_commit:
            # Continuation of stat block
            files = [
                line.strip().split("|")[0].strip()
                for line in block.splitlines()
                if "|" in line
            ]
            current_commit["files_changed"].extend(files)

    if current_commit:
        commits.append(current_commit)

    return commits
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/tools/test_clone_repo.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add tools/clone_repo.py tests/tools/test_clone_repo.py
git commit -m "feat: add get_git_log for local commit history extraction"
```

---

### Task 4: Make `fetch_github_file` token-optional

**Files:**
- Modify: `tools/fetch_github.py:17-23`
- Create: `tests/tools/test_fetch_github.py`

- [ ] **Step 1: Write failing test**

```python
# tests/tools/test_fetch_github.py
from tools.fetch_github import fetch_github_file


def test_fetch_public_repo_no_token():
    """Public repo should work without a token."""
    result = fetch_github_file(
        repo="bravetux/Code_AI_Maniac",
        file_path="README.md",
        branch="main",
        token=None,
    )
    assert "error" not in result
    assert "content" in result
    assert len(result["content"]) > 0


def test_fetch_private_repo_no_token():
    """Private repo without token should give helpful error."""
    result = fetch_github_file(
        repo="bravetux/some-private-repo-that-doesnt-exist",
        file_path="README.md",
        branch="main",
        token=None,
    )
    assert "error" in result
    assert "private" in result["error"].lower() or "GitHub error" in result["error"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/tools/test_fetch_github.py::test_fetch_public_repo_no_token -v`
Expected: FAIL — PyGithub may raise or return a confusing error when `token=None` is passed directly.

- [ ] **Step 3: Modify `fetch_github_file` to handle None/empty token**

In `tools/fetch_github.py`, replace lines 21-22:

```python
# Old:
    g = Github(token)

# New:
    g = Github(token) if token else Github()
```

And update the error handler at lines 46-47:

```python
# Old:
    except GithubException as e:
        return {"error": f"GitHub error: {e.status} {e.data}", "file_path": file_path}

# New:
    except GithubException as e:
        msg = f"GitHub error: {e.status} {e.data}"
        if e.status in (401, 403, 404) and not token:
            msg += " — this repository may be private. Provide a GitHub token to access it."
        return {"error": msg, "file_path": file_path}
```

- [ ] **Step 4: Apply same fix to `fetch_github_pr_diff`**

In `tools/fetch_github.py`, replace line 54:

```python
# Old:
    g = Github(token)

# New:
    g = Github(token) if token else Github()
```

And update lines 62-65:

```python
# Old:
    except GithubException as e:
        return {"error": f"GitHub error: {e.status} {e.data}"}

# New:
    except GithubException as e:
        msg = f"GitHub error: {e.status} {e.data}"
        if e.status in (401, 403, 404) and not token:
            msg += " — this repository may be private. Provide a GitHub token to access it."
        return {"error": msg}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/tools/test_fetch_github.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add tools/fetch_github.py tests/tools/test_fetch_github.py
git commit -m "feat: make GitHub token optional for public repos"
```

---

### Task 5: Update Source Selector — GitHub URL + Clone & Browse

**Files:**
- Modify: `app/components/source_selector.py:171-180`

- [ ] **Step 1: Add import for clone_repo at top of file**

At `app/components/source_selector.py` line 5, add:

```python
from tools.clone_repo import parse_github_url, clone_or_pull
```

- [ ] **Step 2: Replace the GitHub section (lines 171-180)**

Replace the `elif source_type == "GitHub":` block with:

```python
    elif source_type == "GitHub":
        result["source_type"] = "github"

        url_input = st.text_input(
            "GitHub URL / Repository",
            placeholder="https://github.com/owner/repo.git  or  owner/repo",
            key="github_url_input",
        )
        branch = st.text_input("Branch", value="main", key="github_branch")
        token = st.text_input(
            "GitHub token",
            value=s.github_token or "",
            type="password",
            help="Optional — only needed for private repos",
            key="github_token_input",
        )
        if token and token != s.github_token:
            st.session_state["github_token_override"] = token

        effective_token = token or s.github_token or None

        # --- Parse URL into owner/repo ---
        parsed = None
        if url_input:
            try:
                parsed = parse_github_url(url_input)
            except ValueError:
                st.error("Could not parse GitHub URL. Use `owner/repo` or a full URL.")

        # --- Clone & Browse / Re-pull ---
        if parsed:
            repo_slug = parsed["slug"]
            clone_dest = os.path.join("data", "repos", parsed["owner"], parsed["repo"])
            already_cloned = os.path.isdir(os.path.join(clone_dest, ".git"))

            col_clone, col_pull = st.columns(2)
            with col_clone:
                if st.button(
                    "🔄 Re-pull" if already_cloned else "📥 Clone & Browse",
                    key="clone_btn",
                    type="primary",
                ):
                    with st.spinner("Cloning repository..." if not already_cloned
                                    else "Pulling latest changes..."):
                        clone_result = clone_or_pull(
                            repo_slug, branch=branch, token=effective_token
                        )
                    if "error" in clone_result:
                        st.error(clone_result["error"])
                    else:
                        st.session_state["cloned_repo_path"] = clone_result["path"]
                        st.session_state["cloned_repo_slug"] = repo_slug
                        st.success(
                            f"{'Pulled' if clone_result['status'] == 'pulled' else 'Cloned'}"
                            f" to `{clone_result['path']}`"
                        )

            if already_cloned and "cloned_repo_path" not in st.session_state:
                st.session_state["cloned_repo_path"] = clone_dest
                st.session_state["cloned_repo_slug"] = repo_slug

            # --- File selection from cloned repo (folder-recursive reuse) ---
            cloned_path = st.session_state.get("cloned_repo_path")
            if cloned_path and os.path.isdir(cloned_path):
                st.divider()
                st.subheader("Select files to analyse")

                with st.expander("Filter by extension", expanded=False):
                    use_filter = st.checkbox(
                        "Filter by extension", value=True,
                        key="gh_folder_ext_filter",
                    )
                    if use_filter:
                        chosen_exts = st.multiselect(
                            "Extensions to include",
                            options=_DEFAULT_EXTENSIONS,
                            default=_DEFAULT_EXTENSIONS,
                            key="gh_folder_exts",
                        )
                    else:
                        chosen_exts = None

                all_files = scan_folder_recursive(
                    cloned_path,
                    extensions=chosen_exts if use_filter else None,
                )
                total_found = len(all_files)

                if total_found == 0:
                    st.info("No matching files found in the cloned repo.")
                else:
                    st.caption(
                        f"Found **{total_found}** file(s). "
                        f"Limit: **{max_files}** (MAX_FILES in .env)."
                    )

                    rel_map = {
                        os.path.relpath(p, cloned_path): p for p in all_files
                    }
                    rel_paths = list(rel_map.keys())
                    default_selected = rel_paths[:max_files]

                    selected_rel = st.multiselect(
                        f"Select files to analyse (max {max_files})",
                        options=rel_paths,
                        default=default_selected,
                        key="gh_folder_file_select",
                    )

                    if len(selected_rel) > max_files:
                        st.error(
                            f"Too many files selected ({len(selected_rel)}). "
                            f"Please deselect down to {max_files}."
                        )
                        selected_rel = selected_rel[:max_files]

                    if selected_rel:
                        selected_abs = [rel_map[r] for r in selected_rel]
                        # Treat cloned files as local source
                        result["source_type"] = "local"
                        result["source_ref"] = "::".join(selected_abs)
                        st.caption(f"{len(selected_rel)} file(s) selected.")

            # --- Fallback: single file via API (no clone needed) ---
            elif not cloned_path:
                st.divider()
                file_path = st.text_input("Or enter a single file path (API fetch)",
                                          placeholder="src/main.py",
                                          key="github_file_path")
                if parsed and branch and file_path:
                    result["source_ref"] = f"{repo_slug}::{branch}::{file_path}"
```

- [ ] **Step 3: Run the app and manually verify the GitHub UI**

Run: `streamlit run app/Home.py`
Verify:
1. GitHub option shows URL input field
2. Pasting `https://github.com/bravetux/Code_AI_Maniac.git` parses correctly
3. "Clone & Browse" button appears and clones the repo
4. File selection UI appears after clone
5. "Re-pull" shows on subsequent visits
6. Single file API fallback still works when no clone done

- [ ] **Step 4: Commit**

```bash
git add app/components/source_selector.py
git commit -m "feat: GitHub URL input with clone & browse in source selector"
```

---

### Task 6: Update Commits Page — Three Source Options + All Commits

**Files:**
- Modify: `app/pages/3_Commits.py` (full rewrite)

- [ ] **Step 1: Rewrite `3_Commits.py` with three source options**

Replace the entire content of `app/pages/3_Commits.py`:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import create_job
from agents.commit_analysis import run_commit_analysis
from config.settings import get_settings
from app.components.result_tabs import render_results
from tools.clone_repo import parse_github_url, clone_or_pull, get_git_log

st.set_page_config(page_title="Commits — AI Code Maniac", layout="wide")
st.title("Commit Analysis")

conn = get_connection()
init_schema(conn)
s = get_settings()

source = st.radio("Source", ["GitHub (Clone)", "GitHub (API)", "Gitea"], horizontal=True)

custom_prompt = None
with st.expander("Advanced / Fine-tune"):
    custom_prompt = st.text_area("System Prompt override", height=80) or None

if source == "GitHub (Clone)":
    url_input = st.text_input(
        "GitHub URL / Repository",
        placeholder="https://github.com/owner/repo.git  or  owner/repo",
        key="commits_github_url",
    )
    branch = st.text_input("Branch", value="main", key="commits_branch")
    token = st.text_input(
        "GitHub token", value=s.github_token or "", type="password",
        help="Optional — only needed for private repos",
        key="commits_github_token",
    )
    effective_token = token or s.github_token or None

    all_commits_flag = st.checkbox("All commits", value=False, key="all_commits")
    if all_commits_flag:
        limit = None
        st.caption("Will analyse all commits in the repository.")
    else:
        limit = st.slider("Number of commits to analyze", 5, 500, 50,
                           key="commits_limit_clone")

    parsed = None
    if url_input:
        try:
            parsed = parse_github_url(url_input)
        except ValueError:
            st.error("Could not parse GitHub URL. Use `owner/repo` or a full URL.")

    if st.button("Clone & Analyze Commits", type="primary",
                 key="clone_analyze_btn") and parsed:
        repo_slug = parsed["slug"]

        with st.spinner("Cloning / pulling repository..."):
            clone_result = clone_or_pull(repo_slug, branch=branch,
                                         token=effective_token)
        if "error" in clone_result:
            st.error(clone_result["error"])
        else:
            st.success(f"Repository ready at `{clone_result['path']}`")

            with st.spinner("Reading commit history..."):
                commits = get_git_log(clone_result["path"], limit=limit)

            if commits:
                st.info(f"Found {len(commits)} commit(s).")
                job_id = create_job(
                    conn, source_type="github",
                    source_ref=f"{repo_slug}::{branch}",
                    language=None, features=["commit_analysis"],
                )
                with st.spinner("Analyzing commits with AI..."):
                    result = run_commit_analysis(
                        conn=conn, job_id=job_id,
                        repo_ref=f"{repo_slug}::{branch}",
                        commits=commits, custom_prompt=custom_prompt,
                    )
                render_results({"commit_analysis": result})
            else:
                st.warning("No commits found in the repository.")

elif source == "GitHub (API)":
    repo = st.text_input("Repository (owner/repo)", key="commits_api_repo")
    branch = st.text_input("Branch", value="main", key="commits_api_branch")
    token = st.text_input(
        "GitHub token", value=s.github_token or "", type="password",
        help="Optional — only needed for private repos",
        key="commits_api_token",
    )
    limit = st.slider("Number of commits to analyze", 5, 100, 20,
                       key="commits_limit_api")

    if st.button("Fetch & Analyze Commits", type="primary",
                 key="api_analyze_btn") and repo:
        effective_token = token or s.github_token or None
        with st.spinner("Fetching commits via API..."):
            from github import Github
            g = Github(effective_token) if effective_token else Github()
            try:
                r = g.get_repo(repo)
                commits = [
                    {"sha": c.sha[:8], "message": c.commit.message,
                     "author": c.commit.author.name}
                    for c in r.get_commits(sha=branch)[:limit]
                ]
            except Exception as e:
                commits = []
                st.error(f"GitHub API error: {e}")

        if commits:
            job_id = create_job(
                conn, source_type="github",
                source_ref=f"{repo}::{branch}",
                language=None, features=["commit_analysis"],
            )
            with st.spinner("Analyzing commits with AI..."):
                result = run_commit_analysis(
                    conn=conn, job_id=job_id,
                    repo_ref=f"{repo}::{branch}",
                    commits=commits, custom_prompt=custom_prompt,
                )
            render_results({"commit_analysis": result})
        elif not st.session_state.get("_api_error"):
            st.warning("No commits found or fetch failed.")

else:  # Gitea
    from tools.fetch_gitea import fetch_gitea_commits
    repo = st.text_input("Repository (owner/repo)", key="commits_gitea_repo")
    branch = st.text_input("Branch", value="main", key="commits_gitea_branch")
    limit = st.slider("Number of commits to analyze", 5, 100, 20,
                       key="commits_limit_gitea")

    if st.button("Fetch & Analyze Commits", type="primary",
                 key="gitea_analyze_btn") and repo:
        with st.spinner("Fetching commits from Gitea..."):
            result = fetch_gitea_commits(
                gitea_url=s.gitea_url, repo=repo,
                branch=branch, token=s.gitea_token, limit=limit,
            )
            commits = result.get("commits", [])

        if commits:
            job_id = create_job(
                conn, source_type="gitea",
                source_ref=f"{repo}::{branch}",
                language=None, features=["commit_analysis"],
            )
            with st.spinner("Analyzing commits with AI..."):
                result = run_commit_analysis(
                    conn=conn, job_id=job_id,
                    repo_ref=f"{repo}::{branch}",
                    commits=commits, custom_prompt=custom_prompt,
                )
            render_results({"commit_analysis": result})
        else:
            st.warning("No commits found or fetch failed.")
```

- [ ] **Step 2: Run the app and manually verify the Commits page**

Run: `streamlit run app/Home.py`
Verify:
1. Three source radio buttons appear: GitHub (Clone), GitHub (API), Gitea
2. GitHub (Clone): paste URL → Clone & Analyze → shows commits → AI analysis
3. "All commits" checkbox disables slider
4. GitHub (API): works without token for public repos
5. Gitea: unchanged behavior

- [ ] **Step 3: Commit**

```bash
git add app/pages/3_Commits.py
git commit -m "feat: Commits page with clone, API, and Gitea sources + all commits option"
```

---

### Task 7: Wire Up Token Override in Orchestrator

**Files:**
- Modify: `agents/orchestrator.py:27,50-57`

- [ ] **Step 1: Update `_fetch_files` GitHub branch to use token override**

In `agents/orchestrator.py`, replace lines 50-57:

```python
# Old:
    elif source_type == "github":
        parts  = source_ref.split("::")   # owner/repo :: branch :: path
        result = fetch_github_file(repo=parts[0], file_path=parts[2],
                                   branch=parts[1], token=s.github_token)
        if "error" in result:
            raise RuntimeError(result["error"])
        return [{"file_path": parts[2], "content": result["content"],
                 "file_hash": result["file_hash"]}]

# New:
    elif source_type == "github":
        parts  = source_ref.split("::")   # owner/repo :: branch :: path
        token  = s.github_token
        try:
            import streamlit as st
            token = st.session_state.get("github_token_override", token)
        except Exception:
            pass
        result = fetch_github_file(repo=parts[0], file_path=parts[2],
                                   branch=parts[1], token=token or None)
        if "error" in result:
            raise RuntimeError(result["error"])
        return [{"file_path": parts[2], "content": result["content"],
                 "file_hash": result["file_hash"]}]
```

- [ ] **Step 2: Run existing tests to verify nothing broke**

Run: `pytest -v`
Expected: All existing tests still PASS

- [ ] **Step 3: Commit**

```bash
git add agents/orchestrator.py
git commit -m "feat: wire up GitHub token override from session state in orchestrator"
```

---

### Task 8: Integration Test — Full Clone-to-Analysis Flow

**Files:**
- Create: `tests/integration/test_clone_flow.py`

- [ ] **Step 1: Write integration test**

```python
# tests/integration/test_clone_flow.py
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
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/integration/test_clone_flow.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/integration/test_clone_flow.py
git commit -m "test: add integration test for clone-to-analysis flow"
```

---

## Summary of All Changes

| Task | File | Action |
|------|------|--------|
| 1-3 | `tools/clone_repo.py` | **NEW** — `parse_github_url`, `clone_or_pull`, `get_git_log` |
| 1-3 | `tests/tools/test_clone_repo.py` | **NEW** — unit tests for all three functions |
| 4 | `tools/fetch_github.py` | Token-optional `Github()`, better error messages |
| 4 | `tests/tools/test_fetch_github.py` | **NEW** — tests for tokenless access |
| 5 | `app/components/source_selector.py` | URL input, clone button, folder-recursive file selection |
| 6 | `app/pages/3_Commits.py` | Three sources, all-commits checkbox, clone-based commit log |
| 7 | `agents/orchestrator.py` | Token override from session state |
| 8 | `tests/integration/test_clone_flow.py` | **NEW** — end-to-end integration test |
