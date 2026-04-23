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

"""Deterministic SonarQube API fetcher.

Subagent for F11 (sonar_fix_agent). Uses only Python stdlib urllib
to fetch open issues from a Sonar instance's /api/issues/search
endpoint. Paginates; respects Retry-After on 429.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class SonarFetchError(RuntimeError):
    pass


def fetch_issues(sonar_url: str, project_key: str, token: str,
                 statuses: tuple[str, ...] = ("OPEN", "CONFIRMED"),
                 page_size: int = 100,
                 max_total: int = 500,
                 max_retries: int = 3) -> list[dict]:
    """Fetch normalised open issues for a Sonar project.

    Returns: [{rule, severity, component, line, message, effort, textRange}, ...]
    Raises SonarFetchError on auth failure or invalid response.
    """
    base = sonar_url.rstrip("/")
    collected: list[dict] = []
    page = 1
    while len(collected) < max_total:
        url = f"{base}/api/issues/search?" + urllib.parse.urlencode({
            "projectKeys": project_key,
            "statuses": ",".join(statuses),
            "p": page,
            "ps": page_size,
        })
        req = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        })
        body = _request_with_retry(req, max_retries=max_retries)
        if body is None:
            break
        issues = body.get("issues") or []
        for raw in issues:
            collected.append({
                "rule": raw.get("rule"),
                "severity": raw.get("severity"),
                "component": raw.get("component"),
                "line": raw.get("line"),
                "message": raw.get("message"),
                "effort": raw.get("effort"),
                "textRange": raw.get("textRange"),
            })
        total = body.get("total") or 0
        if page * page_size >= total or not issues:
            break
        page += 1
    return collected[:max_total]


def _request_with_retry(req: urllib.request.Request,
                        max_retries: int = 3) -> dict | None:
    delay = 1.0
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req) as resp:
                status = getattr(resp, "status", resp.getcode())
                if status == 429:
                    wait = float(resp.headers.get("Retry-After") or delay)
                    time.sleep(wait)
                    delay *= 2
                    continue
                if status in (401, 403):
                    raise SonarFetchError(f"auth failed (status {status})")
                if status >= 400:
                    raise SonarFetchError(f"sonar API returned status {status}")
                data = resp.read()
                try:
                    return json.loads(data.decode("utf-8", errors="replace"))
                except ValueError as exc:
                    raise SonarFetchError(f"invalid JSON from sonar: {exc}")
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < max_retries - 1:
                wait = float(exc.headers.get("Retry-After") or delay)
                time.sleep(wait)
                delay *= 2
                continue
            if exc.code in (401, 403):
                raise SonarFetchError(f"auth failed (status {exc.code})")
            raise SonarFetchError(f"sonar HTTP error {exc.code}: {exc.reason}")
        except urllib.error.URLError as exc:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
                continue
            raise SonarFetchError(f"sonar URL error: {exc.reason}")
    raise SonarFetchError("sonar exceeded max retries")
