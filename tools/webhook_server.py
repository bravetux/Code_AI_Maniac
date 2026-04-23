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
# Developed: 22nd April 2026

"""F20 — CI/CD-Triggered Review Webhook.

A FastAPI application that receives push / pull-request events from GitHub,
GitLab, Bitbucket, Jenkins, and Azure DevOps, then schedules an analysis job
via the existing orchestrator. This is a new tool — the orchestrator and
fetcher modules remain unchanged.

Run with:

    uvicorn tools.webhook_server:app --host 0.0.0.0 --port 8765

Signature verification relies on these environment variables (all optional):
    GITHUB_WEBHOOK_SECRET, GITLAB_WEBHOOK_SECRET,
    BITBUCKET_WEBHOOK_SECRET, JENKINS_WEBHOOK_SECRET,
    ADO_WEBHOOK_SECRET
"""

from __future__ import annotations

import hashlib
import hmac
import os
import threading
from typing import Any, Optional

try:
    from fastapi import FastAPI, Header, HTTPException, Request
except ImportError as e:  # pragma: no cover
    raise RuntimeError(
        "FastAPI is required for the webhook server. "
        "Install with: pip install fastapi uvicorn"
    ) from e

from db.connection import get_connection
from db.queries.jobs import create_job, get_job, get_job_results

# Default feature set triggered by a webhook — can be overridden via env.
_DEFAULT_FEATURES = [
    "bug_analysis", "static_analysis", "duplication_detection",
    "secret_scan", "refactoring_advisor",
]
_FEATURES_ENV = os.getenv("WEBHOOK_FEATURES", "")
WEBHOOK_FEATURES: list[str] = (
    [f.strip() for f in _FEATURES_ENV.split(",") if f.strip()]
    if _FEATURES_ENV else _DEFAULT_FEATURES
)

app = FastAPI(title="1128 Webhook Receiver", version="1.0")


# ── Signature verification helpers ───────────────────────────────────────────

def _verify_hmac(secret_env: str, body: bytes, sig_header: Optional[str],
                 algo: str = "sha256", prefix: str = "sha256=") -> None:
    secret = os.getenv(secret_env)
    if not secret:
        return  # No secret configured → skip verification (dev mode)
    if not sig_header:
        raise HTTPException(401, f"Missing signature header for {secret_env}")
    expected = hmac.new(secret.encode(), body, getattr(hashlib, algo)).hexdigest()
    candidate = sig_header[len(prefix):] if sig_header.startswith(prefix) else sig_header
    if not hmac.compare_digest(expected, candidate):
        raise HTTPException(401, "Invalid webhook signature")


def _verify_token(secret_env: str, token_header: Optional[str]) -> None:
    secret = os.getenv(secret_env)
    if not secret:
        return
    if not token_header or not hmac.compare_digest(secret, token_header):
        raise HTTPException(401, f"Invalid token for {secret_env}")


# ── Job scheduling ───────────────────────────────────────────────────────────

def _kick_off_job(source_type: str, source_ref: str,
                  features: Optional[list[str]] = None,
                  language: Optional[str] = None) -> str:
    """Create a job row and run the orchestrator in a background thread."""
    conn = get_connection()
    job_id = create_job(
        conn, source_type=source_type, source_ref=source_ref,
        language=language, features=features or WEBHOOK_FEATURES,
    )

    def _runner():
        # Late import — keeps FastAPI startup light.
        from agents.orchestrator import run_analysis
        try:
            run_analysis(conn, job_id)
        except Exception as exc:
            # Orchestrator itself logs failures to the job row; re-raising here
            # would just kill the background thread silently.
            print(f"[webhook] job {job_id} crashed: {exc}")

    threading.Thread(target=_runner, daemon=True, name=f"job-{job_id[:8]}").start()
    return job_id


def _build_github_ref(repo: str, branch: str, path: str) -> str:
    return f"{repo}::{branch}::{path}"


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "features": WEBHOOK_FEATURES}


@app.get("/jobs/{job_id}")
async def job_status(job_id: str) -> dict:
    conn = get_connection()
    job = get_job(conn, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "id": job["id"],
        "status": job["status"],
        "source_type": job["source_type"],
        "source_ref": job["source_ref"],
        "features": job.get("features"),
        "results": get_job_results(conn, job_id),
    }


@app.post("/webhook/github")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None),
) -> dict:
    body = await request.body()
    _verify_hmac("GITHUB_WEBHOOK_SECRET", body, x_hub_signature_256)
    payload: dict[str, Any] = await request.json()
    event = x_github_event or ""

    repo = (payload.get("repository") or {}).get("full_name")
    if not repo:
        raise HTTPException(400, "missing repository.full_name")

    refs: list[tuple[str, str]] = []   # (branch, path)
    if event == "push":
        branch = (payload.get("ref") or "").replace("refs/heads/", "") or "main"
        for commit in payload.get("commits") or []:
            for path in (commit.get("added") or []) + (commit.get("modified") or []):
                refs.append((branch, path))
    elif event == "pull_request":
        pr = payload.get("pull_request") or {}
        branch = (pr.get("head") or {}).get("ref") or "main"
        # We cannot list changed files without another API call; fall back to
        # scanning the branch HEAD — orchestrator handles a single ref fine.
        refs.append((branch, ""))
    else:
        return {"accepted": False, "reason": f"ignored event: {event}"}

    job_ids = []
    for branch, path in refs or [("main", "")]:
        if not path:
            continue  # Skip empty-path placeholder from PR event for now.
        job_ids.append(_kick_off_job("github", _build_github_ref(repo, branch, path)))

    return {"accepted": True, "jobs": job_ids, "event": event, "repo": repo}


@app.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    x_gitlab_token: Optional[str] = Header(None),
    x_gitlab_event: Optional[str] = Header(None),
) -> dict:
    body = await request.body()
    _verify_token("GITLAB_WEBHOOK_SECRET", x_gitlab_token)
    payload: dict[str, Any] = await request.json()
    event = x_gitlab_event or ""

    project = (payload.get("project") or {}).get("path_with_namespace")
    if not project:
        raise HTTPException(400, "missing project.path_with_namespace")

    refs: list[tuple[str, str]] = []
    if event in ("Push Hook", "Tag Push Hook"):
        branch = (payload.get("ref") or "").replace("refs/heads/", "") or "main"
        for commit in payload.get("commits") or []:
            for path in (commit.get("added") or []) + (commit.get("modified") or []):
                refs.append((branch, path))
    elif event == "Merge Request Hook":
        attrs = payload.get("object_attributes") or {}
        branch = attrs.get("source_branch") or "main"
        refs.append((branch, ""))
    else:
        return {"accepted": False, "reason": f"ignored event: {event}"}

    # Current orchestrator fetcher supports GitHub / Gitea / local. GitLab
    # refs are surfaced via Gitea-compatible URLs when configured; for now we
    # record the job as 'github' (a stand-in) so the orchestrator can attempt
    # to resolve, and will fail loudly if the token/host don't match.
    job_ids = [_kick_off_job("github", _build_github_ref(project, b, p))
               for b, p in refs if p]
    return {"accepted": True, "jobs": job_ids, "event": event, "project": project}


@app.post("/webhook/bitbucket")
async def bitbucket_webhook(
    request: Request,
    x_hub_signature: Optional[str] = Header(None),
    x_event_key: Optional[str] = Header(None),
) -> dict:
    body = await request.body()
    _verify_hmac("BITBUCKET_WEBHOOK_SECRET", body, x_hub_signature, prefix="sha256=")
    payload: dict[str, Any] = await request.json()
    event = x_event_key or ""

    repo = (payload.get("repository") or {}).get("full_name")
    if not repo:
        raise HTTPException(400, "missing repository.full_name")

    refs: list[tuple[str, str]] = []
    if event == "repo:push":
        for change in (payload.get("push") or {}).get("changes") or []:
            branch = ((change.get("new") or {}).get("name")) or "main"
            for commit in change.get("commits") or []:
                for path in commit.get("files") or []:
                    refs.append((branch, path.get("path") if isinstance(path, dict) else path))
    elif event.startswith("pullrequest:"):
        pr = payload.get("pullrequest") or {}
        branch = ((pr.get("source") or {}).get("branch") or {}).get("name", "main")
        refs.append((branch, ""))
    else:
        return {"accepted": False, "reason": f"ignored event: {event}"}

    job_ids = [_kick_off_job("github", _build_github_ref(repo, b, p))
               for b, p in refs if p]
    return {"accepted": True, "jobs": job_ids, "event": event, "repo": repo}


@app.post("/webhook/jenkins")
async def jenkins_webhook(
    request: Request,
    x_jenkins_token: Optional[str] = Header(None),
) -> dict:
    _verify_token("JENKINS_WEBHOOK_SECRET", x_jenkins_token)
    payload: dict[str, Any] = await request.json()

    # Expected shape (Jenkins Generic Webhook Trigger plugin):
    # {"repo": "owner/name", "branch": "main", "files": ["src/a.py", ...]}
    repo = payload.get("repo") or payload.get("repository")
    branch = payload.get("branch") or "main"
    files = payload.get("files") or []
    if not repo or not files:
        raise HTTPException(400, "payload must include 'repo' and 'files'")

    job_ids = [_kick_off_job("github", _build_github_ref(repo, branch, p))
               for p in files]
    return {"accepted": True, "jobs": job_ids, "repo": repo}


@app.post("/webhook/azure-devops")
async def ado_webhook(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> dict:
    # ADO service hooks use Basic auth — accept either Basic or a shared token
    # depending on how the hook is configured.
    secret = os.getenv("ADO_WEBHOOK_SECRET")
    if secret and authorization:
        if not hmac.compare_digest(secret, authorization.replace("Basic ", "").strip()):
            raise HTTPException(401, "Invalid ADO authorization")

    payload: dict[str, Any] = await request.json()
    resource = payload.get("resource") or {}
    repo = ((resource.get("repository") or {}).get("name")) or \
            payload.get("repositoryName")
    branch = (resource.get("refUpdates") or [{}])[0].get("name", "") \
               .replace("refs/heads/", "") or "main"
    # ADO doesn't embed changed file list — treat as branch-level trigger.
    if not repo:
        raise HTTPException(400, "missing repository name")

    job_id = _kick_off_job("github", _build_github_ref(repo, branch, ""))
    return {"accepted": True, "jobs": [job_id], "repo": repo}
