import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
from config.prompt_templates import TEMPLATES, TEMPLATE_CATEGORIES

st.set_page_config(page_title="Template Browser — AI Code Maniac", layout="wide")
st.title("Template Browser")

AGENT_LABELS = {
    "bug_analysis": "Bug Analysis",
    "code_design": "Code Design",
    "code_flow": "Code Flow",
    "mermaid": "Mermaid Diagram",
    "requirement": "Requirement Design",
    "static_analysis": "Static Analysis",
    "comment_generator": "PR Comment Generator",
    "commit_analysis": "Commit Analysis",
}

total_templates = len(TEMPLATES)
total_categories = len(TEMPLATE_CATEGORIES)
st.caption(f"{total_templates} templates across {total_categories} categories")

st.divider()

col1, col2 = st.columns(2)
with col1:
    selected_categories = st.multiselect(
        "Category",
        options=TEMPLATE_CATEGORIES,
        default=TEMPLATE_CATEGORIES,
        placeholder="All categories",
    )
with col2:
    all_agents = sorted(AGENT_LABELS.keys())
    selected_agents = st.multiselect(
        "Agent",
        options=all_agents,
        default=all_agents,
        format_func=lambda a: AGENT_LABELS.get(a, a),
        placeholder="All agents",
    )

filtered = [
    t for t in TEMPLATES
    if t.category in selected_categories and t.agent in selected_agents
]

st.caption(f"Showing {len(filtered)} of {total_templates} templates")
st.divider()

for template in filtered:
    agent_label = AGENT_LABELS.get(template.agent, template.agent)
    expander_title = f"{template.category} — {agent_label}"
    with st.expander(expander_title):
        st.markdown(f"*{template.description}*")
        st.code(template.prompt_text, language=None)
