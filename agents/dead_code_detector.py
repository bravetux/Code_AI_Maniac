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

"""F17 — Dead-Code / Unused-Symbol Detector.

Two-stage pipeline:

1. **Fast heuristic pass** — regex-based symbol extraction (defs vs usages)
   inside the file we're analysing. Catches the obvious local cases without
   paying for an LLM call.
2. **LLM semantic pass** — classifies the findings, suppresses false positives
   (public API, framework entry points, dunder / ``__all__`` exports, event
   handlers wired up by string name, etc.), and adds a confidence score.
"""

import os
import re
from datetime import datetime
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_CACHE_KEY = "dead_code_detector"


# Regex patterns per language family — best-effort, not a full parser.
_DEF_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "python":     [("function", r"^\s*def\s+(\w+)\s*\("),
                   ("class",    r"^\s*class\s+(\w+)\b"),
                   ("var",      r"^([A-Z_][A-Z0-9_]{2,})\s*=")],
    "javascript": [("function", r"^\s*function\s+(\w+)\s*\("),
                   ("const",    r"^\s*(?:const|let|var)\s+(\w+)\s*="),
                   ("class",    r"^\s*class\s+(\w+)\b")],
    "typescript": [("function", r"^\s*function\s+(\w+)\s*\("),
                   ("const",    r"^\s*(?:const|let|var)\s+(\w+)\s*[:=]"),
                   ("class",    r"^\s*class\s+(\w+)\b"),
                   ("type",     r"^\s*(?:type|interface)\s+(\w+)\b")],
    "java":       [("method",   r"^\s*(?:public|private|protected|static|\s)+\s+\w+\s+(\w+)\s*\("),
                   ("class",    r"^\s*(?:public\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)\b")],
    "csharp":     [("method",   r"^\s*(?:public|private|protected|internal|static|\s)+\s+\w+\s+(\w+)\s*\("),
                   ("class",    r"^\s*(?:public\s+)?(?:abstract\s+)?(?:sealed\s+)?class\s+(\w+)\b")],
    "go":         [("func",     r"^\s*func\s+(?:\([^)]*\)\s+)?(\w+)\s*\(")],
    "c":          [("function", r"^[\w\s\*]+\s+(\w+)\s*\([^;]*\)\s*\{")],
    "cpp":        [("function", r"^[\w\s\*:<>]+\s+(\w+)\s*\([^;]*\)\s*\{")],
}

_LANG_ALIASES = {
    "py": "python", "js": "javascript", "jsx": "javascript",
    "ts": "typescript", "tsx": "typescript", "kt": "java",
    "c#": "csharp", ".net": "csharp", "dotnet": "csharp",
    "h": "cpp", "hpp": "cpp", "cc": "cpp",
}


def _normalise_lang(language: str | None) -> str:
    key = (language or "").strip().lower()
    return _LANG_ALIASES.get(key, key)


def _extract_candidates(content: str, language: str) -> list[dict]:
    patterns = _DEF_PATTERNS.get(language)
    if not patterns:
        return []
    lines = content.splitlines()
    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for kind, pat in patterns:
        rx = re.compile(pat, re.MULTILINE)
        for i, line in enumerate(lines, start=1):
            m = rx.match(line)
            if not m:
                continue
            name = m.group(1)
            if (name, kind) in seen:
                continue
            seen.add((name, kind))
            # Count usages OUTSIDE the definition line using a word-boundary search.
            body = "\n".join(lines[:i - 1] + lines[i:])
            usages = len(re.findall(rf"\b{re.escape(name)}\b", body))
            if usages == 0:
                candidates.append({"name": name, "kind": kind, "line": i,
                                    "usages_in_file": usages})
    return candidates


_SYSTEM_PROMPT = """You are a code-maintenance reviewer specialising in
identifying dead or unused symbols across a codebase.

You receive:
- A source file
- A heuristic list of symbols that appear defined but unused WITHIN the file

Your job is to classify each candidate and return STRICT JSON:

{
  "findings": [
    {
      "name": "...",
      "kind": "function|class|method|const|type|var",
      "line": 123,
      "verdict": "dead|likely_dead|public_api|framework_hook|false_positive",
      "confidence": 0.0,
      "reason": "short justification — why dead or why not",
      "safe_to_remove": true
    }
  ],
  "notes": "overall caveats (cross-file usage cannot be verified here)"
}

Rules:
- Mark as `public_api` anything exported via `__all__`, re-exported, default
  exports, public interface members, or framework entry points (Flask/FastAPI
  route handlers, Django views, React components, pytest fixtures, main).
- Mark as `framework_hook` anything that looks wired by name / annotation /
  decorator (event handlers, Spring beans, dependency injection, @pytest.fixture,
  @app.route, IoC components, @Bean, etc.).
- Mark as `false_positive` if the heuristic missed usages (string-based lookup,
  reflection, metaprogramming, overrides of a base class, abstract contract).
- Keep `confidence` in [0.0, 1.0]. `safe_to_remove` must be `true` only when
  `verdict` is `dead` and confidence >= 0.8.

Return JSON only — no fences, no prose.
"""


def _render_markdown(file_path: str, language: str, candidates: list[dict],
                     classified: dict) -> str:
    findings = classified.get("findings") or []
    dead = [f for f in findings if f.get("verdict") in ("dead", "likely_dead")]

    lines = [
        f"## Dead-Code / Unused-Symbol Detector — `{os.path.basename(file_path)}`",
        f"- **Language:** {language or 'auto'}",
        f"- **Heuristic candidates:** {len(candidates)}",
        f"- **Classified findings:** {len(findings)}",
        f"- **Likely dead:** {len(dead)}\n",
    ]
    if not findings:
        lines.append("_No unused symbols detected by the heuristic pass._")
        return "\n".join(lines)

    lines.append("| Symbol | Kind | Line | Verdict | Confidence | Safe to remove |")
    lines.append("|---|---|---:|---|---:|:---:|")
    for f in findings:
        lines.append(
            f"| `{f.get('name', '')}` | {f.get('kind', '')} | {f.get('line', '')} "
            f"| {f.get('verdict', '')} | {f.get('confidence', 0):.2f} "
            f"| {'✓' if f.get('safe_to_remove') else ''} |"
        )
    lines.append("")
    for f in findings:
        lines.append(f"- **{f.get('name', '')}** (line {f.get('line', '')}): "
                      f"{f.get('reason', '')}")
    if classified.get("notes"):
        lines.append(f"\n> {classified['notes']}")
    return "\n".join(lines)


def run_dead_code_detector(conn: duckdb.DuckDBPyConnection, job_id: str,
                           file_path: str, content: str, file_hash: str,
                           language: str | None, custom_prompt: str | None,
                           **kwargs) -> dict:
    cached = check_cache(conn, file_hash, _CACHE_KEY, language, custom_prompt)
    if cached:
        return cached

    lang_key = _normalise_lang(language)
    candidates = _extract_candidates(content, lang_key)

    if not candidates:
        result = {
            "markdown": (f"## Dead-Code / Unused-Symbol Detector — "
                          f"`{os.path.basename(file_path)}`\n\n"
                          f"_Heuristic pass found no unused symbols "
                          f"({language or 'auto'})._"),
            "summary": "No unused symbols detected.",
            "findings": [],
        }
        write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                    language=language, custom_prompt=custom_prompt, result=result)
        add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                    language=language, summary=result["summary"])
        return result

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    cand_lines = "\n".join(
        f"- {c['kind']} `{c['name']}` at line {c['line']}" for c in candidates
    )
    prompt = (f"File: {file_path}\nLanguage: {language or 'auto'}\n\n"
              f"Heuristic unused-symbol candidates:\n{cand_lines}\n\n"
              f"Source:\n```\n{content}\n```")
    raw = str(agent(prompt))
    try:
        classified = parse_json_response(raw)
    except Exception:
        classified = {"findings": [], "notes": "LLM response was not valid JSON."}

    markdown = _render_markdown(file_path, language or lang_key, candidates, classified)
    findings = classified.get("findings") or []
    dead = [f for f in findings if f.get("verdict") in ("dead", "likely_dead")]
    summary = (f"{len(dead)} likely-dead symbol(s) among {len(findings)} "
               f"candidate(s).")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join("Reports", ts, "dead_code")
    os.makedirs(out_dir, exist_ok=True)
    label = os.path.splitext(os.path.basename(file_path))[0] or "report"
    report_path = os.path.join(out_dir, f"{label}.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(markdown)

    result = {
        "markdown": markdown,
        "summary": summary,
        "candidates": candidates,
        "findings": findings,
        "output_path": report_path,
    }

    write_cache(conn, job_id=job_id, feature=_CACHE_KEY, file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature=_CACHE_KEY, source_ref=file_path,
                language=language, summary=summary)
    return result
