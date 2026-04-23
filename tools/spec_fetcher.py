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

"""Fetch requirements / user stories from Jira, Azure DevOps, or Qase.

Pipeline helper used alongside the existing source fetchers (fetch_local,
fetch_github, fetch_gitea) — it does NOT replace or alter them. Callers pass
an inline blob OR a provider URL, and this module returns a uniform
``{"source": "...", "title": "...", "body": "...", "provider": "..."}``
record ready to feed an LLM.
"""

from __future__ import annotations

import base64
import os
import re
from typing import Optional
from urllib.parse import urlparse

import requests


class SpecFetchError(RuntimeError):
    pass


# ── Detection ────────────────────────────────────────────────────────────────

_JIRA_RE = re.compile(r"https?://([^/]+)/browse/([A-Z][A-Z0-9_]+-\d+)", re.I)
_ADO_RE = re.compile(
    r"https?://dev\.azure\.com/([^/]+)/([^/]+)/_workitems/edit/(\d+)", re.I)
_QASE_RE = re.compile(r"https?://app\.qase\.io/case/([A-Z0-9]+)-(\d+)", re.I)


def detect_provider(text: str) -> str:
    if _JIRA_RE.search(text or ""):
        return "jira"
    if _ADO_RE.search(text or ""):
        return "azure_devops"
    if _QASE_RE.search(text or ""):
        return "qase"
    return "inline"


# ── Jira ─────────────────────────────────────────────────────────────────────

def _fetch_jira(url: str, email: Optional[str], token: Optional[str]) -> dict:
    m = _JIRA_RE.search(url)
    if not m:
        raise SpecFetchError("Not a recognised Jira browse URL.")
    host, key = m.group(1), m.group(2)
    api = f"https://{host}/rest/api/3/issue/{key}"
    headers = {"Accept": "application/json"}
    auth = None
    if email and token:
        auth = (email, token)
    elif token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.get(api, headers=headers, auth=auth, timeout=30)
    if r.status_code >= 400:
        raise SpecFetchError(f"Jira API {r.status_code}: {r.text[:200]}")
    j = r.json()
    fields = j.get("fields", {}) or {}
    body_parts = []
    desc = fields.get("description")
    if isinstance(desc, dict):
        body_parts.append(_adf_to_text(desc))
    elif isinstance(desc, str):
        body_parts.append(desc)
    ac = fields.get("customfield_10601") or fields.get("acceptance_criteria")
    if ac:
        body_parts.append(f"\n\nAcceptance Criteria:\n{ac}")
    return {
        "source": url,
        "title": f"[{key}] {fields.get('summary', '').strip()}",
        "body": "\n".join(p for p in body_parts if p).strip() or "(no description)",
        "provider": "jira",
    }


def _adf_to_text(node: dict) -> str:
    """Best-effort flatten of Jira's Atlassian Document Format."""
    out: list[str] = []

    def walk(n):
        if isinstance(n, dict):
            if n.get("type") == "text":
                out.append(n.get("text", ""))
            for child in n.get("content", []) or []:
                walk(child)
            if n.get("type") in ("paragraph", "listItem", "heading"):
                out.append("\n")
        elif isinstance(n, list):
            for child in n:
                walk(child)

    walk(node)
    return "".join(out).strip()


# ── Azure DevOps ─────────────────────────────────────────────────────────────

def _fetch_ado(url: str, pat: Optional[str]) -> dict:
    m = _ADO_RE.search(url)
    if not m:
        raise SpecFetchError("Not a recognised Azure DevOps work-item URL.")
    org, project, wid = m.group(1), m.group(2), m.group(3)
    api = (f"https://dev.azure.com/{org}/{project}/_apis/wit/workitems/"
           f"{wid}?$expand=all&api-version=7.0")
    headers = {"Accept": "application/json"}
    if pat:
        token = base64.b64encode(f":{pat}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    r = requests.get(api, headers=headers, timeout=30)
    if r.status_code >= 400:
        raise SpecFetchError(f"ADO API {r.status_code}: {r.text[:200]}")
    j = r.json()
    f = j.get("fields", {}) or {}
    body = "\n\n".join(filter(None, [
        _strip_html(f.get("System.Description") or ""),
        "Acceptance Criteria:\n" + _strip_html(f.get("Microsoft.VSTS.Common.AcceptanceCriteria") or "")
            if f.get("Microsoft.VSTS.Common.AcceptanceCriteria") else "",
    ])).strip()
    return {
        "source": url,
        "title": f"[WI-{wid}] {f.get('System.Title', '').strip()}",
        "body": body or "(no description)",
        "provider": "azure_devops",
    }


def _strip_html(s: str) -> str:
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</p>", "\n\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


# ── Qase ─────────────────────────────────────────────────────────────────────

def _fetch_qase(url: str, token: Optional[str]) -> dict:
    m = _QASE_RE.search(url)
    if not m:
        raise SpecFetchError("Not a recognised Qase case URL.")
    project, case_id = m.group(1), m.group(2)
    api = f"https://api.qase.io/v1/case/{project}/{case_id}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Token"] = token
    r = requests.get(api, headers=headers, timeout=30)
    if r.status_code >= 400:
        raise SpecFetchError(f"Qase API {r.status_code}: {r.text[:200]}")
    j = (r.json() or {}).get("result", {})
    body = "\n\n".join(filter(None, [
        j.get("description") or "",
        "Preconditions:\n" + j["preconditions"] if j.get("preconditions") else "",
        "Expected:\n" + j["expected_result"] if j.get("expected_result") else "",
    ])).strip()
    return {
        "source": url,
        "title": f"[{project}-{case_id}] {j.get('title', '').strip()}",
        "body": body or "(no description)",
        "provider": "qase",
    }


# ── Public entry point ───────────────────────────────────────────────────────

def fetch_spec(text_or_url: str,
               jira_email: Optional[str] = None,
               jira_token: Optional[str] = None,
               ado_pat: Optional[str] = None,
               qase_token: Optional[str] = None) -> dict:
    """Return a normalised spec record.

    ``text_or_url`` may be a raw user-story blob or a supported provider URL.
    Credentials are optional — public Jira instances often allow anonymous read.
    """
    if not text_or_url or not text_or_url.strip():
        raise SpecFetchError("Empty spec input.")

    provider = detect_provider(text_or_url)
    if provider == "jira":
        return _fetch_jira(
            text_or_url,
            jira_email or os.getenv("JIRA_EMAIL"),
            jira_token or os.getenv("JIRA_TOKEN"),
        )
    if provider == "azure_devops":
        return _fetch_ado(text_or_url, ado_pat or os.getenv("ADO_PAT"))
    if provider == "qase":
        return _fetch_qase(text_or_url, qase_token or os.getenv("QASE_TOKEN"))

    # Inline: treat the blob itself as the body.
    first_line = text_or_url.strip().splitlines()[0][:120]
    return {
        "source": "inline",
        "title": first_line,
        "body": text_or_url.strip(),
        "provider": "inline",
    }
