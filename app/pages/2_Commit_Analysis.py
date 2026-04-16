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

import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import create_job
from agents.commit_analysis import run_commit_analysis
from agents.release_notes import run_release_notes
from agents.developer_activity import run_developer_activity
from agents.commit_hygiene import run_commit_hygiene
from agents.churn_analysis import run_churn_analysis
from config.settings import get_settings
from app.components.result_tabs import render_results
from tools.clone_repo import parse_github_url, clone_or_pull, get_git_log

st.set_page_config(page_title="Commits — AI Code Maniac", layout="wide")
st.title("Commit Analysis")

conn = get_connection()
init_schema(conn)
s = get_settings()

source = st.radio("Source", ["GitHub (Clone)", "GitHub (API)", "Gitea"], horizontal=True)

COMMIT_MODES = {
    "Commit Analysis": "commit_analysis",
    "Release Notes": "release_notes",
    "Developer Activity": "developer_activity",
    "Commit Hygiene": "commit_hygiene",
    "Churn Analysis": "churn_analysis",
}

SPINNER_MSGS = {
    "Commit Analysis": "Analyzing commits with AI...",
    "Release Notes": "Generating release notes...",
    "Developer Activity": "Analyzing developer activity...",
    "Commit Hygiene": "Auditing commit conventions...",
    "Churn Analysis": "Analyzing file churn patterns...",
}

analysis_mode = st.selectbox(
    "Analysis Mode",
    list(COMMIT_MODES.keys()),
    key="commits_analysis_mode",
    help="**Commit Analysis** — review quality, risk, changelog.  \n"
         "**Release Notes** — polished user-facing notes.  \n"
         "**Developer Activity** — contributor stats and patterns.  \n"
         "**Commit Hygiene** — conventional commits compliance audit.  \n"
         "**Churn Analysis** — file hotspot detection (clone only).",
)

# Source-availability warnings
source_has_files = (source == "GitHub (Clone)")
if analysis_mode == "Churn Analysis" and not source_has_files:
    st.warning("⚠️ Churn Analysis requires file change data. Switch to **GitHub (Clone)** source.")
if analysis_mode == "Developer Activity" and not source_has_files:
    st.info("Developer Activity works best with clone data (dates + files). "
            "Results from API sources will be limited to author/message analysis.")

can_run = not (analysis_mode == "Churn Analysis" and not source_has_files)

custom_prompt = None
with st.expander("Advanced / Fine-tune"):
    from config.prompt_templates import TEMPLATE_CATEGORIES, apply_template
    template_options = ["None"] + TEMPLATE_CATEGORIES
    chosen_template = st.selectbox(
        "Enhanced Template", template_options,
        key="commits_enhanced_template",
        help="Built-in expert prompt templates that enhance analysis depth and quality.",
    )
    custom_prompt = st.text_area("System Prompt override", height=80) or None
    if chosen_template != "None":
        feature_key = COMMIT_MODES.get(analysis_mode, "commit_analysis")
        custom_prompt = apply_template(chosen_template, feature_key, custom_prompt, language=None)


def _run_selected_analysis(conn, job_id, repo_ref, commits, custom_prompt, mode):
    """Run the selected analysis mode and return (feature_key, result)."""
    if mode == "Release Notes":
        return "release_notes", run_release_notes(
            conn=conn, job_id=job_id, repo_ref=repo_ref,
            commits=commits, custom_prompt=custom_prompt,
        )
    elif mode == "Developer Activity":
        return "developer_activity", run_developer_activity(
            conn=conn, job_id=job_id, repo_ref=repo_ref,
            commits=commits, custom_prompt=custom_prompt,
        )
    elif mode == "Commit Hygiene":
        return "commit_hygiene", run_commit_hygiene(
            conn=conn, job_id=job_id, repo_ref=repo_ref,
            commits=commits, custom_prompt=custom_prompt,
        )
    elif mode == "Churn Analysis":
        return "churn_analysis", run_churn_analysis(
            conn=conn, job_id=job_id, repo_ref=repo_ref,
            commits=commits, custom_prompt=custom_prompt,
        )
    else:
        return "commit_analysis", run_commit_analysis(
            conn=conn, job_id=job_id, repo_ref=repo_ref,
            commits=commits, custom_prompt=custom_prompt,
        )

if source == "GitHub (Clone)":
    url_input = st.text_input(
        "GitHub URL / Repository",
        placeholder="https://github.com/owner/repo.git  or  owner/repo",
        key="commits_github_url",
    )
    branch = st.text_input("Branch", value="main", key="commits_branch")
    token = st.text_input(
        "GitHub token", value=s.github_token or "", type="password",
        help="Optional — only needed for private repos",
        key="commits_github_token",
    )
    effective_token = token or s.github_token or None

    all_commits_flag = st.checkbox("All commits", value=False, key="all_commits")
    if all_commits_flag:
        limit = None
        st.caption("Will analyse all commits in the repository.")
    else:
        limit = st.slider("Number of commits to analyze", 5, 500, 50,
                           key="commits_limit_clone")

    parsed = None
    if url_input:
        try:
            parsed = parse_github_url(url_input)
        except ValueError:
            st.error("Could not parse GitHub URL. Use `owner/repo` or a full URL.")

    if st.button("Clone & Analyze Commits", type="primary",
                 disabled=not can_run,
                 key="clone_analyze_btn") and parsed:
        repo_slug = parsed["slug"]

        with st.spinner("Cloning / pulling repository..."):
            clone_result = clone_or_pull(repo_slug, branch=branch,
                                         token=effective_token)
        if "error" in clone_result:
            st.error(clone_result["error"])
        else:
            st.success(f"Repository ready at `{clone_result['path']}`")

            with st.spinner("Reading commit history..."):
                commits = get_git_log(clone_result["path"], limit=limit)

            if commits:
                st.info(f"Found {len(commits)} commit(s).")
                feature_key = COMMIT_MODES[analysis_mode]
                job_id = create_job(
                    conn, source_type="github",
                    source_ref=f"{repo_slug}::{branch}",
                    language=None, features=[feature_key],
                )
                with st.spinner(SPINNER_MSGS.get(analysis_mode, "Analyzing...")):
                    fkey, result = _run_selected_analysis(
                        conn, job_id, f"{repo_slug}::{branch}",
                        commits, custom_prompt, analysis_mode,
                    )
                render_results({fkey: result})
            else:
                st.warning("No commits found in the repository.")

elif source == "GitHub (API)":
    repo = st.text_input("Repository (owner/repo)", key="commits_api_repo")
    branch = st.text_input("Branch", value="main", key="commits_api_branch")
    token = st.text_input(
        "GitHub token", value=s.github_token or "", type="password",
        help="Optional — only needed for private repos",
        key="commits_api_token",
    )
    limit = st.slider("Number of commits to analyze", 5, 100, 20,
                       key="commits_limit_api")

    if st.button("Fetch & Analyze Commits", type="primary",
                 disabled=not can_run,
                 key="api_analyze_btn") and repo:
        effective_token = token or s.github_token or None
        with st.spinner("Fetching commits via API..."):
            from github import Github
            g = Github(effective_token) if effective_token else Github()
            try:
                r = g.get_repo(repo)
                commits = [
                    {"sha": c.sha[:8], "message": c.commit.message,
                     "author": c.commit.author.name}
                    for c in r.get_commits(sha=branch)[:limit]
                ]
            except Exception as e:
                commits = []
                st.error(f"GitHub API error: {e}")

        if commits:
            feature_key = COMMIT_MODES[analysis_mode]
            job_id = create_job(
                conn, source_type="github",
                source_ref=f"{repo}::{branch}",
                language=None, features=[feature_key],
            )
            with st.spinner(SPINNER_MSGS.get(analysis_mode, "Analyzing...")):
                fkey, result = _run_selected_analysis(
                    conn, job_id, f"{repo}::{branch}",
                    commits, custom_prompt, analysis_mode,
                )
            render_results({fkey: result})
        elif not st.session_state.get("_api_error"):
            st.warning("No commits found or fetch failed.")

else:  # Gitea
    from tools.fetch_gitea import fetch_gitea_commits
    repo = st.text_input("Repository (owner/repo)", key="commits_gitea_repo")
    branch = st.text_input("Branch", value="main", key="commits_gitea_branch")
    limit = st.slider("Number of commits to analyze", 5, 100, 20,
                       key="commits_limit_gitea")

    if st.button("Fetch & Analyze Commits", type="primary",
                 disabled=not can_run,
                 key="gitea_analyze_btn") and repo:
        with st.spinner("Fetching commits from Gitea..."):
            result = fetch_gitea_commits(
                gitea_url=s.gitea_url, repo=repo,
                branch=branch, token=s.gitea_token, limit=limit,
            )
            commits = result.get("commits", [])

        if commits:
            feature_key = COMMIT_MODES[analysis_mode]
            job_id = create_job(
                conn, source_type="gitea",
                source_ref=f"{repo}::{branch}",
                language=None, features=[feature_key],
            )
            with st.spinner(SPINNER_MSGS.get(analysis_mode, "Analyzing...")):
                fkey, result = _run_selected_analysis(
                    conn, job_id, f"{repo}::{branch}",
                    commits, custom_prompt, analysis_mode,
                )
            render_results({fkey: result})
        else:
            st.warning("No commits found or fetch failed.")
