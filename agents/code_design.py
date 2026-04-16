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

import json
import re
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt, parse_json_response
from tools.chunk_file import chunk_by_lines
from tools.cache import check_cache, write_cache
from db.queries.history import add_history

_ANALYSIS_SYSTEM_PROMPT = """You are a principal software architect conducting a collaborative design review.

Your approach mirrors how a senior engineer thinks during a pairing session:
1. Read the code carefully to understand its purpose, structure, and patterns in use.
2. Identify design-level concerns — coupling, cohesion, single-responsibility violations,
   abstraction leaks, naming, error handling strategy.
3. Treat any bug findings as *symptoms* of a design decision. Ask: what design choice
   made this bug possible or likely?
4. Propose prioritised, concrete improvements with rationale — not generic advice."""

_TURN2_INSTRUCTION = """Produce a JSON analysis object with this structure.
Do NOT include a markdown field and do NOT write the design document yet — that comes in the next step.

{
  "title": "<component or module name>",
  "purpose": "<what this code does — 2-3 sentences>",
  "design_assessment": "<honest overall assessment: strengths vs weaknesses>",
  "responsibilities": ["<responsibility this module owns>"],
  "design_issues": [
    {
      "issue": "<design problem name>",
      "root_cause": "<which design decision causes this>",
      "impact": "<what breaks or becomes hard because of this>",
      "recommendation": "<specific, actionable improvement>",
      "priority": "<high|medium|low>"
    }
  ],
  "public_api": [
    {"name": "<function or class>", "signature": "<signature>", "description": "<what it does>"}
  ],
  "dependencies": ["<import or external system>"],
  "data_contracts": "<description of inputs, outputs, and data shapes>",
  "improvements": ["<concrete improvement, ordered by impact>"]
}
Return ONLY valid JSON. No markdown fences."""

_TURN3_PROMPT = """Based on your analysis of {title}, write a complete professional Design Document in markdown.

Write as you would for a technical wiki that will be read by:
- New engineers joining the team (need context and rationale)
- Senior architects reviewing the design (need depth and honesty)
- Stakeholders understanding the system (need a clear executive summary)

Use this structure exactly:

# {title} — Design Document

## Executive Summary
2-3 paragraphs. What is this component? What business or technical problem does it solve?
Who uses it and how? Write so a non-technical reader understands its value.

## Architecture Overview
How is this component structured internally? What are its main parts and how do they interact?
Reference actual class/function names from the code.

## Responsibilities & Scope
What is this component explicitly responsible for?
What is explicitly OUT of scope? (Clear boundaries prevent scope creep.)

## Interface & Public API
Document key functions, classes, or endpoints. Include:
- Parameter names and types
- Return values
- Important preconditions or invariants
- Usage example where helpful

## Data Flow
How does data enter this component, how is it transformed internally, and how does it exit?
Trace the main happy-path data flow step by step.

## Design Decisions & Rationale
What key design choices were made in this code? Why? What alternatives exist?
This section is the most valuable for future maintainers — be honest about trade-offs.

## Known Issues & Technical Debt
{analysis_summary}

List each issue with its severity and recommended remediation. Be direct — sugarcoating technical
debt makes it harder to prioritise.

## Improvement Roadmap
Ordered list of recommended improvements by impact. For each: what to do, why it matters,
rough effort estimate (small/medium/large).

## Dependencies
External systems, libraries, and services this component relies on, and what it uses each for."""


def run_code_design(conn: duckdb.DuckDBPyConnection, job_id: str,
                    file_path: str, content: str, file_hash: str,
                    language: str | None, custom_prompt: str | None,
                    bug_results: dict | None = None,
                    static_results: dict | None = None) -> dict:
    cached = check_cache(conn, file_hash, "code_design", language, custom_prompt)
    if cached:
        return cached

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _ANALYSIS_SYSTEM_PROMPT))

    # ── Turn 1: understand the code structure ─────────────────────────────────
    chunks = chunk_by_lines(content, max_tokens=6000)
    if len(chunks) == 1:
        turn1 = f"Language: {language or 'detect from code'}\nFile: {file_path}\n\n{content}"
    else:
        summaries = []
        for chunk in chunks:
            p = (f"Summarise this section for a design review "
                 f"(lines {chunk['start_line']}-{chunk['end_line']}):\n{chunk['content']}")
            summaries.append(str(agent(p)))
        turn1 = (f"Language: {language or 'detect from code'}\nFile: {file_path}\n\n"
                 f"Code (summarised in sections):\n\n" + "\n---\n".join(summaries))

    structure_notes = str(agent(turn1))

    # ── Turn 2: structured analysis (JSON only, no document) ──────────────────
    context_parts = [f"Your structural analysis of the code:\n{structure_notes}"]

    bugs = (bug_results or {}).get("bugs", [])
    if bugs:
        context_parts.append(
            f"Bugs found by automated bug analysis ({len(bugs)} total):\n"
            + json.dumps(bugs, indent=2)
        )
    if (bug_results or {}).get("narrative"):
        context_parts.append(f"Bug analysis narrative:\n{bug_results['narrative']}")

    semantic = (static_results or {}).get("semantic_findings", [])
    linter   = (static_results or {}).get("linter_findings", [])
    if semantic or linter:
        context_parts.append(
            f"Static analysis findings ({len(linter + semantic)} total):\n"
            + json.dumps(linter + semantic, indent=2)
        )

    turn2 = "\n\n".join(context_parts) + f"\n\n{_TURN2_INSTRUCTION}"
    raw = str(agent(turn2))

    try:
        result = parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        # Turn 2 failed — store raw response, skip Turn 3
        result = {
            "markdown": raw, "design_document": "", "title": file_path, "purpose": "",
            "design_assessment": "", "responsibilities": [],
            "design_issues": [], "public_api": [], "dependencies": [],
            "data_contracts": "", "improvements": [],
        }
        write_cache(conn, job_id=job_id, feature="code_design", file_hash=file_hash,
                    language=language, custom_prompt=custom_prompt, result=result)
        add_history(conn, job_id=job_id, feature="code_design", source_ref=file_path,
                    language=language, summary=result.get("purpose", "Design analysis generated."))
        return result

    # ── Turn 3: write the design document in pure prose ───────────────────────
    if result.get("design_issues"):
        issue_lines = []
        for issue in result["design_issues"]:
            priority = issue.get("priority", "low").upper()
            name = issue.get("issue", "")
            rec  = issue.get("recommendation", "")
            issue_lines.append(f"- [{priority}] **{name}**: {rec}")
        analysis_summary = "\n".join(issue_lines)
    else:
        analysis_summary = "No significant design issues identified."

    turn3 = _TURN3_PROMPT.format(
        title=result.get("title", file_path),
        analysis_summary=analysis_summary,
    )
    try:
        design_document = str(agent(turn3))
    except Exception:
        design_document = ""

    result["design_document"] = design_document
    result["markdown"] = design_document  # backwards compat for renderer and cache readers

    write_cache(conn, job_id=job_id, feature="code_design", file_hash=file_hash,
                language=language, custom_prompt=custom_prompt, result=result)
    add_history(conn, job_id=job_id, feature="code_design", source_ref=file_path,
                language=language, summary=result.get("purpose", "Design document generated."))
    return result
