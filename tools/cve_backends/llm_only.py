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

"""LLM-only CVE assessment backend. Uses Bedrock training knowledge."""
from __future__ import annotations
import json
from agents._bedrock import make_bedrock_model, parse_json_response
from strands import Agent

_SYSTEM_PROMPT = """You are a software security expert assessing dependency risks.
For each package and version, assess known vulnerabilities from your training data.
Return JSON: {"assessments": [{"package": "<name>", "vulnerabilities": [{"cve_id": "<ID or LLM-assessment>", "summary": "<desc>", "severity": "<critical|major|minor>", "fixed_in": "<version>"}]}]}
If no vulnerabilities known, return empty list. Be conservative."""

def lookup_llm(packages: list[dict]) -> list[dict]:
    if not packages: return []
    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)
    pkg_list = "\n".join(f"- {p['name']} {p.get('version', 'unknown')} ({p.get('ecosystem', 'unknown')})" for p in packages)
    raw = str(agent(f"Assess these dependencies for known vulnerabilities:\n\n{pkg_list}"))
    try:
        parsed = parse_json_response(raw)
        assessments = {a["package"]: a for a in parsed.get("assessments", [])}
    except (json.JSONDecodeError, ValueError, KeyError):
        assessments = {}
    results = []
    for pkg in packages:
        assessment = assessments.get(pkg["name"], {})
        vulns = [{"cve_id": v.get("cve_id", "LLM-assessment"), "summary": v.get("summary", ""),
                  "severity": v.get("severity", "major"), "fixed_in": v.get("fixed_in"), "source": "llm"}
                 for v in assessment.get("vulnerabilities", [])]
        results.append({"package": pkg["name"], "version": pkg.get("version"), "ecosystem": pkg.get("ecosystem", ""), "vulnerabilities": vulns})
    return results
