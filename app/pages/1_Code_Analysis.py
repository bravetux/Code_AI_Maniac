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
from app.components.security_selector import render_security_selector
from app.components.security_results import render_security_results, render_preflight_banner

st.set_page_config(page_title="Analysis — AI Code Maniac", layout="wide")
st.title("Code Analysis")

conn = get_connection()
init_schema(conn)

with st.sidebar:
    render_sidebar_profile(conn)
    source = render_source_selector()
    feature_config = render_feature_selector(conn)
    security_config = render_security_selector()
    all_features = feature_config["features"] + security_config["security_features"]
    run_clicked = st.button("Run Analysis", type="primary",
                            disabled=not source.get("source_ref") or not all_features)

if run_clicked:
    job_id = create_job(
        conn,
        source_type=source["source_type"],
        source_ref=source["source_ref"],
        language=feature_config["language"] or None,
        features=feature_config["features"] + security_config["security_features"],
        custom_prompt=feature_config["custom_prompt"],
        template_category=feature_config.get("template_category"),
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
    "bug_analysis":        "Bug Analysis",
    "static_analysis":     "Static Analysis",
    "code_flow":           "Code Flow",
    "requirement":         "Requirements",
    "code_design":         "Code Design",
    "mermaid":             "Mermaid Diagram",
    "comment_generator":   "PR Comments",
    "commit_analysis":     "Commit Analysis",
    "report_per_file":     "Per-File Report",
    "report_consolidated": "Consolidated Report",
    "secret_scan":          "Secret Scan",
    "secret_scan_preflight":"Secret Pre-flight",
    "dependency_analysis":  "Dependency Analysis",
    "threat_model":         "Threat Model",
}

_EVENT_ICON = {
    "fetch":           "📂",
    "phase":           "—",
    "start":           "🔄",
    "complete":        "✅",
    "cached":          "⚡",
    "error":           "❌",
    "report_start":    "📝",
    "report_complete": "📄",
    "report_error":    "❌",
}


def _render_live_progress(conn, job_id: str, job: dict) -> None:
    features = job.get("features") or []
    analysis_features = [f for f in features if f != "commit_analysis"]
    events = get_events(conn, job_id)

    # Count source files from fetch events
    file_count = 1  # default
    for ev in events:
        if ev["event_type"] == "fetch" and ev.get("message", "").startswith("Loaded"):
            msg = ev["message"]
            try:
                file_count = int(msg.split()[1])
            except (IndexError, ValueError):
                pass

    # ── Phase 1: Analysis progress ───────────────────────────────────────
    analysis_total = len(analysis_features) * file_count
    analysis_done = sum(1 for e in events
                        if e["event_type"] in ("complete", "cached", "error")
                        and e.get("agent") not in ("report_per_file", "report_consolidated"))
    analysis_pct = min(int((analysis_done / max(analysis_total, 1)) * 100), 99)

    # Check if analysis is truly done (report events have started)
    report_events = [e for e in events if e["event_type"].startswith("report_")]
    analysis_finished = len(report_events) > 0 or analysis_done >= analysis_total

    if analysis_finished:
        st.progress(100, text=f"Analysis complete — {analysis_done}/{analysis_total} agents done")
    else:
        st.progress(analysis_pct, text=f"Analyzing… {analysis_done}/{analysis_total} agents done")

    # ── Phase 2: Report generation progress ──────────────────────────────
    if report_events:
        report_done = sum(1 for e in report_events if e["event_type"] == "report_complete")
        report_started = sum(1 for e in report_events if e["event_type"] == "report_start")
        report_total = max(report_started, report_done, 1)
        report_pct = min(int((report_done / report_total) * 100), 99)
        st.progress(report_pct, text=f"Generating reports… {report_done}/{report_total}")

    # ── Live Activity Log ────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("##### Live Activity")
        if not events:
            st.caption("Starting up…")
        for ev in events:
            etype   = ev["event_type"]
            agent   = ev.get("agent") or ""
            fpath   = ev.get("file_path") or ""
            message = ev.get("message") or ""
            icon    = _EVENT_ICON.get(etype, "•")
            fname   = os.path.basename(fpath) if fpath else ""
            label   = _AGENT_LABELS.get(agent, agent)

            if etype == "phase":
                st.markdown(f"&nbsp;&nbsp;**{message}**")
            elif etype == "fetch":
                st.markdown(f"{icon} &nbsp; {message}")
            elif etype in ("start", "report_start"):
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + " &nbsp; *running…*"
                )
            elif etype in ("cached",):
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + f" &nbsp; *cache hit* — {message}"
                )
            elif etype in ("complete", "report_complete"):
                st.markdown(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;{icon} &nbsp; **{label}**"
                    + (f" &nbsp; `{fname}`" if fname else "")
                    + (f" &nbsp; — {message}" if message else "")
                )
            elif etype in ("error", "report_error"):
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
    "blocked":   "Blocked — secrets detected",
}
st.caption(f"Job `{job_id[:8]}...` — {STATUS_LABEL.get(status, status)}")

if status in ("pending", "running"):
    _render_live_progress(conn, job_id, job)
    time.sleep(2)
    st.rerun()

elif status == "completed":
    results = get_job_results(conn, job_id)
    if results:
        render_results(results, source_ref=job.get("source_ref", ""))
        render_preflight_banner(results)
        render_security_results(results)
    else:
        st.warning("Analysis completed but no results were saved. Check the terminal for errors.")

elif status == "blocked":
    results = get_job_results(conn, job_id) or {}
    render_preflight_banner(results)
    st.warning("Analysis was blocked by the security pre-flight scanner. "
               "Remove detected secrets and resubmit, or change SECRET_SCAN_MODE in settings.")
    if st.button("Clear and start over"):
        del st.session_state["current_job_id"]
        st.rerun()

elif status == "failed":
    results = get_job_results(conn, job_id) or {}
    err = results.get("error", "Unknown error — check the terminal for the full traceback.")
    st.error(f"Analysis failed: {err}")
    if st.button("Clear and start over"):
        del st.session_state["current_job_id"]
        st.rerun()
