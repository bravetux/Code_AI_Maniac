"""
Save / Load sidebar settings profiles.

A profile captures: source_type, selected features, language, custom prompt,
extra instructions, and mermaid diagram type.  Profiles are stored in DuckDB
and restored by writing to st.session_state (then calling st.rerun() so every
widget picks up the new values via its key=).
"""
import streamlit as st
from config.settings import ALL_AGENTS
from db.queries.sidebar_profiles import (
    save_profile, list_profiles, get_profile, delete_profile,
)

# Map internal source_type values ↔ radio label strings
_SOURCE_LABELS = {
    "local":  "Local File",
    "github": "GitHub",
    "gitea":  "Gitea",
}
_SOURCE_KEYS = {v: k for k, v in _SOURCE_LABELS.items()}


def render_sidebar_profile(conn) -> None:
    """
    Render the profile save/load panel.
    Call this BEFORE render_source_selector and render_feature_selector
    so that any loaded profile values are in session_state before the
    other widgets render.
    """
    profiles = list_profiles(conn)
    profile_names = [p["name"] for p in profiles]

    st.subheader("Settings Profile")

    # ── Load ──────────────────────────────────────────────────────
    if profiles:
        col_sel, col_load, col_del = st.columns([3, 1, 1])
        chosen = col_sel.selectbox(
            "Saved profiles",
            options=[""] + profile_names,
            label_visibility="collapsed",
            key="_profile_select",
        )
        if col_load.button("Load", key="_profile_load", width="stretch"):
            if chosen:
                profile = get_profile(conn, chosen)
                if profile:
                    _apply_profile(profile)
                    st.success(f"Loaded '{chosen}'.")
                    st.rerun()
            else:
                st.warning("Select a profile to load.")

        if col_del.button("Del", key="_profile_del", width="stretch",
                          type="secondary"):
            if chosen:
                target = next((p for p in profiles if p["name"] == chosen), None)
                if target:
                    delete_profile(conn, target["id"])
                    # Clear the selectbox so it doesn't reference a stale name
                    if "_profile_select" in st.session_state:
                        del st.session_state["_profile_select"]
                    st.success(f"Deleted '{chosen}'.")
                    st.rerun()
            else:
                st.warning("Select a profile to delete.")
    else:
        st.caption("No profiles saved yet.")

    # ── Save ──────────────────────────────────────────────────────
    with st.expander("Save current settings as profile"):
        new_name = st.text_input("Profile name", key="_profile_new_name",
                                 placeholder="e.g. Bug Finder, Design Suite")
        if st.button("Save", key="_profile_save", type="primary"):
            if not new_name.strip():
                st.error("Enter a profile name.")
            else:
                _save_current(conn, new_name.strip())
                st.success(
                    f"{'Updated' if new_name in profile_names else 'Saved'} "
                    f"'{new_name}'."
                )
                if "_profile_new_name" in st.session_state:
                    del st.session_state["_profile_new_name"]
                st.rerun()

    st.divider()


# ── Helpers ───────────────────────────────────────────────────────

def _apply_profile(profile: dict) -> None:
    """Write profile values into session_state; widgets pick them up on rerun."""
    # Source type radio
    src = profile.get("source_type") or ""
    st.session_state["sidebar_source_type"] = _SOURCE_LABELS.get(src, "Local File")

    # Feature checkboxes (key per agent)
    enabled_features = set(profile.get("features") or [])
    for key in ALL_AGENTS:
        st.session_state[f"feature_{key}"] = key in enabled_features

    # Language
    st.session_state["sidebar_language"] = profile.get("language") or ""

    # Mermaid type
    st.session_state["sidebar_mermaid_type"] = profile.get("mermaid_type") or "flowchart"

    # Custom prompt / extra instructions
    st.session_state["sidebar_custom_prompt"] = profile.get("custom_prompt") or ""
    st.session_state["sidebar_extra_instructions"] = profile.get("extra_instructions") or ""


def _save_current(conn, name: str) -> None:
    """Read current widget session_state and persist as a named profile."""
    # Source type: radio stores the label string; convert back to key
    source_label = st.session_state.get("sidebar_source_type", "")
    source_type = _SOURCE_KEYS.get(source_label, "local")

    # Active features from checkbox keys
    features = [k for k in ALL_AGENTS
                if st.session_state.get(f"feature_{k}", False)]

    save_profile(
        conn,
        name=name,
        source_type=source_type,
        features=features,
        language=st.session_state.get("sidebar_language", "") or None,
        custom_prompt=st.session_state.get("sidebar_custom_prompt", "") or None,
        extra_instructions=st.session_state.get("sidebar_extra_instructions", "") or None,
        mermaid_type=st.session_state.get("sidebar_mermaid_type", "flowchart"),
    )
