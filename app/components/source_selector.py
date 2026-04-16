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

import os
import tempfile
import streamlit as st
from config.settings import get_settings
from tools.fetch_local import scan_folder_recursive
from tools.clone_repo import parse_github_url, clone_or_pull


def _pick_file() -> str:
    """Open a native file-picker dialog and return the selected path (or '')."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title="Select a file",
            filetypes=[
                ("Code files",
                 " ".join(f"*.{e}" for e in [
                     "py","js","ts","jsx","tsx","java","cs","cpp","c","h",
                     "go","rs","rb","php","swift","kt","scala","sql",
                     "html","css","json","yaml","yml","toml","xml","md","sh",
                 ])),
                ("All files", "*.*"),
            ],
        )
        root.destroy()
        return path or ""
    except Exception:
        return ""


def _pick_folder() -> str:
    """Open a native folder-picker dialog and return the selected path (or '')."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        path = filedialog.askdirectory(title="Select a folder")
        root.destroy()
        return path or ""
    except Exception:
        return ""

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
            if st.button("📂 Browse for file", key="browse_file_btn"):
                picked = _pick_file()
                if picked:
                    st.session_state["local_file_path"] = picked
            path = st.text_input("File path", placeholder="/path/to/file.py",
                                 key="local_file_path")
            result["source_ref"] = path

        else:  # Folder (recursive)
            if st.button("📂 Browse for folder", key="browse_folder_btn"):
                picked = _pick_folder()
                if picked:
                    st.session_state["local_folder_path"] = picked
            folder = st.text_input("Folder path", placeholder="/path/to/project",
                                   key="local_folder_path")

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

        url_input = st.text_input(
            "GitHub URL / Repository",
            placeholder="https://github.com/owner/repo.git  or  owner/repo",
            key="github_url_input",
        )
        branch = st.text_input("Branch", value="main", key="github_branch")
        token = st.text_input(
            "GitHub token",
            value=s.github_token or "",
            type="password",
            help="Optional — only needed for private repos",
            key="github_token_input",
        )
        if token and token != s.github_token:
            st.session_state["github_token_override"] = token

        effective_token = token or s.github_token or None

        # --- Parse URL into owner/repo ---
        parsed = None
        if url_input:
            try:
                parsed = parse_github_url(url_input)
            except ValueError:
                st.error("Could not parse GitHub URL. Use `owner/repo` or a full URL.")

        # --- Clone & Browse / Re-pull ---
        if parsed:
            repo_slug = parsed["slug"]
            clone_dest = os.path.join("data", "repos", parsed["owner"], parsed["repo"])
            already_cloned = os.path.isdir(os.path.join(clone_dest, ".git"))

            col_clone, col_pull = st.columns(2)
            with col_clone:
                if st.button(
                    "🔄 Re-pull" if already_cloned else "📥 Clone & Browse",
                    key="clone_btn",
                    type="primary",
                ):
                    with st.spinner("Cloning repository..." if not already_cloned
                                    else "Pulling latest changes..."):
                        clone_result = clone_or_pull(
                            repo_slug, branch=branch, token=effective_token
                        )
                    if "error" in clone_result:
                        st.error(clone_result["error"])
                    else:
                        st.session_state["cloned_repo_path"] = clone_result["path"]
                        st.session_state["cloned_repo_slug"] = repo_slug
                        st.success(
                            f"{'Pulled' if clone_result['status'] == 'pulled' else 'Cloned'}"
                            f" to `{clone_result['path']}`"
                        )

            if already_cloned and "cloned_repo_path" not in st.session_state:
                st.session_state["cloned_repo_path"] = clone_dest
                st.session_state["cloned_repo_slug"] = repo_slug

            # --- File selection from cloned repo (folder-recursive reuse) ---
            cloned_path = st.session_state.get("cloned_repo_path")
            if cloned_path and os.path.isdir(cloned_path):
                st.divider()
                st.subheader("Select files to analyse")

                with st.expander("Filter by extension", expanded=False):
                    use_filter = st.checkbox(
                        "Filter by extension", value=True,
                        key="gh_folder_ext_filter",
                    )
                    if use_filter:
                        chosen_exts = st.multiselect(
                            "Extensions to include",
                            options=_DEFAULT_EXTENSIONS,
                            default=_DEFAULT_EXTENSIONS,
                            key="gh_folder_exts",
                        )
                    else:
                        chosen_exts = None

                all_files = scan_folder_recursive(
                    cloned_path,
                    extensions=chosen_exts if use_filter else None,
                )
                total_found = len(all_files)

                if total_found == 0:
                    st.info("No matching files found in the cloned repo.")
                else:
                    st.caption(
                        f"Found **{total_found}** file(s). "
                        f"Limit: **{max_files}** (MAX_FILES in .env)."
                    )

                    rel_map = {
                        os.path.relpath(p, cloned_path): p for p in all_files
                    }
                    rel_paths = list(rel_map.keys())
                    default_selected = rel_paths[:max_files]

                    selected_rel = st.multiselect(
                        f"Select files to analyse (max {max_files})",
                        options=rel_paths,
                        default=default_selected,
                        key="gh_folder_file_select",
                    )

                    if len(selected_rel) > max_files:
                        st.error(
                            f"Too many files selected ({len(selected_rel)}). "
                            f"Please deselect down to {max_files}."
                        )
                        selected_rel = selected_rel[:max_files]

                    if selected_rel:
                        selected_abs = [rel_map[r] for r in selected_rel]
                        # Treat cloned files as local source
                        result["source_type"] = "local"
                        result["source_ref"] = "::".join(selected_abs)
                        st.caption(f"{len(selected_rel)} file(s) selected.")

            # --- Fallback: single file via API (no clone needed) ---
            elif not cloned_path:
                st.divider()
                file_path = st.text_input("Or enter a single file path (API fetch)",
                                          placeholder="src/main.py",
                                          key="github_file_path")
                if parsed and branch and file_path:
                    result["source_ref"] = f"{repo_slug}::{branch}::{file_path}"

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
