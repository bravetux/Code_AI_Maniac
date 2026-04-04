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
    # Seed the key from auto-detection only on first render
    if "sidebar_language" not in st.session_state:
        st.session_state["sidebar_language"] = st.session_state.get("detected_language", "")
    language = st.text_input(
        "Language (optional)",
        key="sidebar_language",
        placeholder="Leave blank to auto-detect from file extension / code",
        help="If left blank, language is inferred from the file extension. "
             "The model will self-detect for any extension not recognised."
    )

    st.subheader("Features")
    selected = []
    for key, label in active_features.items():
        if st.checkbox(label, key=f"feature_{key}"):
            selected.append(key)

    mermaid_type = "flowchart"
    if "mermaid" in selected:
        mermaid_type = st.selectbox("Mermaid diagram type", MERMAID_TYPES,
                                    key="sidebar_mermaid_type")

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

        # Seed keys from loaded preset; don't override what user has typed
        if default_prompt and st.session_state.get("sidebar_custom_prompt", "") == "":
            st.session_state["sidebar_custom_prompt"] = default_prompt

        prompt_mode = st.radio(
            "Prompt mode",
            ["Append to default", "Overwrite default"],
            horizontal=True,
            key="sidebar_prompt_mode",
            help=(
                "**Append** — your text is added after the built-in system prompt, "
                "enhancing it without losing its original instructions.\n\n"
                "**Overwrite** — your text replaces the built-in system prompt entirely."
            ),
        )

        custom_prompt_text = st.text_area(
            "System Prompt",
            height=120,
            placeholder=(
                "Append mode: add extra instructions to enhance the default prompt…\n"
                "Overwrite mode: replace the default prompt entirely…"
            ),
            key="sidebar_custom_prompt",
        )
        extra = st.text_input("Extra Instructions",
                              placeholder="e.g. focus on security issues only",
                              key="sidebar_extra_instructions")

        # Build custom_prompt with mode encoding; extra instructions always append
        custom_prompt = ""
        if custom_prompt_text:
            from agents._bedrock import _APPEND_PREFIX
            if prompt_mode == "Append to default":
                custom_prompt = f"{_APPEND_PREFIX}{custom_prompt_text}"
            else:
                custom_prompt = custom_prompt_text
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
