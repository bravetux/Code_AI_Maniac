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
import os
from datetime import datetime
import streamlit as st

FEATURE_LABELS = {
    "bug_analysis":      "Bug Analysis",
    "code_design":       "Code Design",
    "code_flow":         "Code Flow",
    "mermaid":           "Mermaid Diagram",
    "requirement":       "Requirements",
    "static_analysis":   "Static Analysis",
    "comment_generator": "PR Comments",
    "commit_analysis":     "Commit Analysis",
    "code_complexity":     "Code Complexity",
    "test_coverage":       "Test Coverage",
    "duplication_detection": "Duplication Detection",
    "performance_analysis":  "Performance Analysis",
    "type_safety":         "Type Safety",
    "architecture_mapper": "Architecture Mapper",
    "license_compliance":  "License Compliance",
    "change_impact":       "Change Impact",
    "refactoring_advisor": "Refactoring Advisor",
    "api_doc_generator":   "API Doc Generator",
    "doxygen":             "Doxygen Docs",
    "c_test_generator":    "C Test Generator",
    "release_notes":       "Release Notes",
    "developer_activity":  "Developer Activity",
    "commit_hygiene":      "Commit Hygiene",
    "churn_analysis":      "Churn Analysis",
    "secret_scan":         "Secret Scan",
    "dependency_analysis": "Dependency Analysis",
    "threat_model":        "Threat Model",
}

_SEVERITY_ICON = {"critical": "🔴", "major": "🟠", "minor": "🟡", "suggestion": "🔵"}
_RISK_ICON     = {"high": "🔴", "medium": "🟠", "low": "🟢"}

# Security features are rendered by security_results.py, not here
_SECURITY_FEATURES = {"secret_scan", "dependency_analysis", "threat_model"}

_FEATURE_SUFFIX = {
    "bug_analysis":      "_bug_analysis.md",
    "code_design":       "_code_design.md",
    "code_flow":         "_code_flow.md",
    "mermaid":           "_mermaid.md",
    "requirement":       "_requirement.md",
    "static_analysis":   "_static_analysis.md",
    "comment_generator": "_pr_comments.md",
    "commit_analysis":      "_commit_analysis.md",
    "code_complexity":      "_code_complexity.md",
    "test_coverage":        "_test_coverage.md",
    "duplication_detection": "_duplication_detection.md",
    "performance_analysis": "_performance_analysis.md",
    "type_safety":          "_type_safety.md",
    "architecture_mapper":  "_architecture_mapper.md",
    "license_compliance":   "_license_compliance.md",
    "change_impact":        "_change_impact.md",
    "refactoring_advisor":  "_refactoring_advisor.md",
    "api_doc_generator":    "_api_doc_generator.md",
    "doxygen":              "_doxygen.md",
    "c_test_generator":     "_c_test_generator.md",
    "release_notes":        "_release_notes.md",
    "developer_activity":   "_developer_activity.md",
    "commit_hygiene":       "_commit_hygiene.md",
    "churn_analysis":       "_churn_analysis.md",
    "secret_scan":          "_secret_scan.md",
    "dependency_analysis":  "_dependency_analysis.md",
    "threat_model":         "_threat_model.md",
}


def render_results(results: dict, source_ref: str = "") -> None:
    if not results:
        st.info("No results to display.")
        return

    features = [f for f in FEATURE_LABELS if f in results and f not in _SECURITY_FEATURES]
    if not features:
        if "error" in results:
            st.error(f"Analysis error: {results['error']}")
        return

    # ── Save All Reports button ───────────────────────────────────────────────
    col_save, col_msg = st.columns([2, 8])
    with col_save:
        if st.button("💾 Save All Reports", key="save_all_reports_btn",
                     help="Save all tab reports as .md files to the Reports/ folder"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            reports_dir = os.path.join("Reports", ts)
            written = _save_all_reports(results, reports_dir, source_ref)
            with col_msg:
                st.success(
                    f"Saved **{len(written)}** report(s) to `{reports_dir}/`"
                )

    tabs = st.tabs([FEATURE_LABELS[f] for f in features])
    for tab, feature in zip(tabs, features):
        with tab:
            _render_feature(feature, results[feature])


# ── Per-feature dispatcher ────────────────────────────────────────────────────

def _render_feature(feature: str, result: dict) -> None:
    if not isinstance(result, dict):
        st.json(result)
        return

    if "error" in result:
        st.error(result["error"])
        _download_row(feature, result)
        return

    md_label = "⬇ Design Doc" if feature == "code_design" else "⬇ MD"
    _download_row(feature, result, md_label=md_label)

    # Multi-file: show per-file expanders
    if result.get("_multi_file"):
        _render_multi_file(feature, result)
        return

    _render_single(feature, result)


def _render_multi_file(feature: str, result: dict) -> None:
    files = result.get("files", {})
    summary = result.get("summary", "")
    if summary:
        st.caption(summary)
    for file_path, file_result in files.items():
        label = file_path if len(file_path) <= 80 else "..." + file_path[-77:]
        with st.expander(f"📄 {label}", expanded=False):
            if "error" in file_result:
                st.error(file_result["error"])
            else:
                _render_single(feature, file_result)


def _render_single(feature: str, result: dict) -> None:
    if feature == "bug_analysis":
        _render_bugs(result, language=result.get("language", ""))
    elif feature == "code_design":
        _render_code_design(result)
    elif feature == "code_flow":
        _render_code_flow(result)
    elif feature == "mermaid":
        _render_mermaid(result)
    elif feature == "requirement":
        _render_requirements(result)
    elif feature == "static_analysis":
        _render_static(result)
    elif feature == "comment_generator":
        _render_comments(result)
    elif feature == "commit_analysis":
        _render_commits(result)
    elif feature in ("code_complexity", "test_coverage", "duplication_detection",
                     "performance_analysis", "type_safety", "architecture_mapper",
                     "license_compliance", "change_impact", "refactoring_advisor",
                     "api_doc_generator", "doxygen", "c_test_generator",
                     "release_notes",
                     "developer_activity", "commit_hygiene", "churn_analysis"):
        _render_markdown_agent(result)
    else:
        st.json(result)


# ── Download buttons ──────────────────────────────────────────────────────────

def _download_row(feature: str, result: dict, md_label: str = "⬇ MD") -> None:
    json_bytes = json.dumps(result, indent=2, ensure_ascii=False)
    md_bytes   = _to_markdown(feature, result)
    c1, c2, _ = st.columns([1, 1, 6])
    c1.download_button(
        "⬇ JSON", data=json_bytes,
        file_name=f"{feature}_result.json", mime="application/json",
        key=f"dl_json_{feature}",
    )
    c2.download_button(
        md_label, data=md_bytes,
        file_name=f"{feature}_result.md", mime="text/markdown",
        key=f"dl_md_{feature}",
    )
    st.divider()


# ── Bug Analysis ──────────────────────────────────────────────────────────────

def _normalize_severity(raw: str) -> str:
    """Map variant severity labels back to critical / major / minor."""
    _MAP = {
        "critical": "critical", "high": "critical", "error": "critical",
        "major": "major", "medium": "major", "warning": "major",
        "minor": "minor", "low": "minor", "info": "minor",
        "suggestion": "minor", "note": "minor", "trivial": "minor",
    }
    return _MAP.get((raw or "").strip().lower(), "minor")


def _clean_narrative(text: str) -> str:
    """Strip embedded JSON from narrative text that the LLM sometimes includes."""
    if not text:
        return text
    # Find where JSON blob starts and remove everything from there
    brace_pos = text.find("{")
    if brace_pos > 0:
        # Only strip if there's meaningful text before the JSON
        before = text[:brace_pos].strip()
        if before:
            return before
    elif brace_pos == 0:
        # Entire text is JSON — not a narrative
        return ""
    return text


def _render_bugs(result: dict, language: str = "") -> None:
    bugs = result.get("bugs", [])
    narrative = _clean_narrative(result.get("narrative", ""))
    summary = result.get("summary", "")
    lang = (language or "python").lower()

    # Narrative first — establishes context before counts or bug list
    if narrative:
        with st.container(border=True):
            st.markdown("**Overall assessment**")
            st.markdown(narrative)

    if not bugs:
        # Only show "no bugs" banner when there is no narrative that may say otherwise
        if not narrative:
            st.success("No bugs found.")
        return

    # Normalise severity so template-driven variants (high/medium/low) map correctly
    for bug in bugs:
        bug["severity"] = _normalize_severity(bug.get("severity", ""))

    # Summary count as a quiet caption above the grouped bug list
    if summary:
        st.caption(summary)

    critical = [b for b in bugs if b.get("severity") == "critical"]
    major    = [b for b in bugs if b.get("severity") == "major"]
    minor    = [b for b in bugs if b.get("severity") == "minor"]

    for group, label in [(critical, "Critical"), (major, "Major"), (minor, "Minor")]:
        if not group:
            continue
        st.subheader(f"{_SEVERITY_ICON.get(label.lower(), '⚪')} {label} ({len(group)})")
        for bug in group:
            line = bug.get("line", "?")
            desc = bug.get("description", bug.get("message", ""))
            with st.expander(f"Line {line} — {desc[:80]}"):
                st.markdown(desc)
                if bug.get("runtime_impact"):
                    st.markdown(f"**Runtime impact:** {bug['runtime_impact']}")
                if bug.get("root_cause"):
                    st.markdown(f"**Root cause:** {bug['root_cause']}")
                if bug.get("suggestion"):
                    st.markdown(f"**Fix:** {bug['suggestion']}")

                st.divider()
                col_orig, col_fix = st.columns(2)
                original = bug.get("original_snippet", "")
                fixed = bug.get("fixed_snippet", "")
                with col_orig:
                    st.markdown("**Original Code**")
                    if original:
                        st.code(original, language=lang, line_numbers=True)
                    else:
                        st.caption("Re-run analysis to generate snippet.")
                with col_fix:
                    st.markdown("**Fixed Code**")
                    if fixed:
                        st.code(fixed, language=lang, line_numbers=True)
                    else:
                        st.caption("No fix snippet provided.")

                if bug.get("github_comment"):
                    st.markdown("**GitHub PR comment**")
                    st.code(bug["github_comment"], language="markdown")


# ── Code Design ───────────────────────────────────────────────────────────────

def _render_code_design(result: dict) -> None:
    _PRIORITY_ICON = {"high": "🔴", "medium": "🟠", "low": "🟡"}

    # ── Primary: full design document rendered immediately ────────────────────
    doc = result.get("design_document") or result.get("markdown", "")
    if doc:
        st.markdown(doc)
    else:
        # Fallback for old cached results that only have structured fields
        if result.get("purpose"):
            st.info(result["purpose"])

    st.divider()

    # ── Supporting: structured analysis in a collapsed expander ──────────────
    design_issues = result.get("design_issues", [])
    improvements  = result.get("improvements", [])
    public_api    = result.get("public_api", [])
    has_detail    = bool(design_issues or improvements or public_api
                        or result.get("design_assessment")
                        or result.get("dependencies")
                        or result.get("data_contracts"))

    if has_detail:
        with st.expander(f"Analysis detail ({len(design_issues)} issue(s) found)", expanded=False):
            if result.get("design_assessment"):
                with st.container(border=True):
                    st.markdown(f"**Overall assessment:** {result['design_assessment']}")

            if design_issues:
                st.subheader(f"Design issues ({len(design_issues)})")
                for issue in design_issues:
                    icon = _PRIORITY_ICON.get(issue.get("priority", "low"), "⚪")
                    with st.expander(f"{icon} {issue.get('issue', '')}"):
                        if issue.get("root_cause"):
                            st.markdown(f"**Root cause:** {issue['root_cause']}")
                        if issue.get("impact"):
                            st.markdown(f"**Impact:** {issue['impact']}")
                        if issue.get("recommendation"):
                            st.markdown(f"**Recommendation:** {issue['recommendation']}")

            if improvements:
                st.subheader("Improvement roadmap")
                for i, imp in enumerate(improvements, 1):
                    st.markdown(f"{i}. {imp}")

            if public_api:
                st.subheader("Public API")
                for api in public_api:
                    with st.expander(f"`{api.get('name', '')}` — {api.get('signature', '')}"):
                        st.markdown(api.get("description", ""))

            if result.get("dependencies"):
                st.subheader("Dependencies")
                st.markdown(", ".join(f"`{d}`" for d in result["dependencies"]))

            if result.get("data_contracts"):
                st.subheader("Data contracts")
                st.markdown(result["data_contracts"])


# ── Code Flow ─────────────────────────────────────────────────────────────────

def _render_code_flow(result: dict) -> None:
    if result.get("markdown"):
        st.markdown(result["markdown"])
    else:
        if result.get("summary"):
            st.info(result["summary"])
        entry_points = result.get("entry_points", [])
        if entry_points:
            st.markdown("**Entry points:** " + ", ".join(f"`{e}`" for e in entry_points))
        for step in result.get("steps", []):
            cols = st.columns([0.5, 7, 2.5])
            cols[0].markdown(f"**{step.get('step', '')}**")
            cols[1].markdown(step.get("description", ""))
            calls = step.get("calls", [])
            if calls:
                cols[2].markdown(", ".join(f"`{c}`" for c in calls))


# ── Mermaid Diagram ───────────────────────────────────────────────────────────

def _render_mermaid(result: dict) -> None:
    src = result.get("mermaid_source", "")
    desc = result.get("description", "")
    diagram_type = result.get("diagram_type", "")

    if diagram_type:
        st.caption(f"Diagram type: `{diagram_type}`")

    if not src:
        st.warning("No diagram source returned by the agent.")
        return

    from app.components.mermaid_renderer import render_mermaid
    render_mermaid(src)

    # Description sits below the source, not above the iframe gap
    if desc:
        st.caption(desc)


# ── Requirements ──────────────────────────────────────────────────────────────

def _render_requirements(result: dict) -> None:
    if result.get("markdown"):
        st.markdown(result["markdown"])
    else:
        if result.get("summary"):
            st.info(result["summary"])
        for req in result.get("requirements", []):
            rid  = req.get("id", "")
            comp = req.get("component", "")
            stmt = req.get("statement", "")
            lines = req.get("source_lines", [])
            label = f"**{rid}**" + (f" `{comp}`" if comp else "")
            with st.expander(f"{rid} — {stmt[:80]}"):
                st.markdown(f"{label}: {stmt}")
                if lines:
                    st.caption(f"Source lines: {lines}")


# ── Static Analysis ───────────────────────────────────────────────────────────

def _render_static(result: dict) -> None:
    if result.get("summary"):
        st.info(result["summary"])

    narrative = _clean_narrative(result.get("narrative", ""))
    if narrative:
        with st.container(border=True):
            st.markdown("**Overall assessment**")
            st.markdown(narrative)

    linter   = result.get("linter_findings", [])
    semantic = result.get("semantic_findings", [])

    if not linter and not semantic:
        st.success("No issues found.")
        return

    if linter:
        st.subheader(f"Linter findings ({len(linter)})")
        for f in linter:
            icon = _SEVERITY_ICON.get(f.get("severity", "minor"), "⚪")
            line = f.get("line", "?")
            code = f.get("code", "")
            msg  = f.get("message", "")
            st.markdown(f"{icon} **Line {line}** `{code}` — {msg}")

    if semantic:
        st.subheader(f"Semantic findings ({len(semantic)})")
        for f in semantic:
            icon = _SEVERITY_ICON.get(f.get("severity", "minor"), "⚪")
            line = f.get("line", "?")
            cat  = f.get("category", "")
            desc = f.get("description", "")
            sug  = f.get("suggestion", "")
            with st.expander(f"{icon} Line {line} [{cat}] — {desc[:80]}"):
                st.markdown(desc)
                if sug:
                    st.markdown(f"**Suggestion:** {sug}")


# ── PR Comment Generator ──────────────────────────────────────────────────────

def _render_comments(result: dict) -> None:
    summary  = result.get("summary", "")
    comments = result.get("comments", [])

    if summary:
        with st.container(border=True):
            st.markdown("**PR Summary**")
            st.markdown(summary)

    if not comments:
        st.caption("No inline comments generated.")
        return

    st.subheader(f"Inline comments ({len(comments)})")
    for c in comments:
        icon = _SEVERITY_ICON.get(c.get("severity", "suggestion"), "🔵")
        file_ = c.get("file", "")
        line  = c.get("line", "?")
        body  = c.get("body", "")
        sev   = c.get("severity", "")
        with st.expander(f"{icon} {file_} : line {line} — {sev}"):
            st.markdown(body)


# ── Commit Analysis ───────────────────────────────────────────────────────────

def _render_commits(result: dict) -> None:
    if result.get("markdown"):
        risk = result.get("risk_level", "")
        if risk:
            icon = _RISK_ICON.get(risk, "⚪")
            st.metric("Risk Level", f"{icon} {risk.title()}")
        st.markdown(result["markdown"])
    else:
        summary = result.get("summary", "")
        if summary:
            st.info(summary)
        ra   = result.get("risk_assessment", {})
        risk = ra.get("level", "low")
        icon = _RISK_ICON.get(risk, "⚪")
        st.metric("Risk Level", f"{icon} {risk.title()}")
        concerns = ra.get("concerns", [])
        if concerns:
            with st.expander("Risk concerns"):
                for c in concerns:
                    st.markdown(f"- {c}")
        cl = result.get("changelog", {})
        for section, label in [("added", "Added"), ("changed", "Changed"), ("removed", "Removed")]:
            for item in cl.get(section, []):
                st.markdown(f"- [{label}] {item}")
        quality = result.get("commit_quality", [])
        if quality:
            st.subheader(f"Commit quality ({len(quality)} commits)")
            _QUALITY_ICON = {"good": "✅", "needs-improvement": "⚠️", "poor": "❌"}
            for q in quality:
                qicon  = _QUALITY_ICON.get(q.get("quality", ""), "❔")
                sha    = q.get("sha", "")
                msg    = q.get("message", "")
                reason = q.get("reason", "")
                with st.expander(f"{qicon} `{sha}` — {msg[:60]}"):
                    if reason:
                        st.markdown(f"**Reason:** {reason}")


def _render_markdown_agent(result: dict) -> None:
    """Generic renderer for agents that return markdown as their primary output."""
    if result.get("markdown"):
        st.markdown(result["markdown"])
    else:
        summary = result.get("summary", "")
        if summary:
            st.info(summary)


# ── Bulk save to Reports/ folder ─────────────────────────────────────────────

def _source_basename(source_ref: str) -> str:
    """Extract a usable base filename from a source_ref string."""
    if not source_ref:
        return "report"
    # GitHub/Gitea: owner/repo::branch::path/to/file.py → file.py
    # Local single: /path/to/file.py → file.py
    last = source_ref.split("::")[-1]
    name = os.path.basename(last)
    return name if name else "report"


def save_reports_to_disk(results: dict, source_ref: str = "",
                         reports_root: str = "Reports") -> list[str]:
    """
    Write one Markdown report per (source file x feature) into a timestamped
    sub-directory of reports_root.  Standalone — no Streamlit dependency.
    Returns list of written file paths.

    Note: This is the legacy per-feature save used by the manual "Save All
    Reports" button.  The orchestrator now uses _generate_reports() for
    per-file and consolidated reports.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    reports_dir = os.path.join(reports_root, ts)
    os.makedirs(reports_dir, exist_ok=True)
    written = []

    for feature in FEATURE_LABELS:
        if feature not in results:
            continue
        result = results[feature]
        suffix = _FEATURE_SUFFIX.get(feature, f"_{feature}.md")

        if result.get("_multi_file"):
            for file_path, file_result in result.get("files", {}).items():
                base = os.path.basename(file_path) or "report"
                out_path = os.path.join(reports_dir, f"{base}{suffix}")
                try:
                    content = _to_markdown(feature, file_result)
                    with open(out_path, "w", encoding="utf-8") as fh:
                        fh.write(content)
                    written.append(out_path)
                except Exception:
                    pass
        else:
            base = _source_basename(source_ref)
            out_path = os.path.join(reports_dir, f"{base}{suffix}")
            try:
                content = _to_markdown(feature, result)
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                written.append(out_path)
            except Exception:
                pass

    return written


def _save_all_reports(results: dict, reports_dir: str, source_ref: str = "") -> list[str]:
    """
    Write one Markdown report per (source file × feature) into reports_dir.
    Returns list of written file paths.
    """
    os.makedirs(reports_dir, exist_ok=True)
    written = []

    for feature in FEATURE_LABELS:
        if feature not in results:
            continue
        result = results[feature]
        suffix = _FEATURE_SUFFIX.get(feature, f"_{feature}.md")

        if result.get("_multi_file"):
            # One .md per source file
            for file_path, file_result in result.get("files", {}).items():
                base = os.path.basename(file_path) or "report"
                out_path = os.path.join(reports_dir, f"{base}{suffix}")
                try:
                    content = _to_markdown(feature, file_result)
                    with open(out_path, "w", encoding="utf-8") as fh:
                        fh.write(content)
                    written.append(out_path)
                except Exception as exc:
                    st.warning(f"Could not write {out_path}: {exc}")
        else:
            # Single file — derive name from source_ref
            base = _source_basename(source_ref)
            out_path = os.path.join(reports_dir, f"{base}{suffix}")
            try:
                content = _to_markdown(feature, result)
                with open(out_path, "w", encoding="utf-8") as fh:
                    fh.write(content)
                written.append(out_path)
            except Exception as exc:
                st.warning(f"Could not write {out_path}: {exc}")

    return written


# ── Markdown export ───────────────────────────────────────────────────────────

def _to_markdown(feature: str, result: dict) -> str:
    label = FEATURE_LABELS.get(feature, feature)
    lines = [f"# {label}", ""]

    if feature == "bug_analysis":
        lines.append(result.get("summary", ""))
        for bug in result.get("bugs", []):
            lines += [
                f"## Line {bug.get('line', '?')} — {bug.get('severity', '')}",
                bug.get("description", bug.get("message", "")),
                f"**Suggestion:** {bug.get('suggestion', '')}",
                "",
            ]
    elif feature == "code_design":
        lines.append(
            result.get("design_document") or result.get("markdown") or json.dumps(result, indent=2)
        )
    elif feature == "code_flow":
        lines.append(result.get("summary", ""))
        for step in result.get("steps", []):
            lines.append(f"{step.get('step')}. {step.get('description', '')}")
    elif feature == "mermaid":
        lines += ["```mermaid", result.get("mermaid_source", ""), "```"]
    elif feature == "requirement":
        lines.append(result.get("summary", ""))
        for req in result.get("requirements", []):
            lines.append(f"- **{req.get('id')}**: {req.get('statement', '')}")
    elif feature == "static_analysis":
        lines.append(result.get("summary", ""))
        for f in result.get("linter_findings", []):
            lines.append(f"- Line {f.get('line')}: `{f.get('code')}` {f.get('message')}")
        for f in result.get("semantic_findings", []):
            lines.append(f"- Line {f.get('line')} [{f.get('category')}]: {f.get('description')}")
    elif feature == "comment_generator":
        lines.append(result.get("summary", ""))
        for c in result.get("comments", []):
            lines += [f"### {c.get('file')} : line {c.get('line')}", c.get("body", ""), ""]
    elif feature == "commit_analysis":
        lines.append(result.get("summary", ""))
        ra = result.get("risk_assessment", {})
        lines.append(f"**Risk:** {ra.get('level', '')}")
        cl = result.get("changelog", {})
        for k in ("added", "changed", "removed"):
            for item in cl.get(k, []):
                lines.append(f"- [{k}] {item}")
    elif feature in ("release_notes", "developer_activity", "commit_hygiene", "churn_analysis",
                     "code_complexity", "test_coverage", "duplication_detection",
                     "performance_analysis", "type_safety", "architecture_mapper",
                     "license_compliance", "change_impact", "refactoring_advisor",
                     "api_doc_generator", "doxygen", "c_test_generator"):
        lines.append(result.get("markdown") or result.get("summary") or json.dumps(result, indent=2))
    else:
        lines.append(f"```json\n{json.dumps(result, indent=2)}\n```")

    return "\n".join(lines)
