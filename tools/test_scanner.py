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

"""Deterministic test-file scanner.

Subagent for F10 (traceability_matrix). Walks a folder and extracts test
identities by file type - no LLM. Emits a flat list of
``{file, test_name, kind, line, snippet}`` records.
"""

from __future__ import annotations

import json
import os
import re
from typing import Iterable

_PYTHON_TEST_RE = re.compile(r"^\s*def\s+(test_\w+)\s*\(", re.MULTILINE)

_JUNIT_TEST_RE = re.compile(
    r"@Test(?:\([^)]*\))?\s*(?:\w+\s+)*(?:void|[A-Z]\w*)\s+(\w+)\s*\(",
)
_XUNIT_FACT_RE = re.compile(r"\[(Fact|Theory)\][^\[]*?(?:public|internal|private)?\s+\w+\s+(\w+)\s*\(")

_JEST_IT_RE = re.compile(r"""(?:^|\s)(?:it|test)\s*\(\s*['"`]([^'"`]+)['"`]""", re.MULTILINE)

_GHERKIN_SCENARIO_RE = re.compile(r"^\s*Scenario(?:\s*Outline)?\s*:\s*(.+)$", re.MULTILINE)
_ROBOT_CASE_RE = re.compile(r"^\*\*\*\s*Test Cases\s*\*\*\*\s*$(.*?)(?:^\*\*\*|\Z)",
                            re.MULTILINE | re.DOTALL)
_ROBOT_NAME_RE = re.compile(r"^([^\s#].+)$", re.MULTILINE)

_JMX_TXN_RE = re.compile(r'<TransactionController[^>]*testname="([^"]+)"')

_POSTMAN_SCHEMA_MARK = "schema.getpostman.com/json/collection/v2.1.0"


def scan_tests(root: str) -> list[dict]:
    """Return test records for every recognised file under ``root``."""
    if not os.path.isdir(root):
        return []
    out: list[dict] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            try:
                out.extend(_scan_one(full))
            except (OSError, ValueError):
                continue
    return out


def _scan_one(path: str) -> Iterable[dict]:
    name = os.path.basename(path).lower()
    if name.endswith(".py"):
        if name.startswith("test_") or name.endswith("_test.py") or "/tests/" in path.replace("\\", "/"):
            yield from _scan_pytest(path)
        return
    if name.endswith(".java") and ("test" in name):
        yield from _scan_junit(path)
        return
    if name.endswith(".cs") and ("test" in name):
        yield from _scan_xunit(path)
        return
    if name.endswith(".test.ts") or name.endswith(".test.js") or \
       name.endswith(".spec.ts") or name.endswith(".spec.js"):
        yield from _scan_jest(path)
        return
    if name.endswith(".feature"):
        yield from _scan_gherkin(path)
        return
    if name.endswith(".robot"):
        yield from _scan_robot(path)
        return
    if name.endswith(".jmx"):
        yield from _scan_jmx(path)
        return
    if name.endswith(".json"):
        yield from _scan_postman(path)
        return


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _scan_pytest(path: str) -> Iterable[dict]:
    text = _read(path)
    lines = text.splitlines()
    for m in _PYTHON_TEST_RE.finditer(text):
        name = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        snippet = "\n".join(lines[line_no - 1:line_no + 4])
        yield {"file": path, "test_name": name, "kind": "pytest",
               "line": line_no, "snippet": snippet}


def _scan_junit(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _JUNIT_TEST_RE.finditer(text):
        name = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "junit",
               "line": line_no, "snippet": name}


def _scan_xunit(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _XUNIT_FACT_RE.finditer(text):
        name = m.group(2)
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "xunit",
               "line": line_no, "snippet": name}


def _scan_jest(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _JEST_IT_RE.finditer(text):
        name = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "jest",
               "line": line_no, "snippet": name}


def _scan_gherkin(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _GHERKIN_SCENARIO_RE.finditer(text):
        name = m.group(1).strip()
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "gherkin",
               "line": line_no, "snippet": name}


def _scan_robot(path: str) -> Iterable[dict]:
    text = _read(path)
    for block_m in _ROBOT_CASE_RE.finditer(text):
        block = block_m.group(1) or ""
        base_line = text[:block_m.start(1)].count("\n") + 1
        for name_m in _ROBOT_NAME_RE.finditer(block):
            name = name_m.group(1).strip()
            if not name or name.startswith("#"):
                continue
            line_no = base_line + block[:name_m.start()].count("\n")
            yield {"file": path, "test_name": name, "kind": "robot",
                   "line": line_no, "snippet": name}


def _scan_jmx(path: str) -> Iterable[dict]:
    text = _read(path)
    for m in _JMX_TXN_RE.finditer(text):
        name = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        yield {"file": path, "test_name": name, "kind": "jmeter",
               "line": line_no, "snippet": name}


def _scan_postman(path: str) -> Iterable[dict]:
    try:
        text = _read(path)
        if _POSTMAN_SCHEMA_MARK not in text:
            return
        doc = json.loads(text)
    except (ValueError, OSError):
        return
    for idx, item in enumerate(doc.get("item") or []):
        if isinstance(item, dict) and item.get("name"):
            yield {"file": path, "test_name": item["name"], "kind": "postman",
                   "line": idx + 1, "snippet": item["name"]}
