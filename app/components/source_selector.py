import os
import tempfile
import streamlit as st
from config.settings import get_settings


def render_source_selector() -> dict:
    """
    Render source selection UI.
    Returns dict with keys: source_type, source_ref, start_line, end_line
    """
    s = get_settings()
    source_type = st.radio("Source", ["Local File", "GitHub", "Gitea"],
                           horizontal=True)

    result = {"source_type": "", "source_ref": "", "start_line": None, "end_line": None}

    if source_type == "Local File":
        result["source_type"] = "local"
        uploaded = st.file_uploader("Upload file(s)", accept_multiple_files=True,
                                    help="Select up to 50 files")
        if uploaded:
            paths = []
            for f in uploaded[:50]:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(f.name)[1])
                tmp.write(f.read())
                tmp.close()
                paths.append(tmp.name)
            result["source_ref"] = "::".join(paths)
        else:
            path = st.text_input("Or enter file path", placeholder="/path/to/file.py")
            result["source_ref"] = path

    elif source_type == "GitHub":
        result["source_type"] = "github"
        repo = st.text_input("Repository (owner/repo)", placeholder="octocat/Hello-World")
        branch = st.text_input("Branch", value="main")
        file_path = st.text_input("File path", placeholder="src/main.py")
        token = st.text_input("GitHub token", value=s.github_token or "", type="password")
        if repo and branch and file_path:
            result["source_ref"] = f"{repo}::{branch}::{file_path}"
        if token and token != s.github_token:
            st.session_state["github_token_override"] = token

    elif source_type == "Gitea":
        result["source_type"] = "gitea"
        gitea_url = st.text_input("Gitea URL", value=s.gitea_url or "http://localhost:3000")
        repo = st.text_input("Repository (owner/repo)", placeholder="myuser/myrepo")
        branch = st.text_input("Branch", value="main")
        file_path = st.text_input("File path", placeholder="src/main.py")
        token = st.text_input("Gitea token", value=s.gitea_token or "", type="password")
        if repo and branch and file_path:
            result["source_ref"] = f"{repo}::{branch}::{file_path}"
        if gitea_url != s.gitea_url:
            st.session_state["gitea_url_override"] = gitea_url

    with st.expander("Line Range (optional)"):
        col1, col2 = st.columns(2)
        start = col1.number_input("Start line", min_value=1, value=1)
        end = col2.number_input("End line", min_value=1, value=1)
        if not (start == 1 and end == 1):
            result["start_line"] = start
            result["end_line"] = end

    return result
