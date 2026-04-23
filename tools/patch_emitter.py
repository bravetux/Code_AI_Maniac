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
"""Deterministic patch-set emitter.

Shared subagent for Wave 6B agents (F9, F11, F14, F15). Takes a file path
plus either new content, a unified diff, or both (base + new) and writes:

  <reports_root>/<agent_key>/patches/<basename>        (final content)
  <reports_root>/<agent_key>/patches/<basename>.diff   (unified diff)
  <reports_root>/<agent_key>/pr_comment.md             (created or appended)
  <reports_root>/<agent_key>/summary.json              (created or merged)

No LLM involvement - pure Python stdlib.
"""

from __future__ import annotations

import difflib
import json
import os
from typing import Any


def emit(agent_key: str, reports_root: str, file_path: str,
         new_content: str | None = None,
         diff: str | None = None,
         base_content: str | None = None,
         description: str = "",
         summary_extras: dict[str, Any] | None = None) -> dict:
    """Write a PR-ready patch set for a single file.

    Exactly one input shape is required:
      1. new_content only           - new file, emits a full-add diff
      2. diff + base_content        - reverse-apply-validated
      3. base_content + new_content - emitter computes the diff
    """
    if new_content is None and diff is None:
        raise ValueError("emit() requires new_content or diff (or both with base_content)")

    basename = os.path.basename(file_path) or "unnamed"
    out_dir = os.path.join(reports_root, agent_key)
    patches_dir = os.path.join(out_dir, "patches")
    os.makedirs(patches_dir, exist_ok=True)

    content_path = os.path.join(patches_dir, basename)
    diff_path = os.path.join(patches_dir, basename + ".diff")
    pr_comment_path = os.path.join(out_dir, "pr_comment.md")
    summary_path = os.path.join(out_dir, "summary.json")

    applied = True
    final_content: str | None = None
    final_diff: str

    # Mode 2: diff + base_content -> validate reverse-apply
    if diff is not None and new_content is None:
        if base_content is None:
            raise ValueError("diff mode requires base_content for reverse-apply validation")
        try:
            _validate_diff_applies(diff, base_content)
            final_content = _apply_unified_diff(diff, base_content)
            final_diff = diff
        except _DiffApplyError:
            applied = False
            final_content = base_content  # keep original when diff rejected
            final_diff = diff
    # Mode 3: base + new -> compute diff
    elif base_content is not None and new_content is not None:
        final_content = new_content
        final_diff = _compute_diff(file_path, base_content, new_content)
    # Mode 1: new_content only
    elif new_content is not None:
        final_content = new_content
        final_diff = _compute_diff(file_path, "", new_content)
    else:
        applied = False
        final_content = None
        final_diff = diff  # type: ignore[assignment]

    if final_content is not None:
        with open(content_path, "w", encoding="utf-8") as fh:
            fh.write(final_content)
    with open(diff_path, "w", encoding="utf-8") as fh:
        fh.write(final_diff)

    pr_block = _build_pr_block(basename, description, final_diff, applied)
    if os.path.isfile(pr_comment_path):
        with open(pr_comment_path, "a", encoding="utf-8") as fh:
            fh.write("\n" + pr_block)
    else:
        with open(pr_comment_path, "w", encoding="utf-8") as fh:
            fh.write(pr_block)

    entry = {
        "file": basename,
        "description": description,
        "applied": applied,
        "content_path": content_path,
        "diff_path": diff_path,
    }
    if summary_extras:
        entry.update(summary_extras)
    _merge_summary(summary_path, entry, summary_extras)

    markdown = (
        f"Patched `{basename}` - {description}"
        if applied else
        f"Diff for `{basename}` could not be applied cleanly; raw diff written for manual review."
    )

    return {
        "markdown": markdown,
        "applied": applied,
        "paths": {
            "content": content_path,
            "diff": diff_path,
            "pr_comment": pr_comment_path,
            "summary_json": summary_path,
        },
    }


def _compute_diff(file_path: str, base: str, new: str) -> str:
    base_lines = base.splitlines(keepends=True) if base else []
    new_lines = new.splitlines(keepends=True)
    diff_iter = difflib.unified_diff(
        base_lines, new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        n=3,
    )
    return "".join(diff_iter)


class _DiffApplyError(RuntimeError):
    pass


def _validate_diff_applies(diff: str, base: str) -> None:
    """Check that every minus-side hunk line actually appears in base in order."""
    base_lines = base.splitlines()
    lines = diff.splitlines()
    base_idx = 0
    in_hunk = False
    for raw in lines:
        if raw.startswith("@@"):
            in_hunk = True
            try:
                minus_spec = raw.split(" ")[1]
                hunk_base_line = int(minus_spec[1:].split(",")[0]) - 1
                base_idx = hunk_base_line
            except (IndexError, ValueError):
                raise _DiffApplyError(f"unparseable hunk header: {raw!r}")
            continue
        if not in_hunk:
            continue
        if raw.startswith("---") or raw.startswith("+++"):
            continue
        if raw.startswith(" "):
            if base_idx >= len(base_lines) or base_lines[base_idx] != raw[1:]:
                raise _DiffApplyError(f"context mismatch at line {base_idx + 1}")
            base_idx += 1
        elif raw.startswith("-"):
            if base_idx >= len(base_lines) or base_lines[base_idx] != raw[1:]:
                raise _DiffApplyError(f"removed line mismatch at line {base_idx + 1}")
            base_idx += 1
        elif raw.startswith("+"):
            continue
        else:
            continue


def _apply_unified_diff(diff: str, base: str) -> str:
    """Apply a unified diff to ``base``. Assumes validation already passed."""
    base_lines = base.splitlines(keepends=True)
    out: list[str] = []
    lines = diff.splitlines()
    base_idx = 0
    in_hunk = False
    for raw in lines:
        if raw.startswith("@@"):
            try:
                minus_spec = raw.split(" ")[1]
                hunk_base_line = int(minus_spec[1:].split(",")[0]) - 1
            except (IndexError, ValueError):
                raise _DiffApplyError("unparseable hunk header")
            while base_idx < hunk_base_line and base_idx < len(base_lines):
                out.append(base_lines[base_idx])
                base_idx += 1
            in_hunk = True
            continue
        if not in_hunk or raw.startswith("---") or raw.startswith("+++"):
            continue
        if raw.startswith(" "):
            if base_idx < len(base_lines):
                out.append(base_lines[base_idx])
                base_idx += 1
        elif raw.startswith("-"):
            base_idx += 1
        elif raw.startswith("+"):
            out.append(raw[1:] + ("\n" if not raw[1:].endswith("\n") else ""))
    while base_idx < len(base_lines):
        out.append(base_lines[base_idx])
        base_idx += 1
    return "".join(out)


def _build_pr_block(basename: str, description: str,
                    diff: str, applied: bool) -> str:
    status_suffix = "" if applied else " *(diff did not apply cleanly)*"
    header = f"## `{basename}`{status_suffix}"
    desc_line = description or "_(no description)_"
    diff_preview = diff.strip() or "_(no diff)_"
    return f"{header}\n\n{desc_line}\n\n```diff\n{diff_preview}\n```\n"


def _merge_summary(path: str, entry: dict, summary_extras: dict | None) -> None:
    existing: dict = {"files": []}
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                existing = json.load(fh)
        except (OSError, ValueError):
            existing = {"files": []}
    existing.setdefault("files", []).append(entry)
    if summary_extras:
        for k, v in summary_extras.items():
            if k in ("file", "description", "applied",
                     "content_path", "diff_path"):
                continue
            if isinstance(v, list):
                existing.setdefault(k, []).extend(v)
            else:
                existing[k] = v
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(existing, fh, indent=2)
