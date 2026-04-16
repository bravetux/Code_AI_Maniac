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
import pandas as pd
from db.connection import get_connection
from db.queries.presets import list_presets, delete_preset, create_preset

st.set_page_config(page_title="Presets — AI Code Maniac", layout="wide")
st.title("Prompt Presets")

conn = get_connection()
presets = list_presets(conn)

if presets:
    df = pd.DataFrame(presets)[["name", "feature", "system_prompt", "extra_instructions", "created_at"]]
    st.dataframe(df, width="stretch")

    st.subheader("Delete Preset")
    preset_to_delete = st.selectbox("Select preset to delete",
                                     [""] + [p["name"] for p in presets])
    if st.button("Delete") and preset_to_delete:
        target = next((p for p in presets if p["name"] == preset_to_delete), None)
        if target:
            delete_preset(conn, target["id"])
            st.success(f"Deleted '{preset_to_delete}'")
            st.rerun()
else:
    st.info("No presets saved yet. Create one from the Analysis page.")

st.divider()
st.subheader("Create New Preset")
with st.form("create_preset"):
    name = st.text_input("Preset Name")
    feature = st.selectbox("Feature", ["bug_analysis", "code_design", "code_flow",
                                        "mermaid", "requirement", "static_analysis",
                                        "comment_generator", "commit_analysis"])
    system_prompt = st.text_area("System Prompt", height=120)
    extra = st.text_input("Extra Instructions")
    if st.form_submit_button("Save Preset") and name and system_prompt:
        create_preset(conn, name=name, feature=feature,
                      system_prompt=system_prompt, extra_instructions=extra)
        st.success(f"Preset '{name}' saved.")
        st.rerun()
