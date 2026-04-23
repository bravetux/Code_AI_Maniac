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

"""F10 - Traceability Matrix + Coverage Gap Finder.

Pipeline:
  1. Resolve stories + tests_dir + src_dir from custom_prompt prefixes
     (handling the _APPEND_PREFIX wrap added by the feature_selector UI).
  2. Extract ACs with a deterministic numbered/bullet scanner; LLM fallback.
  3. Scan tests folder via tools.test_scanner (no LLM).
  4. Auto-include same-run Reports/<ts>/api_tests/ and perf_tests/.
  5. Match AC <-> test with Jaccard; batched LLM pass over ambiguous rows.
  6. Optionally call agents.test_coverage.run_test_coverage as a subagent.
  7. Emit matrix.csv, matrix.md, gaps.md.
"""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime
from typing import Any

import duckdb
from strands import Agent

from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response, _APPEND_PREFIX
from tools.cache import check_cache, write_cache
from tools.spec_fetcher import fetch_spec, SpecFetchError
from tools.test_scanner import scan_tests
from db.queries.history import add_history


def _report_ts() -> str:
    """Return the current job's report timestamp.
    Prefers JOB_REPORT_TS (generalised); falls back to WAVE6A_REPORT_TS
    (deprecated alias) and then datetime.now()."""
    return (os.environ.get("JOB_REPORT_TS")
            or os.environ.get("WAVE6A_REPORT_TS")
            or datetime.now().strftime("%Y%m%d_%H%M%S"))

_CACHE_KEY = "traceability_matrix"

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "to", "of", "in", "on", "for",
    "with", "by", "as", "is", "are", "be", "been", "being", "at", "that",
    "this", "it", "its", "from", "i", "you", "we", "they", "he", "she",
    "so", "do", "does", "should", "will", "can", "must", "may", "shall",
    "test", "tests", "testing", "case", "cases",
}

_AC_NUMBERED_RE = re.compile(
    r"^\s*(?:AC[-\s]?\d+|[0-9]+(?:\.|\)))\s*[:.\)]?\s*(.+)$",
    re.MULTILINE,
)
_AC_BULLET_RE = re.compile(r"^\s*[-*]\s+(.+)$", re.MULTILINE)


def _strip_append_prefix(custom_prompt: str | None) -> str:
    """Remove the _APPEND_PREFIX marker if present at the start."""
    if not custom_prompt:
        return ""
    if custom_prompt.startswith(_APPEND_PREFIX):
        return custom_prompt[len(_APPEND_PREFIX):]
    return custom_prompt


def _normalise_tokens(text: str) -> set[str]:
    toks = re.findall(r"[A-Za-z][A-Za-z0-9]+", text.lower())
    return {t for t in toks if t not in _STOP_WORDS and len(t) > 2}


def _score_pair(ac_text: str, test_blob: str) -> float:
    a = _normalise_tokens(ac_text)
    b = _normalise_tokens(test_blob.replace("_", " "))
    if not a or not b:
        return 0.0
    inter = a & b
    union = a | b
    return len(inter) / len(union)


def _extract_acs_deterministic(story: str) -> list[dict]:
    """Return ``[{id, text}]`` or empty list when nothing matched."""
    hits: list[str] = []
    for m in _AC_NUMBERED_RE.finditer(story):
        text = m.group(1).strip()
        if text:
            hits.append(text)
    if not hits:
        for m in _AC_BULLET_RE.finditer(story):
            text = m.group(1).strip()
            if text and len(text) > 10:
                hits.append(text)
    return [{"id": f"AC-{i+1}", "text": t} for i, t in enumerate(hits)]


_AC_EXTRACT_PROMPT = """You are a QA analyst extracting acceptance criteria from a user story.

Return STRICT JSON only (no commentary) matching:
{
  "acs": [
    {"id": "AC-1", "text": "..."},
    {"id": "AC-2", "text": "..."}
  ]
}

Rules:
- One AC per observable outcome (link visible, email sent, etc.).
- IDs are sequential AC-1, AC-2, ...
- Preserve the original phrasing; do not invent new criteria.
- Emit 1-15 ACs. If the story has fewer implied criteria, emit just those.
"""


def _extract_acs_llm(story: str, custom_prompt: str | None) -> list[dict]:
    try:
        model = make_bedrock_model()
        agent = Agent(model=model,
                      system_prompt=resolve_prompt(custom_prompt, _AC_EXTRACT_PROMPT))
        raw = str(agent(f"Extract acceptance criteria from this story:\n\n{story}"))
    except Exception:
        return []
    try:
        payload = parse_json_response(raw)
    except Exception:
        return []
    acs = payload.get("acs") or []
    return [{"id": a.get("id") or f"AC-{i+1}", "text": a.get("text", "")}
            for i, a in enumerate(acs) if a.get("text")]


def _is_ambiguous(scores: list[float], top: float) -> bool:
    """An AC is ambiguous if:
      - no test scores >= 0.5, OR
      - top score is between 0.5 and 0.7 (inclusive-exclusive), OR
      - two or more scores are >= 0.7 and within 0.1 of each other.
    """
    high = [s for s in scores if s >= 0.7]
    if not scores:
        return True
    if top < 0.5:
        return True
    if 0.5 <= top < 0.7:
        return True
    if len(high) >= 2:
        second = sorted(scores, reverse=True)[1]
        if top - second < 0.1:
            return True
    return False


def _jaccard_match(acs: list[dict], tests: list[dict]) -> tuple[dict, dict]:
    """Return (locks, ambiguous).

    locks:     {ac_id: [test_record, ...]}
    ambiguous: {ac_id: [(test_record, score), ...]}  top-5
    """
    locks: dict[str, list[dict]] = {}
    ambiguous: dict[str, list[tuple[dict, float]]] = {}
    for ac in acs:
        scored: list[tuple[dict, float]] = []
        for t in tests:
            blob = f"{t.get('test_name', '')} {t.get('snippet', '')}"
            s = _score_pair(ac["text"], blob)
            scored.append((t, s))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[0][1] if scored else 0.0
        just_scores = [s for _, s in scored]
        if _is_ambiguous(just_scores, top):
            ambiguous[ac["id"]] = scored[:5]
        else:
            locks[ac["id"]] = [scored[0][0]]
    return locks, ambiguous


_BATCH_MATCH_PROMPT = """You are a QA traceability analyst.

For each ambiguous acceptance criterion below, pick the tests (0 or more)
that genuinely verify it. Be conservative - do not guess.

Return STRICT JSON only:
{
  "matches": {
    "AC-1": ["test_name_a", "test_name_b"],
    "AC-2": []
  }
}

Rules:
- test ids are the exact test_name strings shown below.
- Emit an entry for every ambiguous AC even if the list is empty.
- Do not invent test names.
"""


def _llm_match_ambiguous(ambiguous: dict, custom_prompt: str | None) -> dict[str, list[str]]:
    if not ambiguous:
        return {}
    payload_lines = []
    for ac_id, cands in ambiguous.items():
        payload_lines.append(f"\n### {ac_id}")
        for idx, (t, score) in enumerate(cands, start=1):
            payload_lines.append(f"{idx}. {t['test_name']} "
                                 f"(kind={t.get('kind')}, score={score:.2f})")
    try:
        model = make_bedrock_model()
        agent = Agent(model=model,
                      system_prompt=resolve_prompt(custom_prompt, _BATCH_MATCH_PROMPT))
        raw = str(agent("\n".join(payload_lines)))
    except Exception:
        return {}
    try:
        payload = parse_json_response(raw)
    except Exception:
        return {}
    matches = payload.get("matches") or {}
    return {k: list(v) for k, v in matches.items() if isinstance(v, list)}


def _build_matrix_rows(acs: list[dict], mapping: dict[str, list[dict]],
                       coverage: dict[str, float] | None) -> list[dict]:
    rows: list[dict] = []
    for ac in acs:
        tests = mapping.get(ac["id"]) or []
        test_names = ", ".join(t["test_name"] for t in tests) or ""
        kinds = ", ".join(sorted({t["kind"] for t in tests})) or ""
        cov_str = "n/a"
        status = "red" if not tests else "green"
        if coverage is not None and tests:
            covs = [coverage.get(t["test_name"], 0.0) for t in tests]
            avg = sum(covs) / len(covs) if covs else 0.0
            cov_str = f"{avg:.0f}"
            if avg < 70.0:
                status = "amber"
        rows.append({
            "AC_ID":       ac["id"],
            "AC_Text":     ac["text"],
            "Tests":       test_names,
            "Kinds":       kinds,
            "Coverage_%":  cov_str,
            "Status":      status,
        })
    return rows


def _write_artifacts(out_dir: str, acs: list[dict],
                     mapping: dict[str, list[dict]],
                     orphans: list[dict],
                     coverage: dict[str, float] | None) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    rows = _build_matrix_rows(acs, mapping, coverage)

    csv_path = os.path.join(out_dir, "matrix.csv")
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["AC_ID", "AC_Text", "Tests",
                                                "Kinds", "Coverage_%", "Status"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    md_lines = [
        "| AC | Text | Tests | Kinds | Coverage % | Status |",
        "|----|------|-------|-------|------------|--------|",
    ]
    for r in rows:
        md_lines.append(
            f"| {r['AC_ID']} | {r['AC_Text']} | {r['Tests'] or '-'} | "
            f"{r['Kinds'] or '-'} | {r['Coverage_%']} | {r['Status']} |"
        )
    md_path = os.path.join(out_dir, "matrix.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(md_lines) + "\n")

    gaps_lines = ["## Traceability Gaps\n"]
    red = [r for r in rows if r["Status"] == "red"]
    amber = [r for r in rows if r["Status"] == "amber"]
    if red:
        gaps_lines.append("### Red - ACs with no tests")
        for r in red:
            gaps_lines.append(f"- **{r['AC_ID']}** - {r['AC_Text']}")
    if amber:
        gaps_lines.append("\n### Amber - ACs covered under 70%")
        for r in amber:
            gaps_lines.append(f"- **{r['AC_ID']}** - {r['AC_Text']} (coverage {r['Coverage_%']}%)")
    if orphans:
        gaps_lines.append("\n### Orphan tests - match no AC")
        for o in orphans:
            gaps_lines.append(f"- `{o['test_name']}` ({o['kind']}) - `{o['file']}`")
    gaps_path = os.path.join(out_dir, "gaps.md")
    with open(gaps_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(gaps_lines) + "\n")

    return {"csv": csv_path, "md": md_path, "gaps": gaps_path, "rows": rows}


def _resolve_inputs(file_path: str, content: str, custom_prompt: str | None) -> dict:
    # Strip _APPEND_PREFIX so our marker scans hit the real body.
    working_prompt = _strip_append_prefix(custom_prompt)

    stories = ""
    tests_dir: str | None = None
    src_dir: str | None = None

    if working_prompt:
        if "__stories__\n" in working_prompt:
            body = working_prompt.split("__stories__\n", 1)[1]
            # stop at the next __xxx__ marker
            body = re.split(r"^__\w+__", body, flags=re.MULTILINE)[0].strip()
            stories = body
        m = re.search(r"^__tests_dir__=(.+)$", working_prompt, re.MULTILINE)
        if m:
            tests_dir = m.group(1).strip()
        m = re.search(r"^__src_dir__=(.+)$", working_prompt, re.MULTILINE)
        if m:
            src_dir = m.group(1).strip()

    if "::" in file_path and not stories:
        parts = file_path.split("::")
        if len(parts) >= 1 and os.path.isfile(parts[0]):
            with open(parts[0], "r", encoding="utf-8") as fh:
                stories = fh.read()
        if tests_dir is None and len(parts) >= 2:
            tests_dir = parts[1]
        if src_dir is None and len(parts) >= 3:
            src_dir = parts[2]

    if not stories and content:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".txt", ".md", "") or "::" not in file_path:
            stories = content

    if stories:
        first_line = stories.strip().splitlines()[0] if stories.strip() else ""
        if re.match(r"^https?://", first_line):
            try:
                spec = fetch_spec(first_line)
                stories = spec.get("body") or spec.get("description") or stories
            except SpecFetchError:
                pass

    return {"stories": stories, "tests_dir": tests_dir, "src_dir": src_dir}


def _auto_scan_same_run(reports_root: str = "Reports") -> list[dict]:
    """Pick up F5/F6 outputs from the most recent Reports/<ts>/ in cwd.

    Honours the WAVE6A_REPORT_TS env var when set (test hook).
    """
    ts = os.environ.get("JOB_REPORT_TS") or os.environ.get("WAVE6A_REPORT_TS")
    if ts:
        base = os.path.join(reports_root, ts)
        if not os.path.isdir(base):
            return []
    else:
        if not os.path.isdir(reports_root):
            return []
        subs = sorted([d for d in os.listdir(reports_root)
                       if os.path.isdir(os.path.join(reports_root, d))])
        if not subs:
            return []
        base = os.path.join(reports_root, subs[-1])

    collected: list[dict] = []
    for sub in ("api_tests", "perf_tests"):
        path = os.path.join(base, sub)
        if os.path.isdir(path):
            collected.extend(scan_tests(path))
    return collected


def _run_coverage_subagent(conn, job_id: str, src_dir: str,
                           custom_prompt: str | None) -> dict[str, float] | None:
    try:
        from agents.test_coverage import run_test_coverage
    except Exception:
        return None
    try:
        if not os.path.isdir(src_dir):
            return None
        blob_parts: list[str] = []
        for dirpath, _d, files in os.walk(src_dir):
            for n in files:
                if n.endswith(".py"):
                    p = os.path.join(dirpath, n)
                    try:
                        with open(p, "r", encoding="utf-8") as fh:
                            blob_parts.append(f"# === {p} ===\n{fh.read()}")
                    except OSError:
                        continue
        if not blob_parts:
            return None
        blob = "\n\n".join(blob_parts)
        res = run_test_coverage(
            conn=conn, job_id=job_id,
            file_path=src_dir, content=blob, file_hash="",
            language="python", custom_prompt=custom_prompt,
        )
        overall = res.get("coverage_percentage") or res.get("coverage_pct") or 0.0
        per_test = res.get("per_test_coverage") or {}
        if per_test:
            return {k: float(v) for k, v in per_test.items()}
        return {"__overall__": float(overall)}
    except Exception:
        return None


def run_traceability_matrix(conn: duckdb.DuckDBPyConnection, job_id: str,
                            file_path: str, content: str, file_hash: str,
                            language: str | None, custom_prompt: str | None,
                            **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    inputs = _resolve_inputs(file_path, content, custom_prompt)
    if not inputs["stories"]:
        return {"markdown": "## Traceability Matrix - error\n\nNo stories resolvable.",
                "summary": "F10 error: no stories",
                "output_path": None}

    acs = _extract_acs_deterministic(inputs["stories"])
    if not acs:
        acs = _extract_acs_llm(inputs["stories"], custom_prompt)
    if not acs:
        return {"markdown": "## Traceability Matrix - error\n\nCould not extract any acceptance criteria.",
                "summary": "F10 error: zero ACs",
                "output_path": None}

    tests: list[dict] = []
    if inputs["tests_dir"]:
        tests.extend(scan_tests(inputs["tests_dir"]))
    tests.extend(_auto_scan_same_run())

    seen = set()
    unique_tests: list[dict] = []
    for t in tests:
        key = (t["file"], t["test_name"])
        if key in seen:
            continue
        seen.add(key)
        unique_tests.append(t)
    tests = unique_tests

    locks, ambiguous = _jaccard_match(acs, tests)

    llm_matches = _llm_match_ambiguous(ambiguous, custom_prompt)

    mapping: dict[str, list[dict]] = {}
    for ac in acs:
        if ac["id"] in locks:
            mapping[ac["id"]] = locks[ac["id"]]
            continue
        test_names = llm_matches.get(ac["id"], [])
        matched = [t for t in tests if t["test_name"] in test_names]
        mapping[ac["id"]] = matched

    matched_keys = {(t["file"], t["test_name"])
                    for ts in mapping.values() for t in ts}
    orphans = [t for t in tests
               if (t["file"], t["test_name"]) not in matched_keys]

    coverage: dict[str, float] | None = None
    if inputs["src_dir"]:
        cov = _run_coverage_subagent(conn, job_id, inputs["src_dir"], custom_prompt)
        if cov:
            if "__overall__" in cov:
                overall = cov["__overall__"]
                coverage = {t["test_name"]: overall
                            for ts in mapping.values() for t in ts}
            else:
                coverage = cov

    ts_str = _report_ts()
    out_dir = os.path.join("Reports", ts_str, "traceability")
    artifacts = _write_artifacts(out_dir, acs, mapping, orphans, coverage)

    rows = artifacts["rows"]
    status_counts = {"green": 0, "amber": 0, "red": 0}
    for r in rows:
        status_counts[r["Status"]] = status_counts.get(r["Status"], 0) + 1
    md_parts = [
        "## Traceability Matrix",
        f"- **ACs:** {len(acs)}",
        f"- **Tests scanned:** {len(tests)}",
        f"- **Orphan tests:** {len(orphans)}",
        f"- **Status breakdown:** "
        f"{status_counts['green']} green, "
        f"{status_counts['amber']} amber, "
        f"{status_counts['red']} red",
        f"- **CSV:** `{artifacts['csv']}`",
        f"- **Markdown matrix:** `{artifacts['md']}`",
        f"- **Gaps report:** `{artifacts['gaps']}`\n",
        "### Preview",
        open(artifacts["md"], "r", encoding="utf-8").read(),
    ]
    markdown = "\n".join(md_parts)
    summary = (f"{len(acs)} ACs, {status_counts['red']} red, "
               f"{status_counts['amber']} amber, "
               f"{len(orphans)} orphan tests.")

    result = {
        "markdown": markdown,
        "summary": summary,
        "output_path": artifacts["csv"],
        "rows": rows,
        "orphans": orphans,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
