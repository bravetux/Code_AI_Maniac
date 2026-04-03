import threading
import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import create_job, get_job
from agents.orchestrator import run_analysis
from app.components.source_selector import render_source_selector
from app.components.feature_selector import render_feature_selector
from app.components.result_tabs import render_results

st.set_page_config(page_title="Analysis — AI Arena", layout="wide")
st.title("Code Analysis")

conn = get_connection()
init_schema(conn)

with st.sidebar:
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
    st.session_state["analysis_results"] = None

    def _run():
        results = run_analysis(conn=conn, job_id=job_id)
        st.session_state["analysis_results"] = results

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    st.rerun()

# Show progress / results
if "current_job_id" in st.session_state:
    job_id = st.session_state["current_job_id"]
    job = get_job(conn, job_id)

    if job:
        status = job["status"]
        status_display = {"pending": "Pending...", "running": "Analyzing...",
                          "completed": "Complete", "failed": "Failed"}.get(status, status)

        st.caption(f"Job `{job_id[:8]}...` — {status_display}")

        if status in ("pending", "running"):
            st.progress(0 if status == "pending" else 50,
                        text=f"{status_display} (refresh to update)")
            if st.button("Refresh"):
                st.rerun()

        elif status == "completed" and st.session_state.get("analysis_results"):
            render_results(st.session_state["analysis_results"])

        elif status == "failed":
            st.error("Analysis failed. Check your credentials and source configuration.")
