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

"""F11 — SonarQube Fix Automation.

Ingests Sonar issues via three channels (prefix, JSON source, API fetch)
and emits PR-ready patches per source file. Issues sorted by severity
and capped at __sonar_top_n__ (default 50) before LLM processing.
"""

from __future__ import annotations

import json
import os
import re
from collections import defaultdict
from datetime import datetime

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.patch_emitter import emit as emit_patch
from tools.sonar_fetcher import fetch_issues, SonarFetchError
from db.queries.history import add_history

_CACHE_KEY = "sonar_fix_agent"

_SEVERITY_RANK = {"BLOCKER": 0, "CRITICAL": 1, "MAJOR": 2, "MINOR": 3, "INFO": 4}
_DEFAULT_TOP_N = 50


def _report_ts() -> str:
    return (os.environ.get("JOB_REPORT_TS")
            or os.environ.get("WAVE6A_REPORT_TS")
            or datetime.now().strftime("%Y%m%d_%H%M%S"))


def _parse_top_n(custom_prompt: str | None) -> int:
    if not custom_prompt:
        return _DEFAULT_TOP_N
    m = re.search(r"^__sonar_top_n__=(\d+)$", custom_prompt, re.MULTILINE)
    if m:
        try:
            return max(1, int(m.group(1)))
        except ValueError:
            pass
    return _DEFAULT_TOP_N


def _resolve_issues(file_path: str, content: str,
                    custom_prompt: str | None) -> list[dict]:
    # Strip _APPEND_PREFIX if present
    working = custom_prompt or ""
    from agents._bedrock import _APPEND_PREFIX
    if working.startswith(_APPEND_PREFIX):
        working = working[len(_APPEND_PREFIX):]

    # 1. Prefix wins
    if "__sonar_issues__\n" in working:
        body = working.split("__sonar_issues__\n", 1)[1]
        body = re.split(r"^__\w+__", body, flags=re.MULTILINE)[0].strip()
        try:
            doc = json.loads(body)
            return _normalise(doc)
        except ValueError:
            return []

    # 2. Source-is-JSON
    ext = os.path.splitext(file_path)[1].lower()
    head = (content or "")[:512]
    if ext == ".json" and ('"issues"' in head or "issues" in head):
        try:
            doc = json.loads(content)
            return _normalise(doc)
        except ValueError:
            pass

    # 3. API fetch (last resort)
    sonar_url = os.environ.get("SONAR_URL")
    token = os.environ.get("SONAR_TOKEN")
    project_key = os.environ.get("SONAR_PROJECT_KEY")
    if sonar_url and token and project_key:
        try:
            return fetch_issues(sonar_url, project_key, token)
        except SonarFetchError:
            return []

    return []


def _normalise(doc: dict) -> list[dict]:
    issues = doc.get("issues") if isinstance(doc, dict) else None
    if not isinstance(issues, list):
        return []
    out: list[dict] = []
    for raw in issues:
        if not isinstance(raw, dict):
            continue
        out.append({
            "rule": raw.get("rule"),
            "severity": raw.get("severity"),
            "component": raw.get("component"),
            "line": raw.get("line"),
            "message": raw.get("message"),
            "effort": raw.get("effort"),
            "textRange": raw.get("textRange"),
        })
    return out


def _sort_and_cap(issues: list[dict], top_n: int) -> list[dict]:
    sorted_ = sorted(issues, key=lambda i: _SEVERITY_RANK.get(i.get("severity") or "", 99))
    return sorted_[:top_n]


_SYSTEM_PROMPT = """You are a senior code quality engineer addressing SonarQube issues.

Given the source file and its open issues, emit a UNIFIED DIFF that addresses
as many issues as possible. For each issue you do NOT address, include it in
an explicit "deferred" rationale after the diff.

Rules:
1. Return a single fenced ```diff block — full unified-diff headers
   --- a/<file> / +++ b/<file>, 3 lines of context.
2. Address only issues you can resolve conservatively. Never break existing
   behaviour to fix a smell.
3. Preserve imports, signatures, and public API unless an issue specifically
   requires changing them.
"""


def _extract_diff(raw: str) -> str:
    m = re.search(r"```diff\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip() + "\n"
    m = re.search(r"```\w*\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip() + "\n"
    return raw.strip() + "\n"


def run_sonar_fix_agent(conn: duckdb.DuckDBPyConnection, job_id: str,
                        file_path: str, content: str, file_hash: str,
                        language: str | None, custom_prompt: str | None,
                        **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    issues = _resolve_issues(file_path, content, custom_prompt)
    if not issues:
        return {
            "markdown": "## SonarQube Fix Automation — error\n\n"
                        "No Sonar issues resolvable. Provide issues via "
                        "`__sonar_issues__\\n<JSON>` prefix, a JSON source "
                        "file, or set `SONAR_URL` + `SONAR_TOKEN` + "
                        "`SONAR_PROJECT_KEY` env vars.",
            "summary": "F11 error: no issues",
            "output_path": None,
        }

    top_n = _parse_top_n(custom_prompt)
    capped = _sort_and_cap(issues, top_n)
    by_file: dict[str, list[dict]] = defaultdict(list)
    for iss in capped:
        by_file[iss.get("component") or "_unknown_"].append(iss)

    ts = _report_ts()
    reports_root = os.path.join("Reports", ts)
    fixed: list[str] = []
    deferred: list[dict] = []
    first_output: str | None = None

    for component, file_issues in by_file.items():
        rel_path = component.split(":", 1)[-1] if ":" in component else component
        if not os.path.isfile(rel_path):
            for iss in file_issues:
                deferred.append({"id": iss.get("rule"),
                                 "reason": f"source file not found: {rel_path}"})
            continue
        with open(rel_path, "r", encoding="utf-8") as fh:
            source = fh.read()

        issue_block = "\n".join(
            f"- {i.get('rule')} [{i.get('severity')}] line {i.get('line')}: {i.get('message')}"
            for i in file_issues
        )
        user_prompt = (
            f"SOURCE FILE (`{rel_path}`):\n```\n{source}\n```\n\n"
            f"OPEN ISSUES:\n{issue_block}\n\n"
            f"Return the unified diff now."
        )

        try:
            model = make_bedrock_model()
            agent = Agent(model=model,
                          system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))
            raw = str(agent(user_prompt))
        except Exception as exc:  # pragma: no cover
            for iss in file_issues:
                deferred.append({"id": iss.get("rule"),
                                 "reason": f"LLM failed: {exc.__class__.__name__}"})
            continue

        diff_text = _extract_diff(raw)
        if not diff_text.strip() or "@@" not in diff_text:
            for iss in file_issues:
                deferred.append({"id": iss.get("rule"),
                                 "reason": "LLM returned no diff"})
            continue

        emit_result = emit_patch(
            agent_key="sonar_fix",
            reports_root=reports_root,
            file_path=rel_path,
            base_content=source,
            diff=diff_text,
            description=(f"Addresses {len(file_issues)} Sonar issue(s) "
                         f"({', '.join(i.get('rule') or '?' for i in file_issues[:5])}"
                         f"{'...' if len(file_issues) > 5 else ''})"),
            summary_extras={"issues_fixed": [i.get("rule") for i in file_issues]},
        )
        if first_output is None:
            first_output = emit_result["paths"]["content"]
        if emit_result["applied"]:
            fixed.extend(i.get("rule") for i in file_issues)
        else:
            for iss in file_issues:
                deferred.append({"id": iss.get("rule"),
                                 "reason": "diff rejected by reverse-apply"})

    md_parts = [
        "## SonarQube Fix Automation",
        f"- **Total issues resolved from intake:** {len(issues)}",
        f"- **Top-N cap used:** {top_n}",
        f"- **Issues fed to LLM:** {len(capped)}",
        f"- **Files patched:** {len(by_file)}",
        f"- **Issues fixed:** {len(fixed)}",
        f"- **Issues deferred:** {len(deferred)}",
    ]
    if fixed:
        md_parts.append(f"\n### Fixed\n" + "\n".join(f"- {r}" for r in fixed[:20]))
    if deferred:
        md_parts.append(f"\n### Deferred\n" + "\n".join(
            f"- {d['id']}: {d['reason']}" for d in deferred[:20]))

    summary = f"F11: {len(fixed)}/{len(capped)} issues fixed across {len(by_file)} file(s)."

    result = {
        "markdown": "\n".join(md_parts),
        "summary": summary,
        "output_path": first_output,
        "issues_total": len(issues),
        "issues_fixed": fixed,
        "issues_deferred": deferred,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
