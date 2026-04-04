import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import time
import threading
import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import create_job, get_job, get_job_results
from db.queries.job_events import get_events
from agents.orchestrator import run_analysis
from app.components.source_selector import render_source_selector
from app.components.feature_selector import render_feature_selector
from app.components.result_tabs import render_results
from app.components.sidebar_profile import render_sidebar_profile

st.set_page_config(page_title="Analysis — AI Arena", layout="wide")
st.title("Code Analysis")

conn = get_connection()
init_schema(conn)

with st.sidebar:
    render_sidebar_profile(conn)
    source = render_source_selector()
    feature_config = render_feature_selector(conn)
    run_clicked = st.button("Run Analysis", type="primary",
                            disabled=not source.get("source_ref") or not feature_config["features"])

if run_clicked:
    job_id = create_job(
        conn,
        source_type=source["source_type"],
        source_ref=source["source_ref"],
        language=feature_config["language"] or None,
        features=feature_config["features"],
        custom_prompt=feature_config["custom_prompt"],
    )
    st.session_state["current_job_id"] = job_id

    def _run(jid):
        run_analysis(conn=conn, job_id=jid)

    threading.Thread(target=_run, args=(job_id,), daemon=True).start()
    st.rerun()

# ── Show progress / results ───────────────────────────────────────────────────
if "current_job_id" not in st.session_state:
    st.info("Configure a source and select features in the sidebar, then click **Run Analysis**.")
    st.stop()

job_id = st.session_state["current_job_id"]
job = get_job(conn, job_id)

if not job:
    st.warning("Job not found.")
    st.stop()

_AGENT_LABELS = {
    "bug_analysis":      "Bug Analysis",
    "static_analysis":   "Static Analysis",
    "code_flow":         "Code Flow",
    "requirement":       "Requirements",
    "code_design":       "Code Design",
    "mermaid":           "Mermaid Diagram",
    "comment_generator": "PR Comments",
    "commit_analysis":   "Commit Analysis",
}

_EVENT_ICON = {
    "fetch":    "📂",
    "phase":    "—",
    "start":    "🔄",
    "complete": "✅",
    "cached":   "⚡",
    "error":    "❌",
}


def _render_live_progress(conn, job_id: str, job: dict) -> None:
    features = job.get("features") or []
    total    = len([f for f in features if f != "commit_analysis"])

    events = get_events(conn, job_id)
    done   = sum(1 for e in events if e["event_type"] in ("complete", "cached", "error"))
    pct    = min(int((done / max(total, 1)) * 100), 99)   # cap at 99 until truly done

    st.progress(pct, text=f"Analyzing… {done}/{total} agents done")

    with st.container(border=True):
        st.markdown("##### Live Activity")
        if not events:
            st.caption("Starting up…")
        for ev in events:
            etype     = ev["event_type"]
            agent     = ev.get("agent") or ""
            fpath     = ev.get("file_path") or ""
            message   = ev.get("message") or ""
            icon      = _EVENT_ICON.get(etype, "•")
            fname     = os.path.basename(fpath) if fpath else ""
            label     = _AGENT_LABELS.get(agent, agent)

            if etype == "phase":
                st.markdown(f"&nbsp;&nbsp;**{message}**")
            elif etype == "fetch":
                st.markdown(f"{icon} &nbsp; {message}")
            elif etype == "start":
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + " &nbsp; *running…*"
                )
            elif etype == "cached":
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + f" &nbsp; *cache hit* — {message}"
                )
            elif etype == "complete":
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + (f" &nbsp; — {message}" if message else "")
                )
            elif etype == "error":
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + (f" &nbsp; — {message}" if message else "")
                )


status = job["status"]
STATUS_LABEL = {
    "pending":   "Queued...",
    "running":   "Analyzing...",
    "completed": "Complete",
    "failed":    "Failed",
}
st.caption(f"Job `{job_id[:8]}...` — {STATUS_LABEL.get(status, status)}")

if status in ("pending", "running"):
    _render_live_progress(conn, job_id, job)
    time.sleep(2)
    st.rerun()

elif status == "completed":
    results = get_job_results(conn, job_id)
    if results:
        render_results(results)
    else:
        st.warning("Analysis completed but no results were saved. Check the terminal for errors.")

elif status == "failed":
    results = get_job_results(conn, job_id) or {}
    err = results.get("error", "Unknown error — check the terminal for the full traceback.")
    st.error(f"Analysis failed: {err}")
    if st.button("Clear and start over"):
        del st.session_state["current_job_id"]
        st.rerun()
