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
import duckdb
from strands import Agent
from agents._bedrock import make_bedrock_model, resolve_prompt
from db.queries.history import add_history

_SYSTEM_PROMPT = """You are a software engineering analytics expert specialising in code churn analysis.
You are given a git commit history with file-level change data. Your job is to identify hotspots —
files and directories that change most frequently — and assess the associated risks.

Produce a thorough markdown report with these sections:

## Hot Spots Summary
List the top 15-20 most frequently changed files, sorted by change count.
Present as a table: | File | Changes | Last Changed By | Risk |
Risk is high/medium/low based on change frequency relative to the repository average.

## Directory-Level Analysis
Aggregate file changes to the directory/module level. Which areas of the codebase are
most active? Present as a table: | Directory | Total File Changes | Unique Files |

## Co-Change Patterns
Identify files that frequently change together in the same commit. These suggest tight
coupling and may indicate:
- Hidden dependencies
- Shotgun surgery anti-pattern
- Candidates for refactoring into a single module

## Stability Report
- Files/directories with zero or very few changes (stable core)
- Note: stable could mean "well-designed" or "dead code" — flag both possibilities

## Risk Assessment
- High-churn files are statistically more likely to contain bugs
- Files with many authors AND high churn are highest risk
- Flag any files that appear to be accumulating technical debt (frequent small fixes)

## Recommendations
- Refactoring candidates (high churn + tight coupling)
- Test coverage priorities (high-churn files should have strong tests)
- Code review focus areas

Guidelines:
- Be data-driven — cite exact file names and counts
- Use tables for readability
- Focus on actionable insights"""


def run_churn_analysis(conn: duckdb.DuckDBPyConnection, job_id: str,
                       repo_ref: str, commits: list[dict],
                       custom_prompt: str | None) -> dict:
    if not commits:
        return {
            "markdown": "No commits provided for churn analysis.",
            "summary": "No commits to analyze.",
        }

    # Hard gate: requires files_changed data
    sample = commits[0] if commits else {}
    if not sample.get("files_changed"):
        return {
            "markdown": (
                "## Churn Analysis Unavailable\n\n"
                "Churn analysis requires file-level change data (`files_changed`), "
                "which is only available when using the **GitHub (Clone)** source.\n\n"
                "Please re-run using **GitHub (Clone)** mode to enable this analysis."
            ),
            "summary": "Skipped — no file change data available.",
        }

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    batch_size = 30
    section_docs = []

    for i in range(0, len(commits), batch_size):
        batch = commits[i:i + batch_size]
        prompt = (f"Repository: {repo_ref}\n"
                  f"Commits {i + 1}–{i + len(batch)} of {len(commits)}:\n"
                  + json.dumps(batch, indent=2))
        section_docs.append(str(agent(prompt)))

    if len(section_docs) > 1:
        synthesis_prompt = (
            f"You analysed file churn for {len(commits)} commits from {repo_ref} in batches. "
            "Merge the partial analyses into one cohesive report. Sum file change counts "
            "across batches to produce accurate totals. De-duplicate co-change patterns. "
            "Keep the same section structure.\n\n"
            + "\n\n---\n\n".join(section_docs)
        )
        markdown = str(agent(synthesis_prompt))
    else:
        markdown = section_docs[0] if section_docs else ""

    summary = f"Churn analysis for {len(commits)} commits ({repo_ref})."
    result = {
        "markdown": markdown,
        "summary": summary,
    }
    add_history(conn, job_id=job_id, feature="churn_analysis", source_ref=repo_ref,
                language=None, summary=summary)
    return result
