# GitHub Clone & Token-Optional Access Design

**Date:** 2026-04-09
**Status:** Approved

## Problem

The current GitHub integration requires `owner/repo` format input plus a token. Users want to:
1. Paste a full GitHub URL (e.g., `https://github.com/bravetux/Code_AI_Maniac.git`) and have it parsed automatically
2. Analyze public repos without needing a GitHub token
3. Clone full repo history for commit analysis with all agents able to analyze cloned files

## Solution Overview

Two complementary approaches:

- **Primary: Clone-as-Local-Source** — `git clone` the repo to `data/repos/<owner>/<repo>/`, use `git log` for commit history, treat cloned files as local source for all agents
- **Fallback: Token-optional GitHub API** — lightweight commit-only analysis via PyGithub without requiring a token for public repos

## New File: `tools/clone_repo.py`

### URL Parser — `parse_github_url(url_or_slug) -> dict`

Accepts and normalizes these formats:
- `https://github.com/bravetux/Code_AI_Maniac.git`
- `https://github.com/bravetux/Code_AI_Maniac`
- `github.com/bravetux/Code_AI_Maniac`
- `bravetux/Code_AI_Maniac` (passthrough)

Returns `{"owner": "bravetux", "repo": "Code_AI_Maniac", "slug": "bravetux/Code_AI_Maniac"}`.

### Clone function — `clone_or_pull(repo_slug, branch="main", token=None) -> dict`

- Target directory: `data/repos/<owner>/<repo>/`
- If directory exists and is a git repo → `git pull`
- If not → `git clone`
- Token handling:
  - Token provided → `https://<token>@github.com/owner/repo.git` (private repos)
  - No token → `https://github.com/owner/repo.git` (public repos)
- Returns `{"path": "...", "status": "cloned|pulled", "error": ...}`

### Commit log — `get_git_log(repo_path, limit=None) -> list[dict]`

- Runs `git log --pretty=format:...` with `--stat`
- Returns `[{"sha", "message", "author", "date", "files_changed"}, ...]`
- `limit=None` returns all commits
- Fast local operation, no API limits

## Modified: `app/components/source_selector.py` — GitHub Option

Current fields: `Repository (owner/repo)`, `Branch`, `File path`, `GitHub token`

New flow:

1. **GitHub URL / Repository** — single text input accepting both URL and `owner/repo` format. Auto-parsed via `parse_github_url()`.
2. **Branch** — text input, default "main"
3. **GitHub token** — optional, helper text: "Optional — only needed for private repos"
4. **Clone & Browse** button — triggers `clone_or_pull()`, then displays folder-recursive file selection UI pointing at the cloned repo
5. **Re-pull** button — shown if repo already cloned, runs `git pull` to refresh

After clone, reuses the existing folder-recursive UI (extension filter, checkboxes, max 50 files). `source_type` set to `"local"`, `source_ref` points to selected files from `data/repos/...`.

## Modified: `app/pages/3_Commits.py`

Source radio gains three options: `GitHub (Clone)` | `GitHub (API)` | `Gitea`

### GitHub (Clone) path
- URL/repo input + branch + optional token
- "Clone & Load" button → `clone_or_pull()`
- Commit range: slider 5-500 (default 50) + "All commits" checkbox
- All commits checked → slider disabled, `limit=None`
- Commits from `get_git_log()` — includes sha, message, author, date, files_changed
- Passes to existing `run_commit_analysis()` agent

### GitHub (API) path — existing behavior preserved
- Token optional for public repos (unauthenticated PyGithub)
- Slider 5-100, default 20

### Gitea path — unchanged

## Modified: `tools/fetch_github.py` — Token-Optional

- `Github(token)` when token provided → authenticated (5000 req/hr)
- `Github()` when token is `None` or empty → unauthenticated (60 req/hr, public repos only)
- Clear error message for private repo access without token: "This repository may be private. Provide a GitHub token to access it."

## Modified: `agents/orchestrator.py`

- Wire up `session_state["github_token_override"]` so manually-entered tokens get used
- When `source_type == "github"` with a cloned repo path, treat as local source

## Database: `repo_metadata` table (already exists)

- `upsert_repo()` after clone/pull with repo URL, branch, last_synced, commit_count
- Shows "last synced" info in UI, avoids unnecessary re-clones

## End-to-End Flows

### Flow 1: GitHub URL → Clone → File Analysis (Analysis page)
```
Paste URL → parse owner/repo → Clone & Browse
  → git clone to data/repos/owner/repo/
  → folder-recursive UI → select files
  → orchestrator runs all agents on selected files (local source)
```

### Flow 2: GitHub URL → Clone → Commit Analysis (Commits page)
```
Paste URL → parse owner/repo → Clone & Load
  → git clone to data/repos/owner/repo/
  → git log → enriched commits (sha, message, author, date, files_changed)
  → run_commit_analysis()
```

### Flow 3: GitHub API → Quick Commit Analysis (Commits page)
```
Enter owner/repo → token optional for public repos
  → PyGithub fetches commits (API, rate limited)
  → run_commit_analysis()
```

## Unchanged Components

- All 8 agents — no logic changes
- Gitea flow
- Local file flow
- Database schema (tables already exist)
- Result rendering

## Files Changed Summary

| File | Change |
|------|--------|
| `tools/clone_repo.py` | **NEW** — URL parser, clone/pull, git log |
| `app/components/source_selector.py` | URL input, clone button, folder-recursive after clone |
| `app/pages/3_Commits.py` | Three source options, all commits checkbox |
| `tools/fetch_github.py` | Token-optional PyGithub |
| `agents/orchestrator.py` | Token override wiring |
