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

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import list_jobs

st.set_page_config(
    page_title="AI Code Maniac",
    page_icon="\U0001f3df",
    layout="wide",
    initial_sidebar_state="collapsed",
)

conn = get_connection()
init_schema(conn)

# ── Inject custom CSS ────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700;800&family=DM+Sans:wght@300;400;500;600;700&display=swap');

/* ── Light theme overrides ─────────────────────────────────────────────── */
section[data-testid="stMain"] {
    background: #ffffff !important;
}
header[data-testid="stHeader"] {
    background: #ffffff !important;
}

/* ── Hero text ──────────────────────────────────────────────────────────── */
.hero-badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: .68rem;
    font-weight: 500;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #0077b6;
    border: 1px solid rgba(0,119,182,.3);
    border-radius: 100px;
    padding: .35em 1.2em;
    background: rgba(0,119,182,.06);
}
.hero-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: clamp(2rem, 4.5vw, 3.4rem);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -.03em;
    color: #1a1a2e;
    margin: .8rem 0 .6rem;
}
.hero-title .acc { color: #0077b6; }
.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    line-height: 1.65;
    color: #555570;
    max-width: 620px;
}

/* ── CTA button ─────────────────────────────────────────────────────────── */
div.cta-wrap [data-testid="stBaseButton-primary"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: .95rem !important;
    letter-spacing: .05em !important;
    background: linear-gradient(135deg, #0077b6, #005a8c) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    padding: .85rem 2.6rem !important;
    box-shadow: 0 2px 12px rgba(0,119,182,.18), 0 4px 16px rgba(0,0,0,.06) !important;
    transition: all .25s ease !important;
}
div.cta-wrap [data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 20px rgba(0,119,182,.28), 0 8px 24px rgba(0,0,0,.1) !important;
}

/* ── Pipeline row ───────────────────────────────────────────────────────── */
.pipe-box {
    background: #f7f8fb;
    border: 1px solid #e2e4ec;
    border-radius: 10px;
    padding: 1.2rem .8rem;
    text-align: center;
}
.pipe-phase {
    font-family: 'JetBrains Mono', monospace;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
}
.pipe-name {
    font-family: 'DM Sans', sans-serif;
    font-size: 16px;
    font-weight: 500;
    color: #3a3a50;
    margin-top: .3rem;
}
.pipe-count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #7a7a90;
    margin-top: .2rem;
}

/* ── Section headers ────────────────────────────────────────────────────── */
.sec-over {
    font-family: 'JetBrains Mono', monospace;
    font-size: .65rem;
    font-weight: 600;
    letter-spacing: .15em;
    text-transform: uppercase;
    color: #7a7a90;
    text-align: center;
}
.sec-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 700;
    color: #1a1a2e;
    text-align: center;
    letter-spacing: -.02em;
}

/* ── Feature cards ──────────────────────────────────────────────────────── */
div[data-testid="stVerticalBlock"] .feature-card {
    background: #f7f8fb;
    border: 1px solid #e2e4ec;
    border-radius: 10px;
    padding: 1.5rem;
    height: 100%;
    transition: background .2s ease, border-color .2s ease, box-shadow .2s ease;
}
.feature-card:hover {
    background: #eef0f6;
    border-color: #d0d2de;
    box-shadow: 0 2px 12px rgba(0,0,0,.04);
}
.fc-phase {
    font-family: 'JetBrains Mono', monospace;
    font-size: .58rem;
    font-weight: 600;
    letter-spacing: .12em;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: .35rem;
    margin-bottom: .5rem;
}
.fc-phase-dot {
    width: 5px; height: 5px; border-radius: 50%;
    display: inline-block;
}
.fc-icon {
    font-size: 1.4rem;
    display: block;
    margin-bottom: .4rem;
}
.fc-name {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: #1a1a2e;
    margin-bottom: .35rem;
}
.fc-desc {
    font-family: 'DM Sans', sans-serif;
    font-size: .85rem;
    color: #555570;
    line-height: 1.55;
    margin-bottom: .8rem;
}
.fc-list {
    padding: 0;
    margin: 0;
}
.fc-list-item {
    font-family: 'DM Sans', sans-serif;
    font-size: .78rem;
    color: #6a6a80;
    line-height: 1.7;
}
.fc-bullet {
    font-weight: 700;
    color: #9a9ab0;
    margin-right: .3rem;
}

/* ── Stats metric overrides ─────────────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: #f7f8fb;
    border: 1px solid #e2e4ec;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
div[data-testid="stMetric"] label {
    font-family: 'DM Sans', sans-serif !important;
    color: #7a7a90 !important;
    font-size: .75rem !important;
    letter-spacing: .08em !important;
    text-transform: uppercase !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    color: #1a1a2e !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

/* ── Bottom tagline ─────────────────────────────────────────────────────── */
.bottom-tag {
    font-family: 'DM Sans', sans-serif;
    font-size: .9rem;
    color: #6a6a80;
    text-align: center;
    margin-bottom: 1rem;
}

/* ── Feature group expanders ────────────────────────────────────────────── */
div[data-testid="stExpander"] {
    border: 1px solid #e2e4ec !important;
    border-radius: 10px !important;
    margin-bottom: .8rem !important;
    background: #ffffff !important;
}
div[data-testid="stExpander"] summary {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: .9rem !important;
    font-weight: 600 !important;
    color: #1a1a2e !important;
    padding: .8rem 1rem !important;
    cursor: pointer !important;
}
div[data-testid="stExpander"] summary:hover {
    background: #f7f8fb !important;
}

/* ── Divider subtle ─────────────────────────────────────────────────────── */
hr {
    border-color: #e2e4ec !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ═══════════════════════════════════════════════════════════════════════════════
#  HERO
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("")  # spacer

st.markdown(
    '<div class="hero-badge">Multi-Agent Code Analysis Platform</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-title">AI Code<span class="acc"> Maniac</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-sub">'
    "25 specialized AI agents dissect your code across quality, complexity, "
    "performance, security, architecture, testing, documentation, and more &mdash; "
    "plus 5 commit analysis modes for release notes, hygiene audits, and churn detection."
    "</div>",
    unsafe_allow_html=True,
)

st.markdown("")  # spacer

# ── Primary CTA ──────────────────────────────────────────────────────────────
with st.container():
    st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
    if st.button("\u2002Start Analysis  \u2192", type="primary"):
        st.switch_page("pages/1_Code_Analysis.py")
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PIPELINE STRIP
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("")
st.divider()
st.markdown("")

_pipe_data = [
    ("Phase 0", "Security Gate", "Pre-flight scan", "#d63060"),
    ("Phase 1", "Foundation", "13 agents", "#0077b6"),
    ("Phase 2", "Context-Aware", "4 agents", "#d48a00"),
    ("Phase 3", "Synthesis", "2 agents", "#1a9960"),
    ("Phase 4", "Threat Model", "1 agent", "#c82050"),
    ("Phase 5", "Reporting", "2 agents", "#7c5cc4"),
    ("Standalone", "Commits", "5 modes", "#9060d0"),
]

pipe_cols = st.columns(len(_pipe_data))
for col, (phase, name, count, color) in zip(pipe_cols, _pipe_data):
    with col:
        st.markdown(
            f'<div class="pipe-box">'
            f'<div class="pipe-phase" style="color:{color};">{phase}</div>'
            f'<div class="pipe-name">{name}</div>'
            f'<div class="pipe-count">{count}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("")

jobs = list_jobs(conn, limit=1000)
if jobs:
    import pandas as pd

    df = pd.DataFrame(jobs)
    total = len(df)
    completed = len(df[df["status"] == "completed"])
    languages = df["language"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Analyses Run", total)
    c2.metric("Completed", completed)
    c3.metric("Languages", languages)
    c4.metric("AI Agents", 25)

    st.markdown("")


# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE CARDS
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown("")
st.markdown('<div class="sec-over">Capabilities</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sec-title">25 Agents. 7 Categories. One Pipeline.</div>',
    unsafe_allow_html=True,
)
st.markdown("")

_FEATURE_GROUPS = [
    {
        "group": "Code Quality & Metrics",
        "group_color": "#0077b6",
        "features": [
            {
                "icon": "\U0001f41b", "name": "Bug Analysis",
                "desc": "Detects bugs across severity levels with precise line attribution.",
                "points": ["Critical / Major / Minor severity", "Root cause and runtime impact",
                           "Side-by-side Original vs Fixed code", "Narrative assessment"],
            },
            {
                "icon": "\U0001f50d", "name": "Static Analysis",
                "desc": "Combines flake8/ESLint linting with AI semantic checks.",
                "points": ["Flake8/ESLint findings with rule codes", "Design smells and anti-patterns",
                           "Security and performance issues", "Feeds downstream agents"],
            },
            {
                "icon": "\U0001f4ca", "name": "Code Complexity",
                "desc": "Cyclomatic and cognitive complexity metrics per function.",
                "points": ["Maintainability index scoring", "Per-function breakdown table",
                           "Hotspot identification (top 3-5)", "Simplification suggestions"],
            },
            {
                "icon": "\U0001f503", "name": "Duplication Detection",
                "desc": "Finds code clones and DRY violations with extraction suggestions.",
                "points": ["Exact and near-duplicate blocks", "Similarity percentage scoring",
                           "Extract Function / Base Class suggestions", "Before/after refactored code"],
            },
            {
                "icon": "\U0001f3af", "name": "Type Safety",
                "desc": "Audits type hint coverage and flags type-related issues.",
                "points": ["Typed vs untyped function inventory", "Coverage grade A through D",
                           "Advanced typing suggestions", "Language-aware (Python, TS, Java)"],
            },
        ],
    },
    {
        "group": "Code Understanding",
        "group_color": "#d48a00",
        "features": [
            {
                "icon": "\U0001f30a", "name": "Code Flow",
                "desc": "Maps execution paths from entry points to outputs.",
                "points": ["Entry-point identification", "Step-by-step execution walkthrough",
                           "Structured Markdown output", "Provides context to downstream agents"],
            },
            {
                "icon": "\U0001f4cb", "name": "Requirements",
                "desc": "Reverse-engineers structured requirements from code.",
                "points": ["Unique IDs: REQ-001, REQ-002 ...", "Maps to source lines",
                           "Functional and non-functional", "Ideal for legacy code"],
            },
            {
                "icon": "\U0001f3d7\ufe0f", "name": "Code Design",
                "desc": "3-turn architecture review with bug and static context.",
                "points": ["Purpose, patterns, responsibilities", "Design issues: High / Medium / Low",
                           "9-section design document", "Public API and dependency mapping"],
            },
            {
                "icon": "\U0001f5fa\ufe0f", "name": "Architecture Mapper",
                "desc": "Maps module dependencies, coupling, and layer violations.",
                "points": ["Import/export dependency map", "Coupling and instability metrics",
                           "Circular dependency detection", "Mermaid component diagram"],
            },
            {
                "icon": "\U0001f4d0", "name": "Mermaid Diagram",
                "desc": "Generates live-rendered architecture diagrams.",
                "points": ["Flowchart, Sequence, Class diagrams", "Uses code-flow for accuracy",
                           "Valid Mermaid syntax output", "Inline Mermaid.js rendering"],
            },
            {
                "icon": "\U0001f4c2", "name": "Doxygen Docs",
                "desc": "Adds Doxygen headers to C/C++ code and generates HTML docs.",
                "points": ["@brief, @param, @return tags", "Annotated source saved to Reports",
                           "Runs doxygen CLI for HTML output", "Supports C, C++, and C#"],
            },
        ],
    },
    {
        "group": "Performance & Optimization",
        "group_color": "#1a9960",
        "features": [
            {
                "icon": "\u26a1", "name": "Performance Analysis",
                "desc": "Algorithmic complexity, memory, and scalability assessment.",
                "points": ["Big-O time and space per function", "N+1 query and resource leak detection",
                           "Caching opportunity identification", "Scalability at 10x / 100x / 1000x"],
            },
            {
                "icon": "\U0001f527", "name": "Refactoring Advisor",
                "desc": "Identifies code smells and recommends refactoring patterns.",
                "points": ["Fowler-catalogue refactorings", "Before/after code sketches",
                           "15+ smell types detected", "Prioritized by impact-to-effort"],
            },
        ],
    },
    {
        "group": "Testing & Maintenance",
        "group_color": "#7c5cc4",
        "features": [
            {
                "icon": "\U0001f9ea", "name": "Test Coverage",
                "desc": "Identifies untested functions and suggests test cases.",
                "points": ["Function inventory with test priority", "Happy path, edge, and error cases",
                           "Test skeleton code generation", "Testability assessment"],
            },
            {
                "icon": "\U0001f40d", "name": "C Test Generator",
                "desc": "Generates Python pytest + ctypes tests for C code.",
                "points": ["Type-safe ctypes bindings", "Happy path and edge cases",
                           "NULL pointer and overflow tests", "Saved to Reports/ folder"],
            },
            {
                "icon": "\U0001f4a5", "name": "Change Impact",
                "desc": "Estimates blast radius for code modifications.",
                "points": ["Public API surface mapping", "Downstream dependency analysis",
                           "2-4 specific change scenarios", "Safe change zones identified"],
            },
        ],
    },
    {
        "group": "Security & Compliance",
        "group_color": "#d63060",
        "features": [
            {
                "icon": "\U0001f510", "name": "Secret Scan",
                "desc": "Two-layer secret detection: regex pre-flight + AI deep scan.",
                "points": ["Phase 0 regex before LLM calls", "Block / Redact / Warn modes",
                           "Finds encoded and split secrets", "Validates pre-flight findings"],
            },
            {
                "icon": "\U0001f4e6", "name": "Dependency Analysis",
                "desc": "Multi-ecosystem SCA with CVE lookup.",
                "points": ["Python, JS, Java, C#, Go, Rust, C/C++", "20+ dependency file formats",
                           "CVE vulnerability mapping", "Prioritized remediation plan"],
            },
            {
                "icon": "\U0001f6e1\ufe0f", "name": "Threat Model",
                "desc": "STRIDE formal analysis or attacker-narrative reports.",
                "points": ["Trust boundaries and attack surface", "STRIDE-per-element threat table",
                           "Attacker narrative with PoC code", "Consumes all prior phase results"],
            },
            {
                "icon": "\U0001f4dc", "name": "License Compliance",
                "desc": "Detects licenses and checks compatibility.",
                "points": ["License headers and SPDX identifiers", "Copyleft obligation detection",
                           "Compatibility matrix analysis", "Attribution requirements list"],
            },
        ],
    },
    {
        "group": "Documentation & Review",
        "group_color": "#d48a00",
        "features": [
            {
                "icon": "\U0001f4d6", "name": "API Doc Generator",
                "desc": "Generates comprehensive API documentation from code.",
                "points": ["Module overview and quick start", "Class/function reference with types",
                           "3-5 usage examples", "Error handling and caveats"],
            },
            {
                "icon": "\U0001f4ac", "name": "PR Comments",
                "desc": "Generates human-quality GitHub PR review comments.",
                "points": ["Inline comments with file and line", "Engineering insight, not just findings",
                           "Must-fix vs nice-to-have summary", "Constructive, collegial tone"],
            },
            {
                "icon": "\U0001f4c4", "name": "Per-File Report",
                "desc": "Assembles all results per file into one document.",
                "points": ["All features in one Markdown report", "Logical section ordering",
                           "No extra LLM calls \u2014 instant", "Optional HTML with pro styling"],
            },
            {
                "icon": "\U0001f4da", "name": "Consolidated Report",
                "desc": "Synthesizes everything into a cohesive narrative.",
                "points": ["Executive summary and architecture", "Three modes: template, hybrid, llm",
                           "Cross-cutting concerns and patterns", "Self-contained HTML output"],
            },
        ],
    },
    {
        "group": "Commit Analysis (5 Modes)",
        "group_color": "#9060d0",
        "features": [
            {
                "icon": "\U0001f4dc", "name": "Commit Analysis",
                "desc": "Assesses commit history for risk and release readiness.",
                "points": ["Risk: High / Medium / Low", "Auto-generated changelog",
                           "Per-commit quality rating", "Clone, GitHub API, or Gitea"],
            },
            {
                "icon": "\U0001f4dd", "name": "Release Notes",
                "desc": "Generates polished user-facing release notes from commits.",
                "points": ["Highlights and executive summary", "Features, fixes, improvements",
                           "Breaking changes flagged", "Groups related commits together"],
            },
            {
                "icon": "\U0001f465", "name": "Developer Activity",
                "desc": "Contributor stats, activity patterns, and bus-factor risks.",
                "points": ["Per-author commit breakdown", "Activity timeline and frequency",
                           "Collaboration and ownership patterns", "Graceful degradation for API sources"],
            },
            {
                "icon": "\u2705", "name": "Commit Hygiene",
                "desc": "Audits commits against Conventional Commits spec.",
                "points": ["Compliance grade A through D", "Convention violation details",
                           "Squash candidates identified", "Message quality scoring"],
            },
            {
                "icon": "\U0001f525", "name": "Churn Analysis",
                "desc": "File hotspot detection from change frequency.",
                "points": ["Top 15-20 most changed files", "Directory-level churn aggregation",
                           "Co-change coupling patterns", "Clone source required for file data"],
            },
        ],
    },
    {
        "group": "Platform Tools",
        "group_color": "#4a90c4",
        "features": [
            {
                "icon": "\U0001f310", "name": "Web Scraper",
                "desc": "Extract clean text from any URL for analysis.",
                "points": ["Strips scripts, styles, and nav elements", "Decodes HTML entities",
                           "CLI and importable Python module", "Feeds content into any agent"],
            },
        ],
    },
]


def _render_feature_card(feat: dict, color: str) -> None:
    items_html = "".join(
        f'<div class="fc-list-item"><span class="fc-bullet">&#8250;</span>{p}</div>'
        for p in feat["points"]
    )
    st.markdown(
        f'<div class="feature-card">'
        f'<span class="fc-icon">{feat["icon"]}</span>'
        f'<div class="fc-name">{feat["name"]}</div>'
        f'<div class="fc-desc">{feat["desc"]}</div>'
        f'<div class="fc-list">{items_html}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


for idx, group in enumerate(_FEATURE_GROUPS):
    color = group["group_color"]
    group_label = f"{group['group']}  ({len(group['features'])} agents)"
    with st.expander(group_label, expanded=True):
        features = group["features"]
        # Render in rows of 3
        for i in range(0, len(features), 3):
            row = st.columns(3)
            for col, feat in zip(row, features[i : i + 3]):
                with col:
                    _render_feature_card(feat, color)


# ═══════════════════════════════════════════════════════════════════════════════
#  BOTTOM CTA
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("")
st.divider()
st.markdown("")

st.markdown(
    '<div class="bottom-tag">'
    "Select your source. Pick your agents. Get results in minutes."
    "</div>",
    unsafe_allow_html=True,
)

with st.container():
    _bl, _bc, _br = st.columns([2, 1, 2])
    with _bc:
        st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
        if st.button(
            "\u2002Start Analysis  \u2192",
            type="primary",
            width="stretch",
            key="bottom_cta",
        ):
            st.switch_page("pages/1_Code_Analysis.py")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")
