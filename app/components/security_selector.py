"""Sidebar Security Testing section — separate from code analysis features."""

import streamlit as st
from config.settings import get_settings, ALL_AGENTS

SECURITY_FEATURES: dict[str, str] = {
    "secret_scan":          "Secret Scan",
    "dependency_analysis":  "Dependency Analysis",
    "threat_model":         "Threat Model",
}

THREAT_MODEL_MODES = ["Formal (STRIDE)", "Attacker Narrative"]
_MODE_MAP = {"Formal (STRIDE)": "formal", "Attacker Narrative": "attacker"}


def render_security_selector() -> dict:
    """Render security testing checkboxes and options.

    Returns dict with: security_features, threat_model_mode
    """
    s = get_settings()
    enabled = s.enabled_agent_set

    active_security = {k: v for k, v in SECURITY_FEATURES.items() if k in enabled}
    if not active_security:
        return {"security_features": [], "threat_model_mode": "formal"}

    st.divider()
    selected = []
    threat_model_mode = "formal"
    with st.expander("Security Testing", expanded=True):
        for key, label in active_security.items():
            if st.checkbox(label, key=f"security_{key}"):
                selected.append(key)

        if "threat_model" in selected:
            mode_label = st.selectbox("Threat model mode", THREAT_MODEL_MODES,
                                      key="sidebar_threat_model_mode")
            threat_model_mode = _MODE_MAP.get(mode_label, "formal")

    return {
        "security_features": selected,
        "threat_model_mode": threat_model_mode,
    }
