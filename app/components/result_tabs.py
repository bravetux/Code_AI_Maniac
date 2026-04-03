import json
import streamlit as st

FEATURE_LABELS = {
    "bug_analysis": "Bug Analysis",
    "code_design": "Code Design",
    "code_flow": "Code Flow",
    "mermaid": "Mermaid Diagram",
    "requirement": "Requirements",
    "static_analysis": "Static Analysis",
    "comment_generator": "PR Comments",
    "commit_analysis": "Commit Analysis",
}


def render_results(results: dict) -> None:
    """Render analysis results as tabs, one per feature."""
    if not results:
        return

    features = [f for f in results if f != "error"]
    if not features:
        if "error" in results:
            st.error(f"Analysis failed: {results['error']}")
        return

    tabs = st.tabs([FEATURE_LABELS.get(f, f) for f in features])

    for tab, feature in zip(tabs, features):
        with tab:
            _render_feature_result(feature, results[feature])


def _render_feature_result(feature: str, result: dict) -> None:
    if "error" in result:
        st.error(result["error"])
        return

    col1, col2 = st.columns([4, 1])
    with col2:
        st.download_button("Download JSON", data=json.dumps(result, indent=2),
                           file_name=f"{feature}_result.json", mime="application/json",
                           key=f"json_{feature}")
        st.download_button("Download MD", data=_to_markdown(feature, result),
                           file_name=f"{feature}_result.md", mime="text/markdown",
                           key=f"md_{feature}")

    if feature == "bug_analysis":
        _render_bugs(result)
    elif feature == "code_design":
        st.markdown(result.get("markdown", json.dumps(result, indent=2)))
    elif feature == "code_flow":
        _render_flow(result)
    elif feature == "mermaid":
        from app.components.mermaid_renderer import render_mermaid
        render_mermaid(result.get("mermaid_source", ""))
        st.caption(result.get("description", ""))
    elif feature == "requirement":
        _render_requirements(result)
    elif feature == "static_analysis":
        _render_static(result)
    elif feature == "comment_generator":
        _render_comments(result)
    elif feature == "commit_analysis":
        _render_commits(result)


def _render_bugs(result: dict) -> None:
    bugs = result.get("bugs", [])
    st.caption(result.get("summary", ""))
    if not bugs:
        st.success("No bugs found.")
        return
    for bug in bugs:
        severity = bug.get("severity", "minor")
        color = {"critical": "🔴", "major": "🟠", "minor": "🟡"}.get(severity, "⚪")
        with st.expander(f"{color} Line {bug.get('line', '?')} — {bug.get('description', '')}"):
            st.write(f"**Severity:** {severity}")
            st.write(f"**Suggestion:** {bug.get('suggestion', '')}")
            st.code(bug.get("github_comment", ""), language="markdown")


def _render_flow(result: dict) -> None:
    st.caption(result.get("summary", ""))
    for step in result.get("steps", []):
        st.write(f"**Step {step['step']}:** {step['description']}")
        if step.get("calls"):
            st.write(f"  Calls: `{'`, `'.join(step['calls'])}`")


def _render_requirements(result: dict) -> None:
    st.caption(result.get("summary", ""))
    for req in result.get("requirements", []):
        st.write(f"**{req.get('id', '')}** ({req.get('component', '')}): {req.get('statement', '')}")


def _render_static(result: dict) -> None:
    st.caption(result.get("summary", ""))
    linter = result.get("linter_findings", [])
    semantic = result.get("semantic_findings", [])
    if linter:
        st.subheader("Linter Findings")
        for f in linter:
            st.write(f"Line {f.get('line')}: `{f.get('code')}` — {f.get('message')}")
    if semantic:
        st.subheader("Semantic Findings")
        for f in semantic:
            st.write(f"Line {f.get('line')}: [{f.get('category')}] {f.get('description')}")


def _render_comments(result: dict) -> None:
    st.caption(result.get("summary", ""))
    for comment in result.get("comments", []):
        with st.expander(f"Line {comment.get('line')} — {comment.get('severity', '')}"):
            st.code(comment.get("body", ""), language="markdown")


def _render_commits(result: dict) -> None:
    st.caption(result.get("summary", ""))
    ra = result.get("risk_assessment", {})
    risk_color = {"high": "🔴", "medium": "🟠", "low": "🟢"}.get(ra.get("level", "low"), "⚪")
    st.write(f"**Risk Level:** {risk_color} {ra.get('level', 'unknown')}")
    cl = result.get("changelog", {})
    if cl.get("added"):
        st.write("**Added:**", ", ".join(cl["added"]))
    if cl.get("changed"):
        st.write("**Changed:**", ", ".join(cl["changed"]))
    if cl.get("removed"):
        st.write("**Removed:**", ", ".join(cl["removed"]))


def _to_markdown(feature: str, result: dict) -> str:
    return f"# {FEATURE_LABELS.get(feature, feature)}\n\n```json\n{json.dumps(result, indent=2)}\n```"
