"""Sidebar Security Testing section — separate from code analysis features."""

import streamlit as st
from config.settings import get_settings, ALL_AGENTS

SECURITY_FEATURES: dict[str, str] = {
    "secret_scan":          "Secret Scan",
    "dependency_analysis":  "Dependency Analysis",
    "threat_model":         "Threat Model",
}

SECURITY_HELP: dict[str, str] = {
    "secret_scan":         "Phase 0 regex pre-flight + Phase 3 LLM deep scan for hardcoded secrets, API keys, tokens, and credentials.",
    "dependency_analysis": "Software Composition Analysis: parses 20+ dependency file types, CVE lookup, risk assessment, and remediation plan.",
    "threat_model":        "STRIDE formal analysis or attacker-narrative penetration test using findings from all prior analysis phases.",
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
            if st.checkbox(label, key=f"security_{key}",
                           help=SECURITY_HELP.get(key)):
                selected.append(key)

        if "threat_model" in selected:
            mode_label = st.selectbox("Threat model mode", THREAT_MODEL_MODES,
                                      key="sidebar_threat_model_mode")
            threat_model_mode = _MODE_MAP.get(mode_label, "formal")

    return {
        "security_features": selected,
        "threat_model_mode": threat_model_mode,
    }
