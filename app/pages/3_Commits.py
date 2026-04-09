import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import create_job
from agents.commit_analysis import run_commit_analysis
from config.settings import get_settings
from app.components.result_tabs import render_results
from tools.clone_repo import parse_github_url, clone_or_pull, get_git_log

st.set_page_config(page_title="Commits — AI Code Maniac", layout="wide")
st.title("Commit Analysis")

conn = get_connection()
init_schema(conn)
s = get_settings()

source = st.radio("Source", ["GitHub (Clone)", "GitHub (API)", "Gitea"], horizontal=True)

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
        custom_prompt = apply_template(chosen_template, "commit_analysis", custom_prompt)

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
                job_id = create_job(
                    conn, source_type="github",
                    source_ref=f"{repo_slug}::{branch}",
                    language=None, features=["commit_analysis"],
                )
                with st.spinner("Analyzing commits with AI..."):
                    result = run_commit_analysis(
                        conn=conn, job_id=job_id,
                        repo_ref=f"{repo_slug}::{branch}",
                        commits=commits, custom_prompt=custom_prompt,
                    )
                render_results({"commit_analysis": result})
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
            job_id = create_job(
                conn, source_type="github",
                source_ref=f"{repo}::{branch}",
                language=None, features=["commit_analysis"],
            )
            with st.spinner("Analyzing commits with AI..."):
                result = run_commit_analysis(
                    conn=conn, job_id=job_id,
                    repo_ref=f"{repo}::{branch}",
                    commits=commits, custom_prompt=custom_prompt,
                )
            render_results({"commit_analysis": result})
        elif not st.session_state.get("_api_error"):
            st.warning("No commits found or fetch failed.")

else:  # Gitea
    from tools.fetch_gitea import fetch_gitea_commits
    repo = st.text_input("Repository (owner/repo)", key="commits_gitea_repo")
    branch = st.text_input("Branch", value="main", key="commits_gitea_branch")
    limit = st.slider("Number of commits to analyze", 5, 100, 20,
                       key="commits_limit_gitea")

    if st.button("Fetch & Analyze Commits", type="primary",
                 key="gitea_analyze_btn") and repo:
        with st.spinner("Fetching commits from Gitea..."):
            result = fetch_gitea_commits(
                gitea_url=s.gitea_url, repo=repo,
                branch=branch, token=s.gitea_token, limit=limit,
            )
            commits = result.get("commits", [])

        if commits:
            job_id = create_job(
                conn, source_type="gitea",
                source_ref=f"{repo}::{branch}",
                language=None, features=["commit_analysis"],
            )
            with st.spinner("Analyzing commits with AI..."):
                result = run_commit_analysis(
                    conn=conn, job_id=job_id,
                    repo_ref=f"{repo}::{branch}",
                    commits=commits, custom_prompt=custom_prompt,
                )
            render_results({"commit_analysis": result})
        else:
            st.warning("No commits found or fetch failed.")
