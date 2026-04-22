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

"""F21 — Pre-Commit / Staged-Change Reviewer.

A standalone CLI that:

1. Reads the list of staged files from ``git diff --cached``.
2. For each file, pulls the STAGED blob (so the review runs on exactly what
   will be committed, not the working tree).
3. Invokes a subset of existing agents (bug_analysis, static_analysis,
   secret_scan) directly — the orchestrator and agents themselves are not
   modified.
4. Prints a concise report and exits non-zero when critical findings surface.

Install as a git hook:

    python tools/precommit_reviewer.py --install-hook

This writes ``.git/hooks/pre-commit`` that invokes the reviewer. Commits fail
when the reviewer exits non-zero.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import uuid
from typing import Optional

from db.connection import get_connection
from tools.language_detect import detect_language
from tools.secret_scanner import scan_secrets


_CRITICAL_KEYWORDS = {"critical", "high", "severe", "blocker"}
_HOOK_SCRIPT = """#!/bin/sh
# AI Code Maniac pre-commit reviewer (F21)
exec python tools/precommit_reviewer.py "$@"
"""


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return out.stdout
    except subprocess.CalledProcessError as e:
        return e.stdout or ""


def _staged_files() -> list[str]:
    """Paths of files added / modified in the index."""
    text = _run(["git", "diff", "--cached", "--name-only",
                 "--diff-filter=AM"])
    return [p.strip() for p in text.splitlines() if p.strip()]


def _read_staged_blob(path: str) -> Optional[str]:
    """Return the staged version of ``path`` (what git will commit)."""
    try:
        out = subprocess.run(
            ["git", "show", f":{path}"],
            capture_output=True, check=True,
        )
        return out.stdout.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError:
        return None


def _file_hash(content: str) -> str:
    import hashlib
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def _analyse_file(conn, job_id: str, path: str, content: str,
                  language: str | None) -> dict:
    """Invoke existing agents — no edits to those modules."""
    from agents.bug_analysis import run_bug_analysis
    from agents.static_analysis import run_static_analysis

    file_hash = _file_hash(content)
    common = dict(conn=conn, job_id=job_id, file_path=path,
                  content=content, file_hash=file_hash,
                  language=language, custom_prompt=None)

    out: dict = {"path": path, "language": language}

    # Fast local secret scan first.
    try:
        out["secrets"] = scan_secrets(content, mode="warn")
    except Exception as e:
        out["secrets"] = {"error": str(e), "secrets_found": []}

    try:
        out["bug_analysis"] = run_bug_analysis(**common)
    except Exception as e:
        out["bug_analysis"] = {"error": str(e)}

    try:
        out["static_analysis"] = run_static_analysis(**common)
    except Exception as e:
        out["static_analysis"] = {"error": str(e)}

    return out


def _is_critical(file_report: dict) -> bool:
    if file_report.get("secrets", {}).get("secrets_found"):
        return True
    for key in ("bug_analysis", "static_analysis"):
        summary = (file_report.get(key) or {}).get("summary", "") or ""
        lowered = summary.lower()
        if any(k in lowered for k in _CRITICAL_KEYWORDS):
            return True
    return False


def _format_report(reports: list[dict]) -> str:
    lines = ["=" * 72, "1128 Pre-Commit Review (F21)", "=" * 72]
    for r in reports:
        lines.append(f"\n--- {r['path']} ({r.get('language') or 'auto'}) ---")
        secrets = r.get("secrets", {}).get("secrets_found") or []
        if secrets:
            lines.append(f"  ! secrets: {len(secrets)} finding(s)")
            for s in secrets[:5]:
                lines.append(f"    · {s.get('rule_id', '?')} "
                             f"line {s.get('line', '?')}")
        for key in ("bug_analysis", "static_analysis"):
            section = r.get(key) or {}
            if "error" in section:
                lines.append(f"  ! {key}: ERROR {section['error']}")
            elif section.get("summary"):
                lines.append(f"  · {key}: {section['summary']}")
    return "\n".join(lines) + "\n"


def _install_hook() -> int:
    root = _run(["git", "rev-parse", "--show-toplevel"]).strip()
    if not root:
        print("Not inside a git repository.", file=sys.stderr)
        return 2
    hook_dir = os.path.join(root, ".git", "hooks")
    hook_path = os.path.join(hook_dir, "pre-commit")
    os.makedirs(hook_dir, exist_ok=True)
    with open(hook_path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(_HOOK_SCRIPT)
    try:
        os.chmod(hook_path, 0o755)
    except OSError:
        pass  # Windows: permissions are noisy but don't block execution.
    print(f"Installed hook → {hook_path}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="F21 Pre-commit reviewer")
    parser.add_argument("--install-hook", action="store_true",
                        help="Write .git/hooks/pre-commit and exit.")
    parser.add_argument("--warn-only", action="store_true",
                        help="Always exit 0 regardless of findings.")
    parser.add_argument("--max-files", type=int, default=20)
    args = parser.parse_args(argv)

    if args.install_hook:
        return _install_hook()

    files = _staged_files()[:args.max_files]
    if not files:
        print("Nothing staged — skipping review.")
        return 0

    conn = get_connection()
    job_id = str(uuid.uuid4())
    reports: list[dict] = []
    critical = 0

    for path in files:
        blob = _read_staged_blob(path)
        if blob is None or not blob.strip():
            continue
        lang = detect_language(path)
        # Skip binary-ish content cheaply.
        if "\0" in blob[:4096]:
            continue
        report = _analyse_file(conn, job_id, path, blob, lang)
        if _is_critical(report):
            critical += 1
        reports.append(report)

    sys.stdout.write(_format_report(reports))
    if critical and not args.warn_only:
        sys.stdout.write(f"\nBlocking commit — {critical} critical finding(s).\n"
                         f"Re-run with --warn-only to override locally.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
