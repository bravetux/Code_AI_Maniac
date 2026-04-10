import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import json
import streamlit as st
import pandas as pd
from db.connection import get_connection
from db.queries.history import list_history, get_history_with_results

st.set_page_config(page_title="History — AI Code Maniac", layout="wide")
st.title("Analysis History")

conn = get_connection()
history = list_history(conn, limit=200)

if not history:
    st.info("No analyses run yet. Go to the Analysis page to get started.")
    st.stop()

df = pd.DataFrame(history)
df["created_at"] = pd.to_datetime(df["created_at"])

# ── Filters ──────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
feature_filter = col1.selectbox("Feature", ["All"] + sorted(df["feature"].unique().tolist()))
lang_filter = col2.selectbox("Language", ["All"] + sorted(df["language"].dropna().unique().tolist()))

filtered = df.copy()
if feature_filter != "All":
    filtered = filtered[filtered["feature"] == feature_filter]
if lang_filter != "All":
    filtered = filtered[filtered["language"] == lang_filter]

if filtered.empty:
    st.info("No matching results.")
    st.stop()

# ── Selectable history table ─────────────────────────────────────────────────
st.subheader("Select analyses to compare (up to 5)")

display = filtered[["id", "created_at", "feature", "language", "source_ref", "summary"]].copy()
display = display.reset_index(drop=True)
display.insert(0, "Select", False)

edited = st.data_editor(
    display,
    column_config={
        "Select": st.column_config.CheckboxColumn("Select", default=False),
        "id": None,
        "created_at": st.column_config.DatetimeColumn("Date", format="YYYY-MM-DD HH:mm"),
        "feature": "Feature",
        "language": "Language",
        "source_ref": "Source",
        "summary": "Summary",
    },
    disabled=["id", "created_at", "feature", "language", "source_ref", "summary"],
    hide_index=True,
    use_container_width=True,
    key="history_selector",
)

selected_rows = edited[edited["Select"] == True]  # noqa: E712
selected_ids = selected_rows["id"].tolist()

if len(selected_ids) > 5:
    st.warning("You can compare up to **5** analyses at a time. Please deselect some rows.")
    st.stop()

if len(selected_ids) < 2:
    st.caption("Select 2–5 rows above to enable comparison.")

# ── Compare buttons ──────────────────────────────────────────────────────────
btn_col1, btn_col2, _ = st.columns([2, 2, 6])
can_compare = 2 <= len(selected_ids) <= 5

with btn_col1:
    client_clicked = st.button(
        f"Compare — Client-side ({len(selected_ids)})",
        type="secondary",
        disabled=not can_compare,
        help="Instant metric extraction — no LLM call, compares counts and scores",
    )

with btn_col2:
    ai_clicked = st.button(
        f"Compare — AI Analysis ({len(selected_ids)})",
        type="primary",
        disabled=not can_compare,
        help="Uses a Strands agent (Bedrock/Claude) for intelligent comparison",
    )

if not client_clicked and not ai_clicked:
    st.stop()

# ── Load data (shared by both modes) ─────────────────────────────────────────
st.divider()

rows = get_history_with_results(conn, selected_ids)
if not rows:
    st.error("Could not load results for the selected analyses.")
    st.stop()

for row in rows:
    rj = row.get("result_json")
    if isinstance(rj, str):
        try:
            row["result_json"] = json.loads(rj)
        except Exception:
            row["result_json"] = {}
    elif rj is None:
        row["result_json"] = {}

# Build column labels
col_labels = []
for i, row in enumerate(rows, 1):
    ts = pd.to_datetime(row["created_at"]).strftime("%m/%d %H:%M")
    src = os.path.basename(row["source_ref"].split("::")[-1]) if row["source_ref"] else "?"
    col_labels.append(f"#{i} {src} ({ts})")

# ── Overview table (shown for both modes) ────────────────────────────────────
st.subheader("Comparison Results")
st.markdown("#### Overview")
overview_data = {
    "Property": ["Source", "Feature", "Language", "Date", "Summary"],
}
for i, row in enumerate(rows):
    overview_data[col_labels[i]] = [
        row["source_ref"],
        row["feature"],
        row["language"] or "auto",
        pd.to_datetime(row["created_at"]).strftime("%Y-%m-%d %H:%M:%S"),
        row["summary"],
    ]
st.dataframe(pd.DataFrame(overview_data), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# CLIENT-SIDE COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
if client_clicked:
    _FEATURE_KEY_MAP = {
        "Bug Analysis": "bug_analysis",
        "Code Design": "code_design",
        "Code Flow": "code_flow",
        "Mermaid Diagram": "mermaid",
        "Requirements": "requirement",
        "Static Analysis": "static_analysis",
        "PR Comments": "comment_generator",
        "Commit Analysis": "commit_analysis",
    }

    def _extract_single_metrics(feature_key: str, data: dict) -> dict:
        if not isinstance(data, dict):
            return {"Status": "OK"}
        metrics = {}

        if feature_key == "bug_analysis":
            bugs = data.get("bugs", [])
            metrics["Total bugs"] = len(bugs)
            for sev in ("critical", "major", "minor"):
                count = sum(1 for b in bugs if (b.get("severity", "") or "").lower() == sev)
                if count:
                    metrics[f"{sev.title()} bugs"] = count

        elif feature_key == "static_analysis":
            linter = data.get("linter_findings", [])
            semantic = data.get("semantic_findings", [])
            metrics["Linter issues"] = len(linter)
            metrics["Semantic issues"] = len(semantic)
            metrics["Total issues"] = len(linter) + len(semantic)

        elif feature_key == "code_design":
            metrics["Design issues"] = len(data.get("design_issues", []))
            metrics["Improvements"] = len(data.get("improvements", []))
            metrics["Public APIs"] = len(data.get("public_api", []))

        elif feature_key == "requirement":
            metrics["Requirements"] = len(data.get("requirements", []))

        elif feature_key == "comment_generator":
            comments = data.get("comments", [])
            metrics["PR comments"] = len(comments)
            for sev in ("critical", "major", "minor", "suggestion"):
                count = sum(1 for c in comments if (c.get("severity", "") or "").lower() == sev)
                if count:
                    metrics[f"{sev.title()} comments"] = count

        elif feature_key == "commit_analysis":
            ra = data.get("risk_assessment", {})
            metrics["Risk level"] = ra.get("level", data.get("risk_level", "N/A"))
            metrics["Concerns"] = len(ra.get("concerns", []))
            cl = data.get("changelog", {})
            metrics["Added"] = len(cl.get("added", []))
            metrics["Changed"] = len(cl.get("changed", []))
            metrics["Removed"] = len(cl.get("removed", []))

        elif feature_key == "code_flow":
            metrics["Flow steps"] = len(data.get("steps", []))
            metrics["Entry points"] = len(data.get("entry_points", []))

        elif feature_key == "mermaid":
            metrics["Diagram type"] = data.get("diagram_type", "N/A")
            src = data.get("mermaid_source", "")
            metrics["Diagram lines"] = len(src.strip().splitlines()) if src else 0

        if data.get("summary"):
            metrics["Summary"] = data["summary"]

        return metrics if metrics else {"Status": "OK"}

    def _extract_metrics(result_json: dict, feature_key: str) -> dict:
        data = result_json.get(feature_key, {})
        if not data:
            return {"Status": "No data"}
        if isinstance(data, dict) and data.get("error"):
            return {"Status": f"Error: {data['error'][:80]}"}
        if isinstance(data, dict) and data.get("_multi_file"):
            files = data.get("files", {})
            agg = {"Files analysed": len(files)}
            for fpath, fres in files.items():
                sub = _extract_single_metrics(feature_key, fres)
                for k, v in sub.items():
                    if isinstance(v, (int, float)):
                        agg[k] = agg.get(k, 0) + v
                    elif k not in agg:
                        agg[k] = v
            return agg
        return _extract_single_metrics(feature_key, data)

    # Collect all feature keys across selected rows
    all_feature_keys = set()
    for row in rows:
        fk = _FEATURE_KEY_MAP.get(row["feature"], row["feature"])
        all_feature_keys.add((row["feature"], fk))

    st.markdown("#### Detailed Metrics Comparison")

    for feat_label, feat_key in sorted(all_feature_keys):
        with st.expander(f"**{feat_label}**", expanded=True):
            all_metrics_keys = []
            col_metrics = []
            for row in rows:
                m = _extract_metrics(row["result_json"], feat_key)
                col_metrics.append(m)
                all_metrics_keys.extend(m.keys())

            seen = set()
            ordered_keys = []
            for k in all_metrics_keys:
                if k not in seen:
                    seen.add(k)
                    ordered_keys.append(k)

            comp_data = {"Metric": ordered_keys}
            for i, (label, m) in enumerate(zip(col_labels, col_metrics)):
                comp_data[label] = [str(m.get(k, "—")) for k in ordered_keys]

            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

            # Highlight best for numeric issue counts (lower = better)
            numeric_rows = []
            _LOWER_IS_BETTER = {"Total bugs", "Critical bugs", "Major bugs", "Minor bugs",
                                "Linter issues", "Semantic issues", "Total issues",
                                "Design issues", "PR comments", "Critical comments",
                                "Major comments", "Minor comments", "Suggestion comments",
                                "Concerns"}
            for k in ordered_keys:
                vals = []
                for m in col_metrics:
                    v = m.get(k)
                    if isinstance(v, (int, float)):
                        vals.append(v)
                if vals and k in _LOWER_IS_BETTER:
                    best_val = min(vals)
                    worst_val = max(vals)
                    if best_val != worst_val:
                        best_labels = [col_labels[j] for j, m in enumerate(col_metrics)
                                       if m.get(k) == best_val]
                        numeric_rows.append((k, best_val, ", ".join(best_labels)))

            if numeric_rows:
                st.caption("**Best results** (fewest issues):")
                for metric, val, winners in numeric_rows:
                    st.caption(f"  {metric}: **{val}** — {winners}")


# ══════════════════════════════════════════════════════════════════════════════
# AI ANALYSIS COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
if ai_clicked:
    from agents.comparison import run_comparison

    _SEVERITY_ICON = {"high": "🔴", "medium": "🟠", "low": "🟡"}

    # Prepare analysis data for the agent
    analyses = []
    for i, row in enumerate(rows):
        analyses.append({
            "label": col_labels[i],
            "feature": row["feature"],
            "source_ref": row["source_ref"],
            "result_json": row["result_json"],
        })

    with st.spinner("Running AI comparison agent..."):
        ai_result = run_comparison(analyses)

    if ai_result.get("error"):
        st.error(f"AI comparison failed: {ai_result['error']}")
        st.stop()

    # ── Verdict ──────────────────────────────────────────────────────────────
    st.markdown("#### AI Verdict")
    verdict = ai_result.get("verdict", "")
    if verdict:
        st.info(verdict)

    # ── Quality scores table ─────────────────────────────────────────────────
    quality = ai_result.get("quality_scores", [])
    if quality:
        st.markdown("#### Quality Scores")
        q_data = {
            "Run": [],
            "Depth (1-5)": [],
            "Accuracy (1-5)": [],
            "Actionability (1-5)": [],
            "Notes": [],
        }
        for q in quality:
            q_data["Run"].append(q.get("run", ""))
            q_data["Depth (1-5)"].append(q.get("depth", "—"))
            q_data["Accuracy (1-5)"].append(q.get("accuracy", "—"))
            q_data["Actionability (1-5)"].append(q.get("actionability", "—"))
            q_data["Notes"].append(q.get("notes", ""))
        st.dataframe(pd.DataFrame(q_data), use_container_width=True, hide_index=True)

    # ── Key differences ──────────────────────────────────────────────────────
    differences = ai_result.get("differences", [])
    if differences:
        st.markdown("#### Key Differences")
        diff_data = {
            "Finding": [],
            "Present In": [],
            "Absent From": [],
            "Significance": [],
        }
        for d in differences:
            diff_data["Finding"].append(d.get("finding", ""))
            diff_data["Present In"].append(", ".join(d.get("present_in", [])))
            diff_data["Absent From"].append(", ".join(d.get("absent_from", [])))
            sig = d.get("significance", "medium")
            icon = _SEVERITY_ICON.get(sig, "⚪")
            diff_data["Significance"].append(f"{icon} {sig}")
        st.dataframe(pd.DataFrame(diff_data), use_container_width=True, hide_index=True)

    # ── Common findings ──────────────────────────────────────────────────────
    common = ai_result.get("common_findings", [])
    if common:
        st.markdown("#### Common Findings (across all runs)")
        for cf in common:
            confidence = cf.get("confidence", "medium")
            icon = "✅" if confidence == "high" else "🔵"
            st.markdown(f"- {icon} **[{confidence}]** {cf.get('finding', '')}")

    # ── Recommendation ───────────────────────────────────────────────────────
    rec = ai_result.get("recommendation", "")
    if rec:
        st.markdown("#### Recommendation")
        st.success(rec)

    # ── Executive summary ────────────────────────────────────────────────────
    summary = ai_result.get("summary", "")
    if summary:
        st.divider()
        st.caption(f"**Executive summary:** {summary}")
