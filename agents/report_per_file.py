"""Per-file report agent — assembles all selected feature results for one source
file into a single structured Markdown document.  No LLM calls."""

import os
from datetime import datetime

# Canonical section order — matches the reading flow in the design spec.
_SECTION_ORDER = [
    "requirement",
    "code_flow",
    "code_design",
    "bug_analysis",
    "static_analysis",
    "mermaid",
    "comment_generator",
]

_SECTION_TITLE = {
    "requirement":       "Requirements",
    "code_flow":         "Code Flow",
    "code_design":       "Code Design",
    "bug_analysis":      "Bug Analysis",
    "static_analysis":   "Static Analysis",
    "mermaid":           "Mermaid Diagram",
    "comment_generator": "PR Comments",
}


def generate_per_file_report(file_path: str, feature_results: dict,
                              language: str = "") -> str:
    """Return a Markdown string combining all feature results for *file_path*."""
    basename = os.path.basename(file_path) or file_path
    lines: list[str] = []

    # Header
    lines.append(f"# Analysis Report — {basename}")
    lines.append("")
    lines.append(f"**File:** `{file_path}`  ")
    lines.append(f"**Language:** {language or 'unknown'}  ")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Sections in canonical order
    rendered = 0
    for feature in _SECTION_ORDER:
        if feature not in feature_results:
            continue
        result = feature_results[feature]
        if not isinstance(result, dict) or "error" in result:
            continue
        title = _SECTION_TITLE.get(feature, feature)
        lines.append(f"## {title}")
        lines.append("")
        lines.append(_render_section(feature, result))
        lines.append("")
        rendered += 1

    if rendered == 0:
        lines.append("*No analysis features were run for this file.*")
        lines.append("")

    return "\n".join(lines)


def _render_section(feature: str, result: dict) -> str:
    """Render a single feature's result as Markdown."""
    if feature == "bug_analysis":
        return _render_bugs(result)
    if feature == "code_design":
        return _render_code_design(result)
    if feature == "code_flow":
        return _render_code_flow(result)
    if feature == "mermaid":
        return _render_mermaid(result)
    if feature == "requirement":
        return _render_requirement(result)
    if feature == "static_analysis":
        return _render_static(result)
    if feature == "comment_generator":
        return _render_comments(result)
    return ""


def _render_bugs(r: dict) -> str:
    parts = []
    if r.get("narrative"):
        parts.append(r["narrative"])
        parts.append("")
    if r.get("summary"):
        parts.append(f"*{r['summary']}*")
        parts.append("")
    for bug in r.get("bugs", []):
        sev = bug.get("severity", "unknown")
        line = bug.get("line", "?")
        desc = bug.get("description", bug.get("message", ""))
        parts.append(f"### Line {line} ({sev})")
        parts.append("")
        parts.append(desc)
        if bug.get("suggestion"):
            parts.append(f"\n**Suggestion:** {bug['suggestion']}")
        if bug.get("original_snippet"):
            parts.append(f"\n```\n{bug['original_snippet']}\n```")
        if bug.get("fixed_snippet"):
            parts.append(f"\n**Fixed:**\n```\n{bug['fixed_snippet']}\n```")
        parts.append("")
    return "\n".join(parts)


def _render_code_design(r: dict) -> str:
    doc = r.get("design_document") or r.get("markdown", "")
    if doc:
        return doc
    parts = []
    if r.get("purpose"):
        parts.append(r["purpose"])
    if r.get("design_assessment"):
        parts.append(f"\n**Assessment:** {r['design_assessment']}")
    return "\n".join(parts) if parts else "*No design document generated.*"


def _render_code_flow(r: dict) -> str:
    if r.get("markdown"):
        return r["markdown"]
    parts = []
    if r.get("summary"):
        parts.append(r["summary"])
    for step in r.get("steps", []):
        parts.append(f"{step.get('step', '')}. {step.get('description', '')}")
    return "\n".join(parts) if parts else "*No code flow data.*"


def _render_mermaid(r: dict) -> str:
    parts = []
    if r.get("description"):
        parts.append(r["description"])
        parts.append("")
    src = r.get("mermaid_source", "")
    if src:
        parts.append(f"```mermaid\n{src}\n```")
    return "\n".join(parts) if parts else "*No diagram generated.*"


def _render_requirement(r: dict) -> str:
    if r.get("markdown"):
        return r["markdown"]
    parts = []
    if r.get("summary"):
        parts.append(r["summary"])
        parts.append("")
    for req in r.get("requirements", []):
        parts.append(f"- **{req.get('id', '')}**: {req.get('statement', '')}")
    return "\n".join(parts) if parts else "*No requirements extracted.*"


def _render_static(r: dict) -> str:
    parts = []
    if r.get("narrative"):
        parts.append(r["narrative"])
        parts.append("")
    linter = r.get("linter_findings", [])
    semantic = r.get("semantic_findings", [])
    if linter:
        parts.append("### Linter Findings")
        parts.append("")
        for f in linter:
            parts.append(f"- **Line {f.get('line', '?')}** `{f.get('code', '')}` — {f.get('message', '')}")
        parts.append("")
    if semantic:
        parts.append("### Semantic Findings")
        parts.append("")
        for f in semantic:
            parts.append(f"- **Line {f.get('line', '?')}** [{f.get('category', '')}]: {f.get('description', '')}")
            if f.get("suggestion"):
                parts.append(f"  - *Suggestion:* {f['suggestion']}")
        parts.append("")
    return "\n".join(parts) if parts else "*No static analysis findings.*"


def _render_comments(r: dict) -> str:
    parts = []
    if r.get("summary"):
        parts.append(r["summary"])
        parts.append("")
    for c in r.get("comments", []):
        parts.append(f"### {c.get('file', '')} : line {c.get('line', '?')} ({c.get('severity', '')})")
        parts.append("")
        parts.append(c.get("body", ""))
        parts.append("")
    return "\n".join(parts) if parts else "*No PR comments generated.*"
