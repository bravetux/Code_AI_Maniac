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

import streamlit as st
from db.queries.presets import list_presets
from config.settings import get_settings, ALL_AGENTS
from config.prompt_templates import TEMPLATE_CATEGORIES

# Flat lookup: agent_key → display label (used by other modules)
ALL_FEATURES: dict[str, str] = {
    "bug_analysis":         "Bug Analysis",
    "static_analysis":      "Static Analysis",
    "code_complexity":      "Code Complexity",
    "duplication_detection": "Duplication Detection",
    "type_safety":          "Type Safety",
    "code_flow":            "Code Flow",
    "requirement":          "Requirement Design",
    "code_design":          "Code Design",
    "architecture_mapper":  "Architecture Mapper",
    "mermaid":              "Mermaid Diagram",
    "performance_analysis": "Performance Analysis",
    "refactoring_advisor":  "Refactoring Advisor",
    "test_coverage":        "Test Coverage",
    "c_test_generator":     "C Test Generator",
    "change_impact":        "Change Impact",
    "license_compliance":   "License Compliance",
    "api_doc_generator":    "API Doc Generator",
    "doxygen":              "Doxygen Docs",
    "comment_generator":    "PR Comment Generator",
    "commit_analysis":      "Commit Analysis",
    # ── Phase 5 ─────────────────────────────────────────────────────────
    "unit_test_generator":  "Unit Test Generator (multi-lang)",
    "story_test_generator": "Story → Test Cases",
    "gherkin_generator":    "BDD / Gherkin Generator",
    "test_data_generator":  "Test Data Generator",
    "dead_code_detector":   "Dead Code Detector",
    "api_contract_checker": "API Contract Checker",
    "openapi_generator":    "OpenAPI Generator",
    # ── Phase 6 — Wave 6A ──────────────────────────────────────────────
    "api_test_generator":    "API Test Generator (OpenAPI)",
    "perf_test_generator":   "Perf/Load Test Generator",
    "traceability_matrix":   "Traceability Matrix + Gaps",
    # ── Phase 6 — Wave 6B ──────────────────────────────────────────────
    "self_healing_agent":   "Self-Healing Test Agent (F9)",
    "sonar_fix_agent":      "SonarQube Fix Automation (F11)",
    "sql_generator":        "NL → SQL Generator (F14)",
    "auto_fix_agent":       "Auto-Fix Patch Generator (F15)",
}

# Grouped categories for sidebar display
FEATURE_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("Code Quality & Metrics", [
        ("bug_analysis",         "Bug Analysis"),
        ("static_analysis",      "Static Analysis"),
        ("code_complexity",      "Code Complexity"),
        ("duplication_detection", "Duplication Detection"),
        ("type_safety",          "Type Safety"),
    ]),
    ("Code Understanding", [
        ("code_flow",            "Code Flow"),
        ("requirement",          "Requirement Design"),
        ("code_design",          "Code Design"),
        ("architecture_mapper",  "Architecture Mapper"),
        ("mermaid",              "Mermaid Diagram"),
        ("doxygen",              "Doxygen Docs"),
    ]),
    ("Performance & Optimization", [
        ("performance_analysis", "Performance Analysis"),
        ("refactoring_advisor",  "Refactoring Advisor"),
    ]),
    ("Testing & Maintenance", [
        ("test_coverage",        "Test Coverage"),
        ("c_test_generator",     "C Test Generator"),
        ("unit_test_generator",  "Unit Test Generator (multi-lang)"),
        ("story_test_generator", "Story → Test Cases"),
        ("gherkin_generator",    "BDD / Gherkin Generator"),
        ("test_data_generator",  "Test Data Generator"),
        ("dead_code_detector",   "Dead Code Detector"),
        ("api_test_generator",   "API Test Generator (OpenAPI)"),
        ("perf_test_generator",  "Perf/Load Test Generator"),
        ("change_impact",        "Change Impact"),
    ]),
    ("Code Generation & Fixes", [
        ("self_healing_agent",   "Self-Healing Test Agent (F9)"),
        ("sonar_fix_agent",      "SonarQube Fix Automation (F11)"),
        ("sql_generator",        "NL → SQL Generator (F14)"),
        ("auto_fix_agent",       "Auto-Fix Patch Generator (F15)"),
    ]),
    ("Security & Compliance", [
        ("license_compliance",   "License Compliance"),
    ]),
    ("Documentation & Review", [
        ("api_doc_generator",    "API Doc Generator"),
        ("openapi_generator",    "OpenAPI Generator"),
        ("api_contract_checker", "API Contract Checker"),
        ("traceability_matrix",  "Traceability Matrix + Gaps"),
        ("comment_generator",    "PR Comment Generator"),
    ]),
]

# Hover tooltips for each feature checkbox
FEATURE_HELP: dict[str, str] = {
    "bug_analysis":         "Finds bugs, security issues, and logic errors with severity, root cause, runtime impact, and concrete fix suggestions.",
    "static_analysis":      "Two-layer analysis: flake8/ESLint linting + LLM semantic scan for design smells, security anti-patterns, and performance issues.",
    "code_complexity":      "Cyclomatic and cognitive complexity metrics, maintainability index, per-function breakdown, and hotspot identification.",
    "duplication_detection": "Detects exact and near-duplicate code blocks, DRY violations, and suggests extractions with before/after code.",
    "type_safety":          "Audits type hint coverage, flags missing annotations and type issues, suggests advanced typing patterns.",
    "code_flow":            "Generates a technical wiki-style execution-flow narrative documenting entry points, data transformations, and control flow.",
    "requirement":          "Reverse-engineers functional and non-functional requirements from code in REQ-NNN format with source line references.",
    "code_design":          "3-turn principal-architect design review producing a 9-section design document with API, dependencies, and improvement roadmap.",
    "architecture_mapper":  "Maps module dependencies, import/export analysis, coupling metrics, layer violations, and generates a Mermaid component diagram.",
    "mermaid":              "Generates flowchart, sequence, or class diagrams as valid Mermaid syntax.",
    "performance_analysis": "Big-O time and space complexity per function, N+1 query detection, caching opportunities, and scalability assessment.",
    "refactoring_advisor":  "Identifies code smells (God Class, Feature Envy, Long Method, etc.) and recommends Fowler-catalogue refactorings with before/after code.",
    "test_coverage":        "Analyses code structure to identify untested functions, missing edge cases, and generates test case suggestions with skeleton code.",
    "c_test_generator":     "Generates Python pytest + ctypes test files for C code: type-safe bindings, happy path, edge cases, error handling. Saved to Reports/.",
    "change_impact":        "Estimates blast radius for code modifications: public API surface, downstream dependents, change scenarios, and side effect mapping.",
    "license_compliance":   "Detects license headers and dependency licenses, checks compatibility matrix, flags copyleft obligations and missing attributions.",
    "api_doc_generator":    "Generates comprehensive API documentation: module overview, class/function reference, usage examples, and error handling.",
    "doxygen":              "Adds Doxygen comment headers to C/C++ functions and generates HTML documentation via the Doxygen tool.",
    "comment_generator":    "Produces GitHub-style PR review comments by combining bug and static analysis findings into actionable feedback.",
    "commit_analysis":      "Reviews commit history for release readiness: commit quality, synthesized changelog, risk assessment, and recommendations.",
    "unit_test_generator":  "F1 — Generates unit tests for Python, JS, TS, Java, .NET, Kotlin, Swift, ABAP, Go, Ruby, PHP with idiomatic frameworks (pytest, Jest, JUnit, xUnit, XCTest, ABAP Unit).",
    "story_test_generator": "F2 — Turns pasted user stories or Jira/ADO/Qase URLs into structured positive / negative / functional / NFR test cases.",
    "gherkin_generator":    "F3 — Produces Cucumber `.feature` files and matching Robot Framework suites from a story or requirement.",
    "test_data_generator":  "F8 — Synthesises test data rows (typical, boundary, invalid, unicode) from code or schema. CSV + JSON + SQL outputs, PII-safe.",
    "dead_code_detector":   "F17 — Heuristic + LLM dead-symbol detection with false-positive filtering for framework hooks and public APIs.",
    "api_contract_checker": "F24 — Compares an OpenAPI/Swagger spec against implemented routes; flags missing/extra endpoints and parameter mismatches.",
    "openapi_generator":    "F37 — Generates an OpenAPI 3.1 spec either FROM implementation code OR FROM a requirements narrative.",
    "api_test_generator":    "F5 — Generates API tests from an OpenAPI/Swagger spec. Framework picked by sidebar language (pytest+requests / REST Assured / xUnit / supertest). Always emits a Postman collection as a second artifact.",
    "perf_test_generator":   "F6 — Generates a JMeter .jmx or Gatling Simulation.scala from an OpenAPI spec or user story. Framework picked by sidebar language (java/scala → Gatling, else JMeter).",
    "traceability_matrix":   "F10 — Cross-references acceptance criteria ↔ tests ↔ code coverage. Emits CSV matrix + gap report. Auto-includes F5/F6 outputs from the same run.",
    "self_healing_agent":    "F9 — Rewrites UI test scripts (Selenium/Playwright/Cypress) when selectors break due to DOM changes. Reads current DOM via __page_html__ prefix or sibling dom.html, emits a unified diff.",
    "sonar_fix_agent":       "F11 — Ingests SonarQube issues and writes PR-ready patches. Accepts API fetch (SONAR_URL env), JSON export as source, or __sonar_issues__ prefix. Top-N issue cap (default 50).",
    "sql_generator":         "F14 — NL → SQL / stored-procedure generator. Schema-aware (DDL source or __db_schema__ prefix) and PostgreSQL-RLS-aware. Pass the NL request via __prompt__ prefix.",
    "auto_fix_agent":        "F15 — Auto-fix / patch generator. Consumes Bug Analysis + Refactoring Advisor findings (auto-scanned from same Reports/<ts>/ or via __findings__ prefix) and emits a PR-ready diff.",
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
    specify_lang = st.toggle(
        "Specify language",
        value=bool(st.session_state.get("sidebar_language", "")),
        key="sidebar_specify_language",
        help="Off — language is auto-detected from the file extension.  "
             "On — enter the language name explicitly.",
    )
    if specify_lang:
        if "sidebar_language" not in st.session_state:
            st.session_state["sidebar_language"] = ""
        language = st.text_input(
            "Language",
            key="sidebar_language",
            placeholder="e.g. Python, JavaScript, Java…",
        )
    else:
        # Clear any previously set language when switching back to auto-detect
        st.session_state["sidebar_language"] = ""
        language = ""
        st.caption("Language will be auto-detected from the file extension.")

    selected = []
    with st.expander("Features", expanded=True):
        # Select / Deselect all
        all_keys = [k for _, feats in FEATURE_GROUPS for k, _ in feats if k in active_features]
        col1, col2 = st.columns(2)
        if col1.button("Select All", key="feature_select_all_btn", use_container_width=True):
            for k in all_keys:
                st.session_state[f"feature_{k}"] = True
            st.rerun()
        if col2.button("Clear All", key="feature_clear_all_btn", use_container_width=True):
            for k in all_keys:
                st.session_state[f"feature_{k}"] = False
            st.rerun()

        for group_name, features in FEATURE_GROUPS:
            # Filter to only enabled agents in this group
            group_active = [(k, lbl) for k, lbl in features if k in active_features]
            if not group_active:
                continue
            st.caption(f"**{group_name}**")
            for key, label in group_active:
                if st.checkbox(label, key=f"feature_{key}",
                               help=FEATURE_HELP.get(key)):
                    selected.append(key)

    # F10 — prefix-convention intake helper (only when Traceability Matrix is selected)
    if "traceability_matrix" in selected:
        with st.expander("Traceability Matrix — inputs", expanded=True):
            f10_stories = st.text_area(
                "Stories file path OR pasted text OR Jira/ADO/Qase URL",
                key="f10_stories", height=80,
                help="Leave blank to fall back to the source file.",
            )
            f10_tests_dir = st.text_input(
                "Tests folder path", key="f10_tests_dir",
                placeholder="e.g. tests/",
            )
            f10_src_dir = st.text_input(
                "Code folder path (optional — enables coverage)",
                key="f10_src_dir", placeholder="e.g. src/",
            )
            f10_prefixes = []
            if f10_stories:   f10_prefixes.append(f"__stories__\n{f10_stories}")
            if f10_tests_dir: f10_prefixes.append(f"__tests_dir__={f10_tests_dir}")
            if f10_src_dir:   f10_prefixes.append(f"__src_dir__={f10_src_dir}")
            if f10_prefixes:
                st.session_state["f10_prefix_block"] = "\n".join(f10_prefixes)
            else:
                st.session_state.pop("f10_prefix_block", None)

    mermaid_type = "flowchart"
    if "mermaid" in selected:
        mermaid_type = st.selectbox("Mermaid diagram type", MERMAID_TYPES,
                                    key="sidebar_mermaid_type")

    custom_prompt = ""
    extra = ""
    with st.expander("Advanced / Fine-tune"):
        # Built-in enhanced templates
        template_options = ["None"] + TEMPLATE_CATEGORIES
        chosen_template = st.selectbox(
            "Enhanced Template",
            template_options,
            key="sidebar_enhanced_template",
            help="Built-in expert prompt templates that enhance analysis depth and quality.",
        )
        st.caption({
            "Deep Analysis": "Multi-pass chain-of-thought with root-cause tracing",
            "Security Focused": "STRIDE + OWASP Top 10 threat modelling",
            "Architecture Reverse Engineering": "Pattern recognition and design archaeology",
            "Quick Scan": "Rapid top-5 findings with traffic-light rating",
            "Report Generator": "Formal publication-quality audit reports",
            "Language Expert": "Auto-selected language-family-specific analysis",
            "Performance Deep Dive": "Algorithmic complexity, memory, I/O, caching analysis",
            "Compliance: SOC 2": "Trust Service Criteria compliance mapping",
            "Compliance: GDPR": "Data protection and privacy regulation analysis",
            "Compliance: PCI-DSS": "Payment card data security standard checks",
            "Compliance: HIPAA": "Healthcare data protection compliance",
            "Compliance: ISO 27001": "Information security management controls",
            "Compliance: Generic Audit": "Framework-agnostic compliance analysis",
        }.get(chosen_template, ""))

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

    # Merge F10 prefix block into custom_prompt if present.
    # Wrap with _APPEND_PREFIX so sibling agents keep their base system
    # prompt intact (the orchestrator fans out one custom_prompt across
    # every selected feature; without the marker, resolve_prompt
    # interprets the F10 block as a full overwrite).
    f10_block = st.session_state.get("f10_prefix_block", "")
    if f10_block:
        from agents._bedrock import _APPEND_PREFIX
        if custom_prompt.startswith(_APPEND_PREFIX):
            body = custom_prompt[len(_APPEND_PREFIX):]
            custom_prompt = f"{_APPEND_PREFIX}{f10_block}\n\n{body}"
        elif custom_prompt:
            custom_prompt = f"{_APPEND_PREFIX}{f10_block}\n\n{custom_prompt}"
        else:
            custom_prompt = f"{_APPEND_PREFIX}{f10_block}"

    return {
        "features": selected,
        "language": language,
        "custom_prompt": custom_prompt if custom_prompt else None,
        "mermaid_type": mermaid_type,
        "template_category": chosen_template if chosen_template != "None" else None,
    }
