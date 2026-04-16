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
