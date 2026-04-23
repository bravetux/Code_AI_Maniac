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

"""F2 — Test Case Generator from User Stories.

Intake: pasted story text or Jira / Azure-DevOps / Qase URL (via the
tools.spec_fetcher pipeline helper). Output: structured test cases covering
positive, negative, functional, and NFR (performance / security / usability /
reliability) dimensions. Saved to Reports/ as markdown + JSON.
"""

import json
import os
from datetime import datetime
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.cache import check_cache, write_cache
from tools.spec_fetcher import fetch_spec, SpecFetchError
from db.queries.history import add_history

_CACHE_KEY = "story_test_generator"


_SYSTEM_PROMPT = """You are a senior QA lead generating rigorous test cases from user stories or requirements.

Produce a balanced, auditable set of test cases that covers:

1. **Positive / happy-path** — each acceptance criterion explicitly verified.
2. **Negative** — invalid input, missing fields, malformed payloads, wrong types, forbidden transitions.
3. **Functional edge cases** — boundary values, empty collections, Unicode, timezone, concurrency where relevant.
4. **Non-functional (NFR)** — at least one case each for performance, security, usability, and reliability when applicable.

Return **STRICT JSON only** matching this schema (no commentary, no code fences):

{
  "story_title": "...",
  "assumptions": ["..."],
  "test_cases": [
    {
      "id": "TC-001",
      "category": "positive|negative|functional|nfr_performance|nfr_security|nfr_usability|nfr_reliability",
      "title": "...",
      "preconditions": ["..."],
      "steps": ["..."],
      "expected_result": "...",
      "priority": "high|medium|low",
      "traces_to": "AC reference or paragraph snippet"
    }
  ]
}

Aim for 8-20 test cases depending on story size. Prefer concrete, executable steps (exact inputs, exact expected outputs) over vague descriptions.
"""


def _render_markdown(spec: dict, payload: dict) -> str:
    cases = payload.get("test_cases", []) or []
    lines = [
        f"## Test Case Generator — {spec.get('title', 'story')}",
        f"- **Provider:** {spec.get('provider', 'inline')}",
        f"- **Source:** `{spec.get('source', 'inline')}`",
        f"- **Generated cases:** {len(cases)}\n",
    ]

    assumptions = payload.get("assumptions") or []
    if assumptions:
        lines.append("### Assumptions")
        lines.extend(f"- {a}" for a in assumptions)
        lines.append("")

    lines.append("### Test Cases")
    lines.append("| ID | Category | Priority | Title | Expected |")
    lines.append("|---|---|---|---|---|")
    for c in cases:
        lines.append(
            f"| {c.get('id', '')} | {c.get('category', '')} | {c.get('priority', '')} "
            f"| {(c.get('title') or '').replace('|', '\\|')} "
            f"| {(c.get('expected_result') or '').replace('|', '\\|')[:120]} |"
        )
    lines.append("")

    for c in cases:
        lines.append(f"#### {c.get('id', '')} — {c.get('title', '')}")
        if c.get("preconditions"):
            lines.append("**Preconditions:**")
            lines.extend(f"- {p}" for p in c["preconditions"])
        if c.get("steps"):
            lines.append("**Steps:**")
            lines.extend(f"{i + 1}. {s}" for i, s in enumerate(c["steps"]))
        lines.append(f"**Expected:** {c.get('expected_result', '')}")
        if c.get("traces_to"):
            lines.append(f"**Traces to:** {c['traces_to']}")
        lines.append("")
    return "\n".join(lines)


def run_story_test_generator(conn: duckdb.DuckDBPyConnection, job_id: str,
                             file_path: str, content: str, file_hash: str,
                             language: str | None, custom_prompt: str | None,
                             **kwargs) -> dict:
    """``content`` is either a pasted story blob or a Jira/ADO/Qase URL.

    ``file_path`` is used purely as a label for history and report naming.
    """
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    try:
        spec = fetch_spec(content)
    except SpecFetchError as e:
        raise RuntimeError(f"Spec fetch failed: {e}")

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    prompt = (
        f"Generate test cases for the following user story / requirement.\n\n"
        f"Title: {spec['title']}\n"
        f"Source: {spec['source']} (provider={spec['provider']})\n\n"
        f"---\n{spec['body']}\n---"
    )
    raw = str(agent(prompt))

    try:
        payload = parse_json_response(raw)
    except Exception:
        payload = {"story_title": spec["title"], "assumptions": [],
                   "test_cases": [], "_raw": raw}

    payload.setdefault("story_title", spec["title"])

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "story_tests")
    os.makedirs(out_dir, exist_ok=True)
    label = (os.path.basename(file_path) or "story").replace("/", "_")[:80] or "story"
    json_path = os.path.join(out_dir, f"{label}.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    markdown = _render_markdown(spec, payload)
    case_count = len(payload.get("test_cases") or [])
    summary = f"Generated {case_count} test case(s) from {spec['provider']} story."

    result = {
        "markdown": markdown,
        "summary": summary,
        "test_cases": payload.get("test_cases", []),
        "spec": spec,
        "output_path": json_path,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
