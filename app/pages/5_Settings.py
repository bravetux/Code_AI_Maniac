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

import tempfile
import zipfile
import streamlit as st
from db.connection import get_connection, reset_connection
from config.settings import get_settings

st.set_page_config(page_title="Settings — AI Code Maniac", layout="wide")
st.title("Settings")

conn = get_connection()
s = get_settings()

# ── AWS / Bedrock ───────────────────────────────────────────────
st.header("AWS / Bedrock")
st.text_input("AWS Region", value=s.aws_region, disabled=True,
              help="Set via AWS_REGION in .env")
st.text_input("Bedrock Model ID", value=s.bedrock_model_id, disabled=True,
              help="Set via BEDROCK_MODEL_ID in .env")
temperature = st.slider("Temperature", 0.0, 1.0, value=s.bedrock_temperature, step=0.05)
if temperature != s.bedrock_temperature:
    st.session_state["temperature_override"] = temperature
    st.info(f"Temperature set to {temperature} for this session. Update .env to persist.")

# ── Source Integrations ─────────────────────────────────────────
st.header("Source Integrations")
col1, col2 = st.columns(2)
col1.text_input("GitHub Token", value="••••••" if s.github_token else "(not set)",
                disabled=True, help="Set via GITHUB_TOKEN in .env")
col2.text_input("Gitea URL", value=s.gitea_url or "(not set)", disabled=True,
                help="Set via GITEA_URL in .env")
col2.text_input("Gitea Token", value="••••••" if s.gitea_token else "(not set)",
                disabled=True, help="Set via GITEA_TOKEN in .env")

# ── Security Testing ──────────────────────────────────────────
st.header("Security Testing")
st.text_input("Secret Scan Mode", value=s.secret_scan_mode, disabled=True,
              help="Set via SECRET_SCAN_MODE in .env. Values: block, redact, warn")
st.text_input("SCA CVE Backend", value=s.sca_cve_backend, disabled=True,
              help="Set via SCA_CVE_BACKEND in .env. Values: osv, nvd, github, llm, osv_llm")
st.text_input("SCA Auto-Discover", value=str(s.sca_auto_discover), disabled=True,
              help="Set via SCA_AUTO_DISCOVER in .env. Auto-discover dependency files from repo")
st.text_input("NVD API Key", value="••••••" if s.nvd_api_key else "(not set)", disabled=True,
              help="Set via NVD_API_KEY in .env. Required for NVD backend")

# ── Database Backup / Restore ────────────────────────────────────
st.header("Database Backup & Restore")
st.caption(f"Database file: `{os.path.abspath(s.db_path)}`")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Export")
    if st.button("Export DB to ZIP"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            export_dir = os.path.join(tmp_dir, "arena_export")
            os.makedirs(export_dir)
            conn.execute(f"EXPORT DATABASE '{export_dir}' (FORMAT PARQUET)")
            zip_path = os.path.join(tmp_dir, "arena_backup.zip")
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, _, files in os.walk(export_dir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        zf.write(filepath, os.path.relpath(filepath, tmp_dir))
            with open(zip_path, "rb") as f:
                st.download_button("Download arena_backup.zip", data=f.read(),
                                   file_name="arena_backup.zip",
                                   mime="application/zip")

with col2:
    st.subheader("Import")
    st.warning("Importing will overwrite all current data.")
    uploaded_zip = st.file_uploader("Upload backup ZIP", type=["zip"])
    if uploaded_zip and st.button("Restore from ZIP"):
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "restore.zip")
            with open(zip_path, "wb") as f:
                f.write(uploaded_zip.read())
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(tmp_dir)
            export_dir = os.path.join(tmp_dir, "arena_export")
            if os.path.exists(export_dir):
                conn.execute(f"IMPORT DATABASE '{export_dir}'")
                reset_connection()
                st.success("Database restored successfully. Please refresh the page.")
                st.rerun()
            else:
                st.error("Invalid backup ZIP — missing arena_export directory.")
