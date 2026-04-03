import os
import tempfile
import streamlit as st
from config.settings import get_settings
from tools.fetch_local import scan_folder_recursive

# Common source-code extensions shown by default in folder scan
_DEFAULT_EXTENSIONS = [
    "py", "js", "ts", "jsx", "tsx", "java", "cs", "cpp", "c", "h",
    "go", "rs", "rb", "php", "swift", "kt", "scala", "r", "sh",
    "sql", "html", "css", "json", "yaml", "yml", "toml", "xml", "md",
]


def render_source_selector() -> dict:
    """
    Render source selection UI.
    Returns dict with keys: source_type, source_ref, start_line, end_line
    """
    s = get_settings()
    max_files = s.max_files
    source_type = st.radio("Source", ["Local File", "GitHub", "Gitea"],
                           horizontal=True, key="sidebar_source_type")

    result = {"source_type": "", "source_ref": "", "start_line": None, "end_line": None}

    if source_type == "Local File":
        result["source_type"] = "local"
        local_mode = st.radio(
            "Input mode",
            ["Upload files", "File path", "Folder (recursive)"],
            horizontal=True,
            key="local_mode",
        )

        if local_mode == "Upload files":
            uploaded = st.file_uploader(
                f"Upload file(s) — max {max_files}",
                accept_multiple_files=True,
                help=f"Up to {max_files} files (set MAX_FILES in .env to change)",
            )
            if uploaded:
                if len(uploaded) > max_files:
                    st.warning(f"Only the first {max_files} of {len(uploaded)} files will be used.")
                paths = []
                for f in uploaded[:max_files]:
                    tmp = tempfile.NamedTemporaryFile(
                        delete=False, suffix=os.path.splitext(f.name)[1]
                    )
                    tmp.write(f.read())
                    tmp.close()
                    paths.append(tmp.name)
                result["source_ref"] = "::".join(paths)

        elif local_mode == "File path":
            path = st.text_input("File path", placeholder="/path/to/file.py")
            result["source_ref"] = path

        else:  # Folder (recursive)
            folder = st.text_input("Folder path", placeholder="/path/to/project")

            with st.expander("Filter by extension", expanded=False):
                use_filter = st.checkbox("Filter by extension", value=True,
                                         key="folder_ext_filter")
                if use_filter:
                    chosen_exts = st.multiselect(
                        "Extensions to include",
                        options=_DEFAULT_EXTENSIONS,
                        default=_DEFAULT_EXTENSIONS,
                        key="folder_exts",
                    )
                else:
                    chosen_exts = None

            if folder and os.path.isdir(folder):
                all_files = scan_folder_recursive(
                    folder, extensions=chosen_exts if use_filter else None
                )
                total_found = len(all_files)

                if total_found == 0:
                    st.info("No matching files found in that folder.")
                else:
                    st.caption(
                        f"Found **{total_found}** file(s). "
                        f"Limit: **{max_files}** (MAX_FILES in .env)."
                    )

                    # Show relative paths for readability
                    rel_map = {
                        os.path.relpath(p, folder): p for p in all_files
                    }
                    rel_paths = list(rel_map.keys())

                    # Pre-select up to max_files
                    default_selected = rel_paths[:max_files]

                    selected_rel = st.multiselect(
                        f"Select files to analyse (max {max_files})",
                        options=rel_paths,
                        default=default_selected,
                        key="folder_file_select",
                    )

                    if len(selected_rel) > max_files:
                        st.error(
                            f"Too many files selected ({len(selected_rel)}). "
                            f"Please deselect down to {max_files}."
                        )
                        selected_rel = selected_rel[:max_files]

                    if selected_rel:
                        selected_abs = [rel_map[r] for r in selected_rel]
                        result["source_ref"] = "::".join(selected_abs)
                        st.caption(f"{len(selected_rel)} file(s) selected.")

            elif folder:
                st.error(f"Directory not found: `{folder}`")

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
