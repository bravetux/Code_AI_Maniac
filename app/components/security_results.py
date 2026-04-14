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


# ── Helper: extract analysed files from multi-file or single results ─────────

def _get_analysed_files(result: dict) -> list[str]:
    """Return list of file paths analysed for this feature."""
    if result.get("_multi_file"):
        return list(result.get("files", {}).keys())
    # For single-file results, no explicit file list — caller shows from job context
    return []


# ── Summary table builders ───────────────────────────────────────────────────

def _secret_scan_summary_table(result: dict) -> list[dict]:
    """Build summary table rows for secret scan."""
    rows = []
    for s in result.get("secrets", []):
        rows.append({
            "Line": s.get("line", "?"),
            "Type": s.get("type", "").replace("_", " ").title(),
            "Severity": s.get("severity", "").title(),
            "Description": s.get("description", "")[:120],
            "FP Risk": s.get("false_positive_risk", "").title(),
        })
    for v in result.get("phase0_validation", []):
        rows.append({
            "Line": v.get("line", "?"),
            "Type": f"Pre-flight: {v.get('phase0_type', '')}",
            "Severity": "Confirmed" if v.get("verdict") == "confirmed" else "Dismissed",
            "Description": v.get("reason", "")[:120],
            "FP Risk": "",
        })
    return rows


def _dependency_summary_table(result: dict) -> list[dict]:
    """Build summary table rows for dependency analysis."""
    rows = []
    for d in result.get("dependencies", []):
        vuln_count = len(d.get("vulnerabilities", []))
        if vuln_count > 0:
            for v in d["vulnerabilities"]:
                rows.append({
                    "Package": d.get("package", ""),
                    "Version": d.get("version", "?"),
                    "CVE": v.get("cve_id", ""),
                    "Severity": v.get("severity", "").title(),
                    "Fixed In": v.get("fixed_in", "—"),
                    "Source": v.get("source", ""),
                })
        else:
            rows.append({
                "Package": d.get("package", ""),
                "Version": d.get("version", "?"),
                "CVE": "—",
                "Severity": "Clean",
                "Fixed In": "—",
                "Source": "—",
            })
    return rows


def _threat_model_summary_table(result: dict) -> list[dict]:
    """Build summary table rows for threat model."""
    rows = []
    mode = result.get("mode", "formal")
    if mode == "formal":
        for t in result.get("stride_analysis", []):
            rows.append({
                "ID": t.get("id", ""),
                "Category": t.get("category", ""),
                "Threat": t.get("threat", "")[:100],
                "Risk": t.get("risk_score", "").title(),
                "Likelihood": t.get("likelihood", "").title(),
                "Impact": t.get("impact", "").title(),
            })
    else:
        for s in result.get("attack_scenarios", []):
            rows.append({
                "ID": s.get("id", ""),
                "Title": s.get("title", ""),
                "STRIDE": s.get("stride_category", ""),
                "Risk": s.get("risk_score", "").title(),
                "Impact": s.get("impact", "")[:80],
            })
    return rows


# ── Main renderer ────────────────────────────────────────────────────────────

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

            # ── Download buttons ─────────────────────────────────────
            c1, c2, _ = st.columns([1, 1, 6])
            c1.download_button("\u2b07 JSON", data=json.dumps(result, indent=2, ensure_ascii=False),
                               file_name=f"{feature}_result.json", mime="application/json", key=f"sec_dl_json_{feature}")
            c2.download_button("\u2b07 MD", data=_to_markdown(feature, result),
                               file_name=f"{feature}_result.md", mime="text/markdown", key=f"sec_dl_md_{feature}")

            # ── Summary table ────────────────────────────────────────
            if feature == "secret_scan":
                _render_secret_scan(result)
            elif feature == "dependency_analysis":
                _render_dependency_analysis(result)
            elif feature == "threat_model":
                _render_threat_model(result)


# ── Secret Scan tab ──────────────────────────────────────────────────────────

def _render_secret_scan(result: dict) -> None:
    secrets = result.get("secrets", [])
    validations = result.get("phase0_validation", [])
    narrative = result.get("narrative", "")

    # ── Summary metrics ──────────────────────────────────────────
    total = len(secrets)
    confirmed = sum(1 for v in validations if v.get("verdict") == "confirmed")
    dismissed = sum(1 for v in validations if v.get("verdict") == "false_positive")
    critical = len([s for s in secrets if s.get("severity") == "critical"])
    major = len([s for s in secrets if s.get("severity") == "major"])
    minor = len([s for s in secrets if s.get("severity") == "minor"])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Issues", total)
    m2.metric("Critical", critical)
    m3.metric("Major", major)
    m4.metric("Minor", minor)
    m5.metric("Pre-flight Confirmed", confirmed)

    # ── Summary table ────────────────────────────────────────────
    table_rows = _secret_scan_summary_table(result)
    if table_rows:
        st.markdown("")
        st.markdown("**Issues Summary**")
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.divider()

    # ── Narrative ────────────────────────────────────────────────
    if narrative:
        with st.container(border=True):
            st.markdown("**Assessment**")
            st.markdown(narrative)

    if not secrets and not validations:
        st.success("No additional secrets found.")
        return

    # ── Detailed findings ────────────────────────────────────────
    st.markdown("**Detailed Findings**")
    critical_list = [s for s in secrets if s.get("severity") == "critical"]
    major_list = [s for s in secrets if s.get("severity") == "major"]
    minor_list = [s for s in secrets if s.get("severity") == "minor"]

    for group, label in [(critical_list, "Critical"), (major_list, "Major"), (minor_list, "Minor")]:
        if not group:
            continue
        st.markdown(f"#### {_SEVERITY_ICON.get(label.lower(), '')} {label} ({len(group)})")
        for s in group:
            with st.expander(f"Line {s.get('line', '?')} — {s.get('type', '').replace('_', ' ').title()}"):
                st.markdown(s.get("description", ""))
                if s.get("evidence"):
                    st.markdown("**Evidence:**")
                    st.code(s["evidence"])
                if s.get("recommendation"):
                    st.markdown(f"**Recommendation:** {s['recommendation']}")
                fp = s.get("false_positive_risk", "")
                if fp:
                    st.caption(f"False positive risk: {fp}")

    # ── Phase 0 validation ───────────────────────────────────────
    if validations:
        st.markdown("")
        st.markdown("**Phase 0 Pre-flight Validation**")
        for v in validations:
            icon = "\u2705" if v.get("verdict") == "confirmed" else "\u274c"
            with st.container(border=True):
                st.markdown(
                    f"{icon} **Line {v.get('line', '?')}** — "
                    f"`{v.get('phase0_type', '')}` — **{v.get('verdict', '').title()}**"
                )
                st.markdown(v.get("reason", ""))


# ── Dependency Analysis tab ──────────────────────────────────────────────────

def _render_dependency_analysis(result: dict) -> None:
    deps = result.get("dependencies", [])
    risk_summary = result.get("risk_summary", "")
    remediation = result.get("remediation", "")

    # ── Summary metrics ──────────────────────────────────────────
    total_deps = len(deps)
    vuln_count = sum(1 for d in deps if d.get("vulnerabilities"))
    total_cves = sum(len(d.get("vulnerabilities", [])) for d in deps)
    safe_count = total_deps - vuln_count

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Dependencies", total_deps)
    m2.metric("Vulnerable", vuln_count)
    m3.metric("Total CVEs", total_cves)
    m4.metric("Clean", safe_count)

    # ── Summary table ────────────────────────────────────────────
    table_rows = _dependency_summary_table(result)
    if table_rows:
        st.markdown("")
        st.markdown("**Dependencies Overview**")
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.divider()

    # ── Risk summary ─────────────────────────────────────────────
    if risk_summary:
        with st.container(border=True):
            st.markdown("**Risk Summary**")
            st.markdown(risk_summary)

    if not deps:
        st.info("No dependencies found.")
        return

    # ── Detailed findings ────────────────────────────────────────
    vuln_deps = [d for d in deps if d.get("vulnerabilities")]
    safe_deps = [d for d in deps if not d.get("vulnerabilities")]

    if vuln_deps:
        st.markdown("**Vulnerable Packages**")
        for d in vuln_deps:
            with st.expander(f"\U0001f6a8 {d['package']} {d.get('version', '?')} — {len(d['vulnerabilities'])} CVE(s)"):
                for v in d["vulnerabilities"]:
                    icon = _SEVERITY_ICON.get(v.get("severity", "major"), "")
                    with st.container(border=True):
                        st.markdown(
                            f"{icon} **{v.get('cve_id', '')}** "
                            f"[{v.get('severity', '').title()}]"
                        )
                        st.markdown(v.get("summary", ""))
                        col_a, col_b = st.columns(2)
                        if v.get("fixed_in"):
                            col_a.markdown(f"**Fixed in:** `{v['fixed_in']}`")
                        col_b.caption(f"Source: {v.get('source', '')}")

    if safe_deps:
        with st.expander(f"\u2705 No known vulnerabilities ({len(safe_deps)})"):
            for d in safe_deps:
                st.markdown(f"- `{d['package']}` {d.get('version', '?')} ({d.get('ecosystem', '')})")

    # ── Remediation ──────────────────────────────────────────────
    if remediation:
        st.markdown("")
        with st.container(border=True):
            st.markdown("**Remediation Plan**")
            st.markdown(remediation)


# ── Threat Model tab ─────────────────────────────────────────────────────────

def _render_threat_model(result: dict) -> None:
    mode = result.get("mode", "formal")

    if mode == "formal":
        _render_threat_model_formal(result)
    else:
        _render_threat_model_attacker(result)


def _render_threat_model_formal(result: dict) -> None:
    threats = result.get("stride_analysis", [])
    boundaries = result.get("trust_boundaries", [])
    surface = result.get("attack_surface", [])

    # ── Summary metrics ──────────────────────────────────────────
    total = len(threats)
    crit = len([t for t in threats if t.get("risk_score") == "critical"])
    maj = len([t for t in threats if t.get("risk_score") == "major"])
    mn = len([t for t in threats if t.get("risk_score") == "minor"])

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Threats", total)
    m2.metric("Critical", crit)
    m3.metric("Major", maj)
    m4.metric("Minor", mn)
    m5.metric("Trust Boundaries", len(boundaries))

    # ── Summary table ────────────────────────────────────────────
    table_rows = _threat_model_summary_table(result)
    if table_rows:
        st.markdown("")
        st.markdown("**Threat Summary**")
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.divider()

    # ── Trust boundaries ─────────────────────────────────────────
    if boundaries:
        st.markdown("#### Trust Boundaries")
        for tb in boundaries:
            with st.container(border=True):
                st.markdown(f"**{tb.get('id', '')}** — {tb.get('description', '')}")
                if tb.get("components"):
                    st.markdown("Components: " + ", ".join(f"`{c}`" for c in tb["components"]))

    # ── Attack surface ───────────────────────────────────────────
    if surface:
        st.markdown("#### Attack Surface")
        surface_rows = []
        for entry in surface:
            surface_rows.append({
                "Entry Point": entry.get("entry_point", ""),
                "Exposure": entry.get("exposure", "").title(),
                "Data Handled": entry.get("data_handled", ""),
            })
        st.dataframe(surface_rows, use_container_width=True, hide_index=True)

    # ── STRIDE detailed findings ─────────────────────────────────
    if threats:
        st.markdown("")
        st.markdown("#### STRIDE Analysis — Detailed Findings")
        for t in threats:
            icon = _SEVERITY_ICON.get(t.get("risk_score", "minor"), "")
            with st.expander(
                f"{icon} {t.get('id', '')} [{t.get('category', '')}] — "
                f"{t.get('threat', '')[:80]}"
            ):
                # Info row
                col_a, col_b, col_c = st.columns(3)
                col_a.markdown(f"**Risk:** {t.get('risk_score', '').title()}")
                col_b.markdown(f"**Likelihood:** {t.get('likelihood', '').title()}")
                col_c.markdown(f"**Impact:** {t.get('impact', '').title()}")

                st.markdown("")
                st.markdown(f"**Asset:** {t.get('asset', '')}")
                st.markdown(f"**Attack Vector:** {t.get('attack_vector', '')}")

                if t.get("existing_mitigation"):
                    st.markdown(f"**Existing Mitigation:** {t['existing_mitigation']}")

                st.markdown(f"**Recommended Fix:** {t.get('recommended_mitigation', '')}")

                # Code comparison
                original = t.get("original_code", "")
                fixed = t.get("fixed_code", "")
                if original or fixed:
                    st.divider()
                    col_orig, col_fix = st.columns(2)
                    with col_orig:
                        st.markdown("**Original Code**")
                        if original:
                            st.code(original, line_numbers=True)
                        else:
                            st.caption("No original snippet provided.")
                    with col_fix:
                        st.markdown("**Fixed Code**")
                        if fixed:
                            st.code(fixed, line_numbers=True)
                        else:
                            st.caption("No fix snippet provided.")

                if t.get("related_findings"):
                    st.caption("Related: " + ", ".join(t["related_findings"]))

    # ── Data flow diagram ────────────────────────────────────────
    mermaid_src = result.get("data_flow_mermaid", "")
    if mermaid_src:
        st.markdown("")
        st.markdown("#### Data Flow Diagram")
        from app.components.mermaid_renderer import render_mermaid
        render_mermaid(mermaid_src)


def _render_threat_model_attacker(result: dict) -> None:
    scenarios = result.get("attack_scenarios", [])
    ranking = result.get("priority_ranking", [])

    # ── Summary metrics ──────────────────────────────────────────
    total = len(scenarios)
    crit = len([s for s in scenarios if s.get("risk_score") == "critical"])
    maj = len([s for s in scenarios if s.get("risk_score") == "major"])
    mn = len([s for s in scenarios if s.get("risk_score") == "minor"])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Attack Scenarios", total)
    m2.metric("Critical", crit)
    m3.metric("Major", maj)
    m4.metric("Minor", mn)

    # ── Summary table ────────────────────────────────────────────
    table_rows = _threat_model_summary_table(result)
    if table_rows:
        st.markdown("")
        st.markdown("**Scenario Summary**")
        st.dataframe(table_rows, use_container_width=True, hide_index=True)

    st.divider()

    # ── Executive summary ────────────────────────────────────────
    exec_summary = result.get("executive_summary", "")
    if exec_summary:
        with st.container(border=True):
            st.markdown("**Executive Summary**")
            st.markdown(exec_summary)

    if not scenarios:
        st.success("No attack scenarios identified.")
        return

    # Sort by priority ranking
    if ranking:
        rank_map = {sid: i for i, sid in enumerate(ranking)}
        scenarios = sorted(scenarios, key=lambda s: rank_map.get(s.get("id", ""), 999))

    # ── Detailed scenarios ───────────────────────────────────────
    st.markdown("**Attack Scenarios — Detailed Analysis**")
    for s in scenarios:
        icon = _SEVERITY_ICON.get(s.get("risk_score", "minor"), "")
        with st.expander(f"{icon} {s.get('id', '')} — {s.get('title', '')}"):
            # Info row
            col_a, col_b = st.columns(2)
            col_a.markdown(f"**STRIDE Category:** {s.get('stride_category', '')}")
            col_b.markdown(f"**Risk:** {s.get('risk_score', '').title()}")

            st.markdown("")
            st.markdown(f"**Prerequisites:** {s.get('prerequisites', '')}")

            st.markdown("")
            st.markdown("**Attack Narrative:**")
            st.markdown(s.get("narrative", ""))

            st.markdown("")
            st.markdown(f"**Impact:** {s.get('impact', '')}")

            if s.get("proof_of_concept"):
                st.markdown("")
                st.markdown("**Proof of Concept:**")
                st.code(s["proof_of_concept"])

            st.markdown("")
            st.markdown(f"**Mitigation:** {s.get('mitigation', '')}")

            # Code comparison
            original = s.get("original_code", "")
            fixed = s.get("fixed_code", "")
            if original or fixed:
                st.divider()
                col_orig, col_fix = st.columns(2)
                with col_orig:
                    st.markdown("**Original Code**")
                    if original:
                        st.code(original, line_numbers=True)
                    else:
                        st.caption("No original snippet provided.")
                with col_fix:
                    st.markdown("**Fixed Code**")
                    if fixed:
                        st.code(fixed, line_numbers=True)
                    else:
                        st.caption("No fix snippet provided.")

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
                          f"**Asset:** {t.get('asset', '')}",
                          f"**Attack Vector:** {t.get('attack_vector', '')}",
                          f"**Mitigation:** {t.get('recommended_mitigation', '')}"]
                if t.get("original_code"):
                    lines += ["", "**Original Code:**", f"```\n{t['original_code']}\n```"]
                if t.get("fixed_code"):
                    lines += ["", "**Fixed Code:**", f"```\n{t['fixed_code']}\n```"]
                lines.append("")
            if result.get("data_flow_mermaid"):
                lines += ["## Data Flow", "```mermaid", result["data_flow_mermaid"], "```"]
        else:
            if result.get("executive_summary"):
                lines += ["## Executive Summary", result["executive_summary"], ""]
            for s in result.get("attack_scenarios", []):
                lines += [f"## {s.get('id', '')} — {s.get('title', '')}",
                          f"**Risk:** {s.get('risk_score', '')} | **STRIDE:** {s.get('stride_category', '')}",
                          f"**Prerequisites:** {s.get('prerequisites', '')}",
                          "", s.get("narrative", ""), "",
                          f"**Impact:** {s.get('impact', '')}",
                          f"**Mitigation:** {s.get('mitigation', '')}"]
                if s.get("original_code"):
                    lines += ["", "**Original Code:**", f"```\n{s['original_code']}\n```"]
                if s.get("fixed_code"):
                    lines += ["", "**Fixed Code:**", f"```\n{s['fixed_code']}\n```"]
                lines.append("")
    return "\n".join(lines)
