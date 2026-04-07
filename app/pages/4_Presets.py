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
    st.dataframe(df, use_container_width=True)

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
