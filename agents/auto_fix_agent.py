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

"""F15 — Auto-Fix / Patch Generator.

Consumes Bug Analysis + Refactoring Advisor findings (auto-scanned from
same-run Reports/<ts>/<agent>/*.md OR via __findings__ prefix) and emits
a PR-ready unified diff against the target source file.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt, _APPEND_PREFIX
from tools.cache import check_cache, write_cache
from tools.patch_emitter import emit as emit_patch
from db.queries.history import add_history

_CACHE_KEY = "auto_fix_agent"


def _report_ts() -> str:
    return (os.environ.get("JOB_REPORT_TS")
            or os.environ.get("WAVE6A_REPORT_TS")
            or datetime.now().strftime("%Y%m%d_%H%M%S"))


def _resolve_findings(file_path: str, custom_prompt: str | None,
                      reports_root: str | None) -> list[dict]:
    # Strip _APPEND_PREFIX wrap if present
    working = custom_prompt or ""
    if working.startswith(_APPEND_PREFIX):
        working = working[len(_APPEND_PREFIX):]

    # 1. Prefix wins
    if "__findings__\n" in working:
        body = working.split("__findings__\n", 1)[1]
        body = re.split(r"^__\w+__", body, flags=re.MULTILINE)[0].strip()
        try:
            doc = json.loads(body)
            return _normalise_findings(doc)
        except ValueError:
            return [{"id": f"INLINE-{i+1}", "description": line.strip()}
                    for i, line in enumerate(body.splitlines()) if line.strip()]

    # 2. Auto-scan Reports/<ts>/bug_analysis/ and refactoring_advisor/
    if reports_root and os.path.isdir(reports_root):
        source_basename = os.path.splitext(os.path.basename(file_path))[0]
        collected: list[dict] = []
        for sub in ("bug_analysis", "refactoring_advisor"):
            sub_dir = os.path.join(reports_root, sub)
            if not os.path.isdir(sub_dir):
                continue
            for name in os.listdir(sub_dir):
                stem = os.path.splitext(name)[0]
                if source_basename in stem or stem in source_basename:
                    full = os.path.join(sub_dir, name)
                    try:
                        text = open(full, "r", encoding="utf-8", errors="replace").read()
                        doc = json.loads(text)
                        collected.extend(_normalise_findings(doc))
                    except (OSError, ValueError):
                        continue
        if collected:
            return collected
    return []


def _normalise_findings(doc: dict) -> list[dict]:
    if isinstance(doc, list):
        items = doc
    elif isinstance(doc, dict):
        items = doc.get("findings") or doc.get("bugs") or doc.get("issues") or []
    else:
        items = []
    out: list[dict] = []
    for idx, f in enumerate(items):
        if not isinstance(f, dict):
            continue
        out.append({
            "id": f.get("id") or f"F-{idx+1}",
            "line": f.get("line"),
            "severity": f.get("severity"),
            "description": f.get("description") or f.get("message") or "",
            "suggestion": f.get("suggestion") or "",
        })
    return out


_SYSTEM_PROMPT = """You are a senior software engineer producing a PR-ready patch.

Given the source file and the findings below, emit a UNIFIED DIFF that
addresses each finding conservatively. Never break existing behaviour.

Rules:
1. Return ONE fenced ```diff block with full headers --- a/<file> / +++ b/<file>,
   3 lines of context per hunk.
2. If a finding requires a judgement call you can't make safely (e.g. removing
   a public API), leave it for the human — don't change that code.
3. Keep imports minimal. Add new imports only when necessary for your fix.
"""


def _extract_diff(raw: str) -> str:
    m = re.search(r"```diff\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if m:
        body = m.group(1).strip() + "\n"
    else:
        m = re.search(r"```\w*\s*\n(.*?)```", raw, re.DOTALL)
        if m:
            body = m.group(1).strip() + "\n"
        else:
            body = raw.strip() + "\n"
    return _normalise_blank_context(body)


def _normalise_blank_context(diff: str) -> str:
    """Convert bare empty lines inside a hunk to space-prefixed blank context.

    LLMs (and some editors) frequently strip the single-space prefix from
    blank context lines, producing diffs that strict parsers reject. Inside
    a hunk, a line that is completely empty should be treated as a blank
    context line (" \\n"). Headers (@@, ---, +++) and non-hunk whitespace
    are preserved verbatim.
    """
    raw_lines = diff.split("\n")
    # Preserve the trailing empty element from a final newline.
    trailing = ""
    if raw_lines and raw_lines[-1] == "":
        raw_lines = raw_lines[:-1]
        trailing = "\n"
    out: list[str] = []
    in_hunk = False
    for line in raw_lines:
        if line.startswith("@@"):
            in_hunk = True
            out.append(line)
            continue
        if line.startswith("---") or line.startswith("+++"):
            in_hunk = False
            out.append(line)
            continue
        if in_hunk and line == "":
            out.append(" ")
        else:
            out.append(line)
    return "\n".join(out) + trailing


def run_auto_fix_agent(conn: duckdb.DuckDBPyConnection, job_id: str,
                       file_path: str, content: str, file_hash: str,
                       language: str | None, custom_prompt: str | None,
                       **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    ts = _report_ts()
    reports_root = os.path.join("Reports", ts)

    findings = _resolve_findings(file_path, custom_prompt, reports_root)
    if not findings:
        return {
            "markdown": "## Auto-Fix Patch Generator — error\n\n"
                        "No findings resolvable. Provide findings via "
                        "`__findings__\\n<JSON or markdown>` prefix, or run "
                        "Bug Analysis / Refactoring Advisor in the same job "
                        "so their output can be auto-scanned.",
            "summary": "F15 error: no findings",
            "output_path": None,
        }

    finding_block = "\n".join(
        f"- {f['id']} [{f.get('severity') or 'unspecified'}] "
        f"line {f.get('line') or '?'}: {f['description']}"
        + (f"\n  Suggestion: {f['suggestion']}" if f['suggestion'] else "")
        for f in findings
    )
    user_prompt = (
        f"SOURCE FILE (`{os.path.basename(file_path)}`):\n"
        f"```\n{content}\n```\n\n"
        f"FINDINGS:\n{finding_block}\n\n"
        f"Emit the unified diff now."
    )

    try:
        model = make_bedrock_model()
        agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))
        raw = str(agent(user_prompt))
    except Exception as exc:  # pragma: no cover
        return {
            "markdown": f"## Auto-Fix Patch Generator — LLM call failed\n\n{exc}",
            "summary": f"F15 error: LLM call failed ({exc.__class__.__name__})",
            "output_path": None,
        }

    diff_text = _extract_diff(raw)
    if not diff_text.strip() or "@@" not in diff_text:
        return {
            "markdown": "## Auto-Fix Patch Generator — LLM returned no diff",
            "summary": "F15 error: LLM returned empty or invalid diff",
            "output_path": None,
        }

    emit_result = emit_patch(
        agent_key="auto_fix",
        reports_root=reports_root,
        file_path=os.path.basename(file_path),
        base_content=content,
        diff=diff_text,
        description=f"Addresses {len(findings)} finding(s): "
                    + ", ".join(f["id"] for f in findings[:5]),
        summary_extras={
            "findings_addressed": [f["id"] for f in findings],
        },
    )

    md_parts = [
        f"## Auto-Fix Patch Generator — `{os.path.basename(file_path)}`",
        f"- **Findings input:** {len(findings)}",
        f"- **Diff applied cleanly:** {emit_result['applied']}",
        f"- **Patched file:** `{emit_result['paths']['content']}`",
        f"- **Diff:** `{emit_result['paths']['diff']}`",
    ]
    if not emit_result["applied"]:
        md_parts.append("\n> **Warning:** the LLM-emitted diff did not apply "
                        "cleanly against the source. Raw diff saved for manual "
                        "review; patched content reflects the original source.")
    markdown = "\n".join(md_parts)
    summary = (f"F15 patched {os.path.basename(file_path)} for {len(findings)} finding(s)"
               + ("" if emit_result['applied'] else " — diff rejected"))

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": emit_result["paths"]["content"],
        "applied": emit_result["applied"],
        "findings_addressed": [f["id"] for f in findings],
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
