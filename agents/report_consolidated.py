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

"""Consolidated Report Agent.

Synthesizes all per-file analysis results into a single cohesive document.
Supports three modes:
  - template : pure assembly, no LLM calls
  - llm      : single LLM call to produce a full narrative document
  - hybrid   : template skeleton with LLM-generated executive summary,
                architecture overview, and conclusion sections
"""

import json
import os
from datetime import datetime, timezone
from strands import Agent
from agents._bedrock import make_bedrock_model

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FEATURE_LABELS = {
    "requirement": "Requirements",
    "code_flow": "Code Flow",
    "code_design": "Code Design",
    "bug_analysis": "Bug Analysis",
    "static_analysis": "Static Analysis",
    "mermaid": "Mermaid Diagrams",
    "comment_generator": "PR Comments",
}

_MAX_CONTEXT_PER_FILE = 3000  # chars, to avoid token overflow


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_consolidated_report(
    per_file_reports: list[str],
    all_results: dict,
    file_paths: list[str],
    features: list[str],
    language: str,
    mode: str = "template",
) -> str:
    """Generate a consolidated analysis report.

    Parameters
    ----------
    per_file_reports : list of markdown strings, one per file
    all_results      : dict mapping file_path -> {feature -> result_dict}
    file_paths       : ordered list of file paths analysed
    features         : list of feature keys that were run
    language         : primary programming language
    mode             : 'template' | 'llm' | 'hybrid'

    Returns
    -------
    str  Markdown document
    """
    if mode == "llm":
        return _build_llm(per_file_reports, all_results, file_paths, features, language)
    if mode == "hybrid":
        return _build_hybrid(per_file_reports, all_results, file_paths, features, language)
    # default: template
    return _build_template(per_file_reports, all_results, file_paths, features, language)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _slug(text: str) -> str:
    """Generate a simple GitHub-style anchor slug from heading text."""
    slug = text.lower()
    slug = slug.replace(" ", "-")
    # keep only alphanumeric, hyphens, underscores, dots
    slug = "".join(c for c in slug if c.isalnum() or c in "-_.")
    return slug


def _compute_stats(all_results: dict, features: list[str]) -> list[tuple[str, str]]:
    """Return (label, value) pairs for the summary statistics table."""
    rows: list[tuple[str, str]] = []

    file_count = len(all_results)
    rows.append(("Files Analyzed", str(file_count)))
    rows.append(("Features Run", str(len(features))))

    # Bug counts from bug_analysis
    total_bugs = 0
    critical_bugs = 0
    if "bug_analysis" in features:
        for file_data in all_results.values():
            ba = file_data.get("bug_analysis", {})
            bugs = ba.get("bugs", [])
            total_bugs += len(bugs)
            for bug in bugs:
                sev = str(bug.get("severity", "")).lower()
                if sev == "critical":
                    critical_bugs += 1
        rows.append(("Total Bugs Found", str(total_bugs)))
        rows.append(("Critical Bugs", str(critical_bugs)))

    # Static analysis / linter findings
    linter_count = 0
    if "static_analysis" in features:
        for file_data in all_results.values():
            sa = file_data.get("static_analysis", {})
            issues = sa.get("issues", [])
            linter_count += len(issues)
        rows.append(("Linter / Static Findings", str(linter_count)))

    return rows


def _prepare_context(all_results: dict, features: list[str]) -> str:
    """Build a compact context block from all results for LLM prompts.

    Truncates each file/feature block to _MAX_CONTEXT_PER_FILE chars to avoid
    token overflow.
    """
    parts: list[str] = []
    for file_path, file_data in all_results.items():
        file_parts: list[str] = [f"### {file_path}"]
        for feat in features:
            result = file_data.get(feat)
            if result is None:
                continue
            label = _FEATURE_LABELS.get(feat, feat)
            snippet = json.dumps(result, indent=2)
            if len(snippet) > _MAX_CONTEXT_PER_FILE:
                snippet = snippet[:_MAX_CONTEXT_PER_FILE] + "\n... [truncated]"
            file_parts.append(f"#### {label}\n```json\n{snippet}\n```")
        parts.append("\n\n".join(file_parts))
    return "\n\n---\n\n".join(parts)


def _call_llm(prompt: str) -> str:
    """Call Bedrock Claude via Strands Agent and return the text response."""
    model = make_bedrock_model()
    agent = Agent(model=model)
    result = agent(prompt)
    if hasattr(result, "message"):
        msg = result.message
        if isinstance(msg, dict):
            content = msg.get("content", [])
            if content and isinstance(content[0], dict):
                return content[0].get("text", str(result))
        return str(msg)
    return str(result)


# ---------------------------------------------------------------------------
# Mode builders
# ---------------------------------------------------------------------------


def _build_template(
    per_file_reports: list[str],
    all_results: dict,
    file_paths: list[str],
    features: list[str],
    language: str,
) -> str:
    """Assemble a template-only report: no LLM calls."""
    lines: list[str] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    feature_labels = [_FEATURE_LABELS.get(f, f) for f in features]

    # ---- Title + metadata ----
    lines.append("# Consolidated Analysis Report")
    lines.append("")
    lines.append(f"**Language:** {language.capitalize()}")
    lines.append(f"**Files Analyzed:** {len(file_paths)}")
    lines.append(f"**Features:** {', '.join(feature_labels) if feature_labels else 'N/A'}")
    lines.append(f"**Generated:** {timestamp}")
    lines.append("")

    # ---- Empty state ----
    if not file_paths:
        lines.append("No files were analyzed — no analysis data available.")
        return "\n".join(lines)

    # ---- Table of Contents ----
    lines.append("## Table of Contents")
    lines.append("")
    for fp in file_paths:
        basename = os.path.basename(fp)
        anchor = _slug(basename)
        lines.append(f"- [{basename}](#{anchor})")
    lines.append("")

    # ---- Summary Statistics ----
    lines.append("## Summary Statistics")
    lines.append("")
    stats = _compute_stats(all_results, features)
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for label, value in stats:
        lines.append(f"| {label} | {value} |")
    lines.append("")

    # ---- Per-file sections ----
    lines.append("## Per-File Analysis")
    lines.append("")

    for fp, report in zip(file_paths, per_file_reports):
        basename = os.path.basename(fp)
        anchor = _slug(basename)
        lines.append(f'<a id="{anchor}"></a>')
        lines.append("")
        # Strip top-level heading from per-file report to avoid duplication
        report_body = report
        report_lines = report.splitlines()
        if report_lines and report_lines[0].startswith("# "):
            report_body = "\n".join(report_lines[1:]).lstrip("\n")
        lines.append(f"## {fp}")
        lines.append("")
        lines.append(report_body)
        lines.append("")

    return "\n".join(lines)


def _build_llm(
    per_file_reports: list[str],
    all_results: dict,
    file_paths: list[str],
    features: list[str],
    language: str,
) -> str:
    """Send all results to LLM for a full synthesized narrative document."""
    context = _prepare_context(all_results, features)
    feature_labels = [_FEATURE_LABELS.get(f, f) for f in features]
    file_list = ", ".join(file_paths) if file_paths else "none"

    prompt = f"""You are a senior software engineering lead. Produce a comprehensive, cohesive
consolidated code analysis report in Markdown format for the following codebase.

**Language:** {language}
**Files:** {file_list}
**Features analysed:** {', '.join(feature_labels)}

Below are the structured analysis results for each file:

{context}

Write a thorough report that includes:
1. An executive summary of the overall codebase health
2. Key findings across all files (bugs, design issues, code flow patterns)
3. Cross-file patterns and recurring themes
4. Prioritised recommendations for the development team
5. A conclusion

Use clear Markdown headings, tables where appropriate, and keep the tone professional.
"""
    return _call_llm(prompt)


def _build_hybrid(
    per_file_reports: list[str],
    all_results: dict,
    file_paths: list[str],
    features: list[str],
    language: str,
) -> str:
    """Template skeleton with LLM-generated narrative sections."""
    lines: list[str] = []
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    feature_labels = [_FEATURE_LABELS.get(f, f) for f in features]
    context = _prepare_context(all_results, features)
    file_list = ", ".join(file_paths) if file_paths else "none"

    # ---- Title + metadata ----
    lines.append("# Consolidated Analysis Report")
    lines.append("")
    lines.append(f"**Language:** {language.capitalize()}")
    lines.append(f"**Files Analyzed:** {len(file_paths)}")
    lines.append(f"**Features:** {', '.join(feature_labels) if feature_labels else 'N/A'}")
    lines.append(f"**Generated:** {timestamp}")
    lines.append("")

    # ---- LLM: Executive Summary ----
    lines.append("## Executive Summary")
    lines.append("")
    exec_prompt = f"""You are a senior software engineering lead. Write a concise executive summary
(200-400 words) of the following code analysis results for a {language} codebase.
Files: {file_list}
Features: {', '.join(feature_labels)}

Analysis results:
{context}

Focus on the most critical findings, overall codebase health, and top priorities.
Write in plain prose (no sub-headings). Return only the summary text."""
    exec_summary = _call_llm(exec_prompt)
    lines.append(exec_summary)
    lines.append("")

    # ---- Template: Summary Statistics ----
    lines.append("## Summary Statistics")
    lines.append("")
    stats = _compute_stats(all_results, features)
    lines.append("| Metric | Value |")
    lines.append("|--------|-------|")
    for label, value in stats:
        lines.append(f"| {label} | {value} |")
    lines.append("")

    # ---- LLM: Architecture & Module Relationships ----
    lines.append("## Architecture & Module Relationships")
    lines.append("")
    arch_prompt = f"""Based on the following code analysis results for a {language} codebase,
write a concise analysis (200-300 words) of the architecture and module relationships.
Files: {file_list}

Analysis results:
{context}

Describe how the modules interact, the overall architecture pattern, and any structural concerns.
Write in plain prose. Return only the analysis text."""
    arch_text = _call_llm(arch_prompt)
    lines.append(arch_text)
    lines.append("")

    # ---- Template: Per-file sections ----
    if file_paths:
        lines.append("## Per-File Analysis")
        lines.append("")
        for fp, report in zip(file_paths, per_file_reports):
            report_body = report
            report_lines = report.splitlines()
            if report_lines and report_lines[0].startswith("# "):
                report_body = "\n".join(report_lines[1:]).lstrip("\n")
            lines.append(f"## {fp}")
            lines.append("")
            lines.append(report_body)
            lines.append("")

    # ---- LLM: Conclusion & Recommendations ----
    lines.append("## Conclusion & Recommendations")
    lines.append("")
    concl_prompt = f"""Based on the following code analysis results for a {language} codebase,
write a conclusion and prioritised recommendations (150-250 words).
Files: {file_list}

Analysis results:
{context}

Provide actionable, prioritised next steps for the development team.
Write in plain prose. Return only the conclusion and recommendations text."""
    concl_text = _call_llm(concl_prompt)
    lines.append(concl_text)
    lines.append("")

    return "\n".join(lines)
