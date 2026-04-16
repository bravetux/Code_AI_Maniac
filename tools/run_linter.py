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
# Developed: 12th April 2026

import subprocess
import json

try:
    from strands import tool
except ImportError:
    def tool(f): return f


@tool
def run_linter(file_path: str, language: str) -> dict:
    """Run static linters on a file. Returns findings list."""
    lang = language.lower().strip()

    if lang in ("python", "py"):
        return _run_flake8(file_path)
    elif lang in ("javascript", "js", "typescript", "ts"):
        return _run_eslint(file_path)
    else:
        return {"findings": [], "skipped": True, "reason": f"No linter for {language}"}


def _run_flake8(file_path: str) -> dict:
    try:
        result = subprocess.run(
            ["flake8", file_path],
            capture_output=True, text=True, timeout=30
        )
        findings = []
        for line in result.stdout.strip().splitlines():
            # flake8 default format: path:line:col: code message
            parts = line.split(":")
            if len(parts) >= 4:
                findings.append({
                    "line": int(parts[1]) if parts[1].strip().isdigit() else 0,
                    "col": int(parts[2]) if parts[2].strip().isdigit() else 0,
                    "code": parts[3].strip().split()[0] if parts[3].strip() else "",
                    "message": ":".join(parts[3:]).strip(),
                    "tool": "flake8",
                })
        return {"findings": findings, "skipped": False}
    except FileNotFoundError:
        return {"findings": [], "skipped": True, "reason": "flake8 not installed"}
    except subprocess.TimeoutExpired:
        return {"findings": [], "skipped": True, "reason": "linter timed out"}


def _run_eslint(file_path: str) -> dict:
    try:
        result = subprocess.run(
            ["eslint", "--format=json", file_path],
            capture_output=True, text=True, timeout=30
        )
        raw = json.loads(result.stdout or "[]")
        findings = []
        for file_result in raw:
            for msg in file_result.get("messages", []):
                findings.append({
                    "line": msg.get("line", 0),
                    "col": msg.get("column", 0),
                    "code": msg.get("ruleId", ""),
                    "message": msg.get("message", ""),
                    "tool": "eslint",
                })
        return {"findings": findings, "skipped": False}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"findings": [], "skipped": True, "reason": "eslint not installed or parse error"}
    except subprocess.TimeoutExpired:
        return {"findings": [], "skipped": True, "reason": "linter timed out"}
