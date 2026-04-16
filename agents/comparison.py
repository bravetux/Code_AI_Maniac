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
from agents._bedrock import make_bedrock_model, parse_json_response

_SYSTEM_PROMPT = """You are a senior software engineering lead comparing multiple code analysis results for the same or related source files.

You will receive 2–5 analysis results (each labelled with an ID like #1, #2, etc.).
Each result contains the output of one or more analysis agents (bug analysis, static analysis, code design, etc.).

Your job is to produce a structured, insightful comparison:

1. **Overall verdict** — which analysis run produced the most thorough or actionable results and why.
2. **Key differences** — findings that appeared in one run but not another (e.g. bugs caught in #1 but missed in #2).
3. **Common findings** — issues that appear across all runs (high-confidence problems).
4. **Quality assessment** — rate each run on depth, accuracy, and actionability (1–5 scale).
5. **Recommendation** — which run's results should the team act on, and any findings from other runs worth incorporating.

Return a JSON object:
{
  "verdict": "<one-paragraph overall verdict>",
  "differences": [
    {
      "finding": "<what was found>",
      "present_in": ["#1", "#3"],
      "absent_from": ["#2"],
      "significance": "<high|medium|low>"
    }
  ],
  "common_findings": [
    {
      "finding": "<issue found in all runs>",
      "confidence": "<high|medium>"
    }
  ],
  "quality_scores": [
    {
      "run": "#1",
      "depth": <1-5>,
      "accuracy": <1-5>,
      "actionability": <1-5>,
      "notes": "<brief note>"
    }
  ],
  "recommendation": "<which run to act on and what to incorporate from others>",
  "summary": "<two-sentence executive summary>"
}"""


def run_comparison(analyses: list[dict]) -> dict:
    """
    Compare 2–5 analysis results using a Strands/Bedrock agent.

    Each item in *analyses* should have:
      - label:       e.g. "#1 file.py (04/10 07:08)"
      - feature:     e.g. "Bug Analysis"
      - source_ref:  file path
      - result_json: the full result dict from that job
    """
    if len(analyses) < 2:
        return {"error": "Need at least 2 analyses to compare."}

    # Build the user prompt with each analysis labelled
    parts = []
    for item in analyses:
        label = item["label"]
        feature = item["feature"]
        source = item["source_ref"]
        rj = item["result_json"]

        # Extract only the relevant feature data to keep the prompt focused
        feature_key_map = {
            "Bug Analysis": "bug_analysis",
            "Code Design": "code_design",
            "Code Flow": "code_flow",
            "Mermaid Diagram": "mermaid",
            "Requirements": "requirement",
            "Static Analysis": "static_analysis",
            "PR Comments": "comment_generator",
            "Commit Analysis": "commit_analysis",
        }
        fk = feature_key_map.get(feature, feature)
        feature_data = rj.get(fk, rj)

        # Truncate very large results to stay within token limits
        serialized = json.dumps(feature_data, indent=2, ensure_ascii=False)
        if len(serialized) > 8000:
            serialized = serialized[:8000] + "\n... (truncated)"

        parts.append(
            f"--- {label} ---\n"
            f"Feature: {feature}\n"
            f"Source: {source}\n"
            f"Results:\n{serialized}\n"
        )

    user_prompt = (
        f"Compare these {len(analyses)} analysis results:\n\n"
        + "\n".join(parts)
    )

    model = make_bedrock_model()
    agent = Agent(model=model, system_prompt=_SYSTEM_PROMPT)
    raw = str(agent(user_prompt))

    try:
        result = parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        # If JSON parsing fails, return the raw text as the verdict
        result = {
            "verdict": raw,
            "differences": [],
            "common_findings": [],
            "quality_scores": [],
            "recommendation": "",
            "summary": "AI comparison completed (unstructured response).",
        }

    return result
