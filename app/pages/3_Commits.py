import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import create_job
from agents.commit_analysis import run_commit_analysis
from config.settings import get_settings
from app.components.result_tabs import render_results

st.set_page_config(page_title="Commits — AI Arena", layout="wide")
st.title("Commit Analysis")

conn = get_connection()
init_schema(conn)
s = get_settings()

source = st.radio("Source", ["GitHub", "Gitea"], horizontal=True)
repo = st.text_input("Repository (owner/repo)")
branch = st.text_input("Branch", value="main")
limit = st.slider("Number of commits to analyze", 5, 100, 20)

custom_prompt = None
with st.expander("Advanced / Fine-tune"):
    custom_prompt = st.text_area("System Prompt override", height=80) or None

if st.button("Fetch & Analyze Commits", type="primary") and repo:
    with st.spinner("Fetching commits..."):
        if source == "GitHub":
            from github import Github
            g = Github(s.github_token)
            r = g.get_repo(repo)
            commits = [{"sha": c.sha[:8], "message": c.commit.message,
                        "author": c.commit.author.name}
                       for c in r.get_commits(sha=branch)[:limit]]
        else:  # Gitea
            from tools.fetch_gitea import fetch_gitea_commits
            result = fetch_gitea_commits(gitea_url=s.gitea_url, repo=repo,
                                         branch=branch, token=s.gitea_token, limit=limit)
            commits = result.get("commits", [])

    if commits:
        job_id = create_job(conn, source_type=source.lower(), source_ref=f"{repo}::{branch}",
                            language=None, features=["commit_analysis"])
        with st.spinner("Analyzing commits with AI..."):
            result = run_commit_analysis(conn=conn, job_id=job_id,
                                         repo_ref=f"{repo}::{branch}",
                                         commits=commits, custom_prompt=custom_prompt)
        render_results({"commit_analysis": result})
    else:
        st.warning("No commits found or fetch failed.")
