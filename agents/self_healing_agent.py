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
"""F9 — Self-Healing Test Agent.

Rewrites UI test scripts (Selenium/Playwright/Cypress) when selectors
break due to DOM changes. Framework detected from test content. DOM
supplied inline or via sibling dom.html.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt
from tools.cache import check_cache, write_cache
from tools.patch_emitter import emit as emit_patch
from db.queries.history import add_history

_CACHE_KEY = "self_healing_agent"


def _report_ts() -> str:
    return (os.environ.get("JOB_REPORT_TS")
            or os.environ.get("WAVE6A_REPORT_TS")
            or datetime.now().strftime("%Y%m%d_%H%M%S"))


_SELENIUM_MARKERS = ("from selenium", "webdriver", "By.ID", "By.XPATH",
                     "By.CSS_SELECTOR", "find_element(")
_PLAYWRIGHT_MARKERS = ("from playwright", "page.locator(", "page.get_by_",
                       "chromium.launch")
_CYPRESS_MARKERS = ("cy.get(", "cy.visit(", "cy.contains(", "describe(")


def _detect_framework(content: str, file_name: str | None = None) -> str | None:
    text = content or ""
    if file_name and (file_name.endswith(".cy.js") or file_name.endswith(".cy.ts")):
        return "cypress"
    if any(m in text for m in _CYPRESS_MARKERS) and "cy." in text:
        return "cypress"
    if any(m in text for m in _PLAYWRIGHT_MARKERS):
        return "playwright"
    if any(m in text for m in _SELENIUM_MARKERS):
        return "selenium"
    return None


_SELENIUM_BY_RE = re.compile(r'By\.\w+\s*,\s*[\'"]([^\'"]+)[\'"]')
_SELENIUM_CSS_IN_FIND = re.compile(
    r'find_element\([^,]*,\s*[\'"]([^\'"]+)[\'"]'
)
_PLAYWRIGHT_LOCATOR_RE = re.compile(
    r'(?:page|locator)\.(?:locator|get_by_test_id|get_by_role|get_by_text)'
    r'\(\s*[\'"]([^\'"]+)[\'"]'
)
_CYPRESS_GET_RE = re.compile(r'cy\.get\s*\(\s*[\'"]([^\'"]+)[\'"]')


def _extract_selectors(content: str, framework: str | None) -> list[str]:
    if not framework or not content:
        return []
    text = content
    found: list[str] = []
    if framework == "selenium":
        found.extend(_SELENIUM_BY_RE.findall(text))
        found.extend(_SELENIUM_CSS_IN_FIND.findall(text))
    elif framework == "playwright":
        found.extend(_PLAYWRIGHT_LOCATOR_RE.findall(text))
    elif framework == "cypress":
        found.extend(_CYPRESS_GET_RE.findall(text))
    seen: set[str] = set()
    ordered: list[str] = []
    for s in found:
        if s not in seen:
            seen.add(s)
            ordered.append(s)
    return ordered


def _resolve_dom(file_path: str, custom_prompt: str | None) -> str | None:
    """Resolve DOM snapshot via prefix or sibling dom.html.
    Strips the _APPEND_PREFIX wrap from the F10 UI helper convention."""
    # Strip _APPEND_PREFIX if present (matches Wave 6A convention)
    working = custom_prompt or ""
    from agents._bedrock import _APPEND_PREFIX
    if working.startswith(_APPEND_PREFIX):
        working = working[len(_APPEND_PREFIX):]
    if "__page_html__\n" in working:
        body = working.split("__page_html__\n", 1)[1]
        body = re.split(r"^__\w+__", body, flags=re.MULTILINE)[0]
        return body.rstrip()
    parent = os.path.dirname(os.path.abspath(file_path))
    sibling = os.path.join(parent, "dom.html")
    if os.path.isfile(sibling):
        with open(sibling, "r", encoding="utf-8") as fh:
            return fh.read()
    return None


_SYSTEM_PROMPT = """You are a UI test maintenance engineer specialising in {framework}.

The test script below uses selectors that no longer match the current DOM.
Your task: emit a UNIFIED DIFF that updates ONLY the selectors so the test
works against the current DOM. Do not rewrite assertions, flow, or imports.

Rules:
1. Return ONLY a single fenced ```diff block — no explanation before/after.
2. Use full unified-diff headers: --- a/<file> / +++ b/<file>.
3. Keep 3 lines of context around each change.
4. Prefer stable selectors when available in the new DOM — data-testid > aria-label > role > class > id.
5. If the DOM does not contain an equivalent element for an old selector, leave that line untouched (do not remove the test step).
"""


def _extract_diff_block(raw: str) -> str:
    m = re.search(r"```diff\s*\n(.*?)```", raw, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip() + "\n"
    m = re.search(r"```\w*\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip() + "\n"
    return raw.strip() + "\n"


def run_self_healing_agent(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, content: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    dom = _resolve_dom(file_path, custom_prompt)
    if dom is None:
        return {
            "markdown": "## Self-Healing Test Agent — error\n\nNo DOM snapshot supplied. "
                        "Provide `__page_html__\\n<html>` in the fine-tune prompt "
                        "or a sibling `dom.html` file next to the source.",
            "summary": "F9 error: no DOM",
            "output_path": None,
        }

    framework = _detect_framework(content, file_name=os.path.basename(file_path))
    selectors = _extract_selectors(content, framework)
    framework_label = framework or "generic"

    system = _SYSTEM_PROMPT.format(framework=framework_label)
    user_prompt = (
        f"OLD TEST FILE (`{os.path.basename(file_path)}`):\n"
        f"```\n{content}\n```\n\n"
        f"CURRENT DOM:\n```html\n{dom}\n```\n\n"
        f"OLD SELECTORS FOUND: {selectors or '(none detected)'}\n\n"
        f"Return the unified diff now."
    )

    try:
        model = make_bedrock_model()
        agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, system))
        raw = str(agent(user_prompt))
    except Exception as exc:  # pragma: no cover — network/LLM failure path
        return {
            "markdown": f"## Self-Healing Test Agent — LLM call failed\n\n{exc}",
            "summary": f"F9 error: LLM call failed ({exc.__class__.__name__})",
            "output_path": None,
        }

    diff_text = _extract_diff_block(raw)
    if not diff_text.strip() or "@@" not in diff_text:
        return {
            "markdown": "## Self-Healing Test Agent — LLM returned no diff",
            "summary": "F9 error: LLM returned empty or invalid diff",
            "output_path": None,
        }

    ts = _report_ts()
    reports_root = os.path.join("Reports", ts)
    emit_result = emit_patch(
        agent_key="self_healing",
        reports_root=reports_root,
        file_path=os.path.basename(file_path),
        base_content=content,
        diff=diff_text,
        description=f"Selector rewrite for {framework_label} ({len(selectors)} old selectors)",
        summary_extras={"framework": framework_label,
                        "old_selectors": selectors,
                        "confidence": "high" if framework else "low"},
    )

    md_parts = [
        f"## Self-Healing Test Agent — `{os.path.basename(file_path)}`",
        f"- **Framework:** {framework_label}",
        f"- **Old selectors detected:** {len(selectors)}",
        f"- **Diff applied cleanly:** {emit_result['applied']}",
        f"- **Patched file:** `{emit_result['paths']['content']}`",
        f"- **Diff:** `{emit_result['paths']['diff']}`",
        f"- **PR comment:** `{emit_result['paths']['pr_comment']}`",
    ]
    markdown = "\n".join(md_parts)
    summary = f"F9 {framework_label} selector rewrite — {'applied' if emit_result['applied'] else 'diff rejected'}."

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": emit_result["paths"]["content"],
        "framework": framework_label,
        "applied": emit_result["applied"],
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
