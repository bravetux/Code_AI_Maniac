import streamlit as st
from db.queries.presets import list_presets
from config.settings import get_settings, ALL_AGENTS

# All agents in display order with their UI labels
ALL_FEATURES: dict[str, str] = {
    "bug_analysis":      "Bug Analysis",
    "code_design":       "Code Design",
    "code_flow":         "Code Flow",
    "mermaid":           "Mermaid Diagram",
    "requirement":       "Requirement Design",
    "static_analysis":   "Static Analysis",
    "comment_generator": "PR Comment Generator",
    "commit_analysis":   "Commit Analysis",
}

MERMAID_TYPES = ["flowchart", "sequence", "class"]


def render_feature_selector(conn) -> dict:
    """
    Render feature checkboxes, language input, and fine-tune panel.
    Only shows agents that are enabled via ENABLED_AGENTS in .env.
    Returns dict with: features, language, custom_prompt, mermaid_type
    """
    s = get_settings()
    enabled = s.enabled_agent_set

    # Show a mode banner when a restricted profile is active
    if enabled != ALL_AGENTS:
        st.info(
            f"**Restricted mode** — {len(enabled)} of {len(ALL_AGENTS)} agents enabled "
            f"(`ENABLED_AGENTS` in .env)."
        )

    # Only expose enabled agents
    active_features = {k: v for k, v in ALL_FEATURES.items() if k in enabled}

    st.subheader("Language")
    extension_hint = st.session_state.get("detected_extension", "")
    language = st.text_input(
        "Language",
        value=st.session_state.get("detected_language", ""),
        placeholder="e.g. Python, JavaScript, Go, COBOL",
        help=f"Auto-detected from extension: {extension_hint}" if extension_hint else "Enter language"
    )

    st.subheader("Features")
    selected = []
    for key, label in active_features.items():
        if st.checkbox(label, key=f"feature_{key}"):
            selected.append(key)

    mermaid_type = "flowchart"
    if "mermaid" in selected:
        mermaid_type = st.selectbox("Mermaid diagram type", MERMAID_TYPES)

    custom_prompt = ""
    extra = ""
    with st.expander("Advanced / Fine-tune"):
        all_presets = list_presets(conn)
        # Only show presets whose feature is currently enabled
        presets = [p for p in all_presets if p.get("feature") in enabled]
        preset_names = ["None"] + [p["name"] for p in presets]
        chosen_preset = st.selectbox("Load preset", preset_names)

        default_prompt = ""
        if chosen_preset != "None":
            preset = next((p for p in presets if p["name"] == chosen_preset), None)
            if preset:
                default_prompt = preset.get("system_prompt", "")

        custom_prompt = st.text_area("System Prompt", value=default_prompt,
                                     height=120, placeholder="Override the default system prompt...")
        extra = st.text_input("Extra Instructions",
                              placeholder="e.g. focus on security issues only")
        if extra:
            custom_prompt = f"{custom_prompt}\n\nAdditional: {extra}".strip()

        preset_name = st.text_input("Save as preset (optional name)")
        if st.button("Save Preset") and preset_name and custom_prompt:
            for feature in selected:
                from db.queries.presets import create_preset
                create_preset(conn, name=preset_name, feature=feature,
                              system_prompt=custom_prompt, extra_instructions=extra)
            st.success(f"Preset '{preset_name}' saved.")

    return {
        "features": selected,
        "language": language,
        "custom_prompt": custom_prompt if custom_prompt else None,
        "mermaid_type": mermaid_type,
    }
