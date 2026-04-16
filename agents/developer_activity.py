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

_SYSTEM_PROMPT = """You are a software engineering analytics expert analysing a git commit history to produce
a Developer Activity & Contribution report.

Produce a thorough markdown report with these sections:

## Executive Summary
2-4 bullet overview: total commits analysed, number of unique contributors, dominant activity type
(feature work, bug-fixing, chores, etc.), and any standout observation.

## Contributor Breakdown
For each author (sorted by commit count, descending):
- Commit count and percentage of total
- Primary activity type (features, fixes, refactors, docs, etc.) inferred from messages
- Key contributions (summarise, don't just list messages)
- Files/areas most touched (if file data is available)

## Activity Timeline
(Only if commit dates are available — skip this section entirely if dates are absent.)
- Commit frequency over time (daily/weekly patterns)
- Active vs quiet periods
- Bursts of activity and what they correspond to

## Collaboration Patterns
- Shared file ownership — files modified by multiple authors (if file data available)
- Co-authorship or pair-programming signals in messages
- Areas with single-author ownership (bus-factor risk)

## Recommendations
- Bus-factor risks (critical areas owned by a single person)
- Workload imbalances
- Knowledge-sharing suggestions

Guidelines:
- Be data-driven — cite numbers and specific examples
- If file change data is not available, skip file-based analysis without apology
- If date data is not available, skip time-based analysis without apology
- Focus on actionable insights, not just statistics"""


def run_developer_activity(conn: duckdb.DuckDBPyConnection, job_id: str,
                           repo_ref: str, commits: list[dict],
                           custom_prompt: str | None) -> dict:
    if not commits:
        return {
            "markdown": "No commits provided for developer activity analysis.",
            "summary": "No commits to analyze.",
        }

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=resolve_prompt(custom_prompt, _SYSTEM_PROMPT))

    # Detect available data fields for graceful degradation
    sample = commits[0] if commits else {}
    data_notes = []
    if "date" not in sample or not sample.get("date"):
        data_notes.append("NOTE: Commit dates are not available. Skip all time-based analysis.")
    if "files_changed" not in sample or not sample.get("files_changed"):
        data_notes.append("NOTE: File change lists are not available. Skip file-ownership analysis.")
    data_preamble = "\n".join(data_notes) + "\n\n" if data_notes else ""

    batch_size = 30
    section_docs = []

    for i in range(0, len(commits), batch_size):
        batch = commits[i:i + batch_size]
        prompt = (data_preamble
                  + f"Repository: {repo_ref}\n"
                  f"Commits {i + 1}–{i + len(batch)} of {len(commits)}:\n"
                  + json.dumps(batch, indent=2))
        section_docs.append(str(agent(prompt)))

    if len(section_docs) > 1:
        synthesis_prompt = (
            f"You produced partial developer activity reports for {len(commits)} commits "
            f"from {repo_ref} in batches. Merge them into one cohesive report. "
            "Sum commit counts per author across batches. De-duplicate and consolidate. "
            "Keep the same section structure.\n\n"
            + "\n\n---\n\n".join(section_docs)
        )
        markdown = str(agent(synthesis_prompt))
    else:
        markdown = section_docs[0] if section_docs else ""

    summary = f"Developer activity report for {len(commits)} commits ({repo_ref})."
    result = {
        "markdown": markdown,
        "summary": summary,
    }
    add_history(conn, job_id=job_id, feature="developer_activity", source_ref=repo_ref,
                language=None, summary=summary)
    return result
