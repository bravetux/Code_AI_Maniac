"""Security Testing results — separate tab group below analysis results."""

import json
import streamlit as st

SECURITY_LABELS = {
    "secret_scan":         "Secret Scan",
    "dependency_analysis": "Dependency Analysis",
    "threat_model":        "Threat Model",
}

_SEVERITY_ICON = {"critical": "\U0001f534", "major": "\U0001f7e0", "minor": "\U0001f7e1"}
_RISK_ICON = {"high": "\U0001f534", "medium": "\U0001f7e0", "low": "\U0001f7e2"}


def render_preflight_banner(results: dict) -> None:
    """Show Phase 0 pre-flight secret scan warning banner."""
    preflight = results.get("secret_scan_preflight")
    if not preflight:
        return
    secrets = preflight.get("secrets_found", [])
    action = preflight.get("action_taken", "warn")
    if not secrets:
        return
    if action == "block":
        st.error(f"**Security Gate: BLOCKED** — {len(secrets)} secret(s) detected. "
                 "Analysis halted to prevent credential exposure. Remove secrets and resubmit.")
    elif action == "redact":
        st.warning(f"**Security Gate: REDACTED** — {len(secrets)} secret(s) detected and redacted before analysis.")
    else:
        st.warning(f"**Security Gate: WARNING** — {len(secrets)} secret(s) detected in submitted code.")
    with st.expander(f"Pre-flight findings ({len(secrets)})"):
        for s in secrets:
            icon = _SEVERITY_ICON.get("critical" if s["confidence"] == "high" else "major", "")
            st.markdown(f"{icon} **Line {s['line']}** [{s['type']}] — `{s['match']}`")


def render_security_results(results: dict) -> None:
    """Render security testing result tabs."""
    features = [f for f in SECURITY_LABELS if f in results]
    if not features:
        return
    st.divider()
    st.subheader("Security Testing")
    tabs = st.tabs([SECURITY_LABELS[f] for f in features])
    for tab, feature in zip(tabs, features):
        with tab:
            result = results[feature]
            if not isinstance(result, dict):
                st.json(result)
                continue
            if "error" in result:
                st.error(result["error"])
                continue
            c1, c2, _ = st.columns([1, 1, 6])
            c1.download_button("\u2b07 JSON", data=json.dumps(result, indent=2, ensure_ascii=False),
                               file_name=f"{feature}_result.json", mime="application/json", key=f"dl_json_{feature}")
            c2.download_button("\u2b07 MD", data=_to_markdown(feature, result),
                               file_name=f"{feature}_result.md", mime="text/markdown", key=f"dl_md_{feature}")
            st.divider()
            if feature == "secret_scan":
                _render_secret_scan(result)
            elif feature == "dependency_analysis":
                _render_dependency_analysis(result)
            elif feature == "threat_model":
                _render_threat_model(result)


def _render_secret_scan(result: dict) -> None:
    secrets = result.get("secrets", [])
    validations = result.get("phase0_validation", [])
    narrative = result.get("narrative", "")
    if narrative:
        with st.container(border=True):
            st.markdown("**Assessment**")
            st.markdown(narrative)
    if not secrets and not validations:
        st.success("No additional secrets found.")
        return
    if result.get("summary"):
        st.caption(result["summary"])
    critical = [s for s in secrets if s.get("severity") == "critical"]
    major = [s for s in secrets if s.get("severity") == "major"]
    minor = [s for s in secrets if s.get("severity") == "minor"]
    for group, label in [(critical, "Critical"), (major, "Major"), (minor, "Minor")]:
        if not group:
            continue
        st.subheader(f"{_SEVERITY_ICON.get(label.lower(), '')} {label} ({len(group)})")
        for s in group:
            with st.expander(f"Line {s.get('line', '?')} — {s.get('type', '')}"):
                st.markdown(s.get("description", ""))
                if s.get("evidence"):
                    st.code(s["evidence"])
                if s.get("recommendation"):
                    st.markdown(f"**Recommendation:** {s['recommendation']}")
                fp = s.get("false_positive_risk", "")
                if fp:
                    st.caption(f"False positive risk: {fp}")
    if validations:
        st.subheader("Phase 0 Validation")
        for v in validations:
            icon = "\u2705" if v.get("verdict") == "confirmed" else "\u274c"
            st.markdown(f"{icon} Line {v.get('line', '?')} [{v.get('phase0_type', '')}] — "
                        f"**{v.get('verdict', '')}**: {v.get('reason', '')}")


def _render_dependency_analysis(result: dict) -> None:
    deps = result.get("dependencies", [])
    risk_summary = result.get("risk_summary", "")
    remediation = result.get("remediation", "")
    if result.get("summary"):
        st.caption(result["summary"])
    if risk_summary:
        with st.container(border=True):
            st.markdown("**Risk Summary**")
            st.markdown(risk_summary)
    if not deps:
        st.info("No dependencies found.")
        return
    vuln_deps = [d for d in deps if d.get("vulnerabilities")]
    safe_deps = [d for d in deps if not d.get("vulnerabilities")]
    if vuln_deps:
        st.subheader(f"\U0001f6a8 Vulnerable ({len(vuln_deps)})")
        for d in vuln_deps:
            with st.expander(f"{d['package']} {d.get('version', '?')} — {len(d['vulnerabilities'])} CVE(s)"):
                for v in d["vulnerabilities"]:
                    icon = _SEVERITY_ICON.get(v.get("severity", "major"), "")
                    st.markdown(f"{icon} **{v.get('cve_id', '')}** [{v.get('severity', '')}] — {v.get('summary', '')}")
                    if v.get("fixed_in"):
                        st.markdown(f"Fixed in: `{v['fixed_in']}`")
                    st.caption(f"Source: {v.get('source', '')}")
    if safe_deps:
        with st.expander(f"\u2705 No known vulnerabilities ({len(safe_deps)})"):
            for d in safe_deps:
                st.markdown(f"- {d['package']} {d.get('version', '?')} ({d.get('ecosystem', '')})")
    if remediation:
        with st.container(border=True):
            st.markdown("**Remediation Plan**")
            st.markdown(remediation)


def _render_threat_model(result: dict) -> None:
    mode = result.get("mode", "formal")
    if result.get("summary"):
        st.caption(result["summary"])
    if mode == "formal":
        _render_threat_model_formal(result)
    else:
        _render_threat_model_attacker(result)


def _render_threat_model_formal(result: dict) -> None:
    boundaries = result.get("trust_boundaries", [])
    if boundaries:
        st.subheader("Trust Boundaries")
        for tb in boundaries:
            st.markdown(f"**{tb.get('id', '')}**: {tb.get('description', '')}")
            if tb.get("components"):
                st.caption("Components: " + ", ".join(f"`{c}`" for c in tb["components"]))
    surface = result.get("attack_surface", [])
    if surface:
        st.subheader("Attack Surface")
        for entry in surface:
            exposure_icon = _RISK_ICON.get("high" if entry.get("exposure") == "public" else "low", "")
            st.markdown(f"{exposure_icon} **{entry.get('entry_point', '')}** [{entry.get('exposure', '')}] — {entry.get('data_handled', '')}")
    threats = result.get("stride_analysis", [])
    if threats:
        st.subheader(f"STRIDE Threats ({len(threats)})")
        for t in threats:
            icon = _SEVERITY_ICON.get(t.get("risk_score", "minor"), "")
            with st.expander(f"{icon} {t.get('id', '')} [{t.get('category', '')}] — {t.get('threat', '')[:80]}"):
                st.markdown(f"**Asset:** {t.get('asset', '')}")
                st.markdown(f"**Attack vector:** {t.get('attack_vector', '')}")
                st.markdown(f"**Likelihood:** {t.get('likelihood', '')} | **Impact:** {t.get('impact', '')}")
                if t.get("existing_mitigation"):
                    st.markdown(f"**Existing mitigation:** {t['existing_mitigation']}")
                st.markdown(f"**Recommended:** {t.get('recommended_mitigation', '')}")
                if t.get("related_findings"):
                    st.caption("Related: " + ", ".join(t["related_findings"]))
    mermaid_src = result.get("data_flow_mermaid", "")
    if mermaid_src:
        st.subheader("Data Flow Diagram")
        from app.components.mermaid_renderer import render_mermaid
        render_mermaid(mermaid_src)


def _render_threat_model_attacker(result: dict) -> None:
    exec_summary = result.get("executive_summary", "")
    if exec_summary:
        with st.container(border=True):
            st.markdown("**Executive Summary**")
            st.markdown(exec_summary)
    scenarios = result.get("attack_scenarios", [])
    ranking = result.get("priority_ranking", [])
    if not scenarios:
        st.success("No attack scenarios identified.")
        return
    if ranking:
        rank_map = {sid: i for i, sid in enumerate(ranking)}
        scenarios = sorted(scenarios, key=lambda s: rank_map.get(s.get("id", ""), 999))
    st.subheader(f"Attack Scenarios ({len(scenarios)})")
    for s in scenarios:
        icon = _SEVERITY_ICON.get(s.get("risk_score", "minor"), "")
        with st.expander(f"{icon} {s.get('id', '')} — {s.get('title', '')}"):
            st.markdown(f"**STRIDE:** {s.get('stride_category', '')}")
            st.markdown(f"**Prerequisites:** {s.get('prerequisites', '')}")
            st.markdown(s.get("narrative", ""))
            st.markdown(f"**Impact:** {s.get('impact', '')}")
            if s.get("proof_of_concept"):
                st.markdown("**Proof of Concept:**")
                st.code(s["proof_of_concept"])
            st.markdown(f"**Mitigation:** {s.get('mitigation', '')}")
            if s.get("related_findings"):
                st.caption("Related: " + ", ".join(s["related_findings"]))


# ── Markdown export ──────────────────────────────────────────────────────────

def _to_markdown(feature: str, result: dict) -> str:
    label = SECURITY_LABELS.get(feature, feature)
    lines = [f"# {label}", ""]
    if feature == "secret_scan":
        lines.append(result.get("summary", ""))
        for s in result.get("secrets", []):
            lines += [f"## Line {s.get('line', '?')} — {s.get('type', '')} [{s.get('severity', '')}]",
                      s.get("description", ""), f"**Recommendation:** {s.get('recommendation', '')}", ""]
    elif feature == "dependency_analysis":
        lines.append(result.get("summary", ""))
        if result.get("risk_summary"):
            lines += ["", "## Risk Summary", result["risk_summary"], ""]
        for d in result.get("dependencies", []):
            if d.get("vulnerabilities"):
                lines.append(f"### {d['package']} {d.get('version', '?')}")
                for v in d["vulnerabilities"]:
                    lines.append(f"- **{v.get('cve_id', '')}** [{v.get('severity', '')}]: {v.get('summary', '')}")
                lines.append("")
        if result.get("remediation"):
            lines += ["## Remediation", result["remediation"]]
    elif feature == "threat_model":
        lines.append(result.get("summary", ""))
        if result.get("mode") == "formal":
            for t in result.get("stride_analysis", []):
                lines += [f"## {t.get('id', '')} [{t.get('category', '')}] — {t.get('threat', '')}",
                          f"**Risk:** {t.get('risk_score', '')} | **Likelihood:** {t.get('likelihood', '')} | **Impact:** {t.get('impact', '')}",
                          f"**Mitigation:** {t.get('recommended_mitigation', '')}", ""]
            if result.get("data_flow_mermaid"):
                lines += ["## Data Flow", "```mermaid", result["data_flow_mermaid"], "```"]
        else:
            if result.get("executive_summary"):
                lines += ["## Executive Summary", result["executive_summary"], ""]
            for s in result.get("attack_scenarios", []):
                lines += [f"## {s.get('id', '')} — {s.get('title', '')}",
                          f"**Risk:** {s.get('risk_score', '')}", s.get("narrative", ""),
                          f"**Mitigation:** {s.get('mitigation', '')}", ""]
    return "\n".join(lines)
