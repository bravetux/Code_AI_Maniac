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

/* ── Dark theme overrides ───────────────────────────────────────────────── */
section[data-testid="stMain"] {
    background: #06060c !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
}

/* ── Hero text ──────────────────────────────────────────────────────────── */
.hero-badge {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: .68rem;
    font-weight: 500;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: #00c8ff;
    border: 1px solid rgba(0,200,255,.25);
    border-radius: 100px;
    padding: .35em 1.2em;
    background: rgba(0,200,255,.06);
}
.hero-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: clamp(2rem, 4.5vw, 3.4rem);
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -.03em;
    color: #e8e8f0;
    margin: .8rem 0 .6rem;
}
.hero-title .acc { color: #00c8ff; }
.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    line-height: 1.65;
    color: #b0b0c8;
    max-width: 620px;
}

/* ── CTA button ─────────────────────────────────────────────────────────── */
div.cta-wrap [data-testid="stBaseButton-primary"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: .95rem !important;
    letter-spacing: .05em !important;
    background: linear-gradient(135deg, #00c8ff, #0090cc) !important;
    color: #000 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: .85rem 2.6rem !important;
    box-shadow: 0 0 24px rgba(0,200,255,.12), 0 4px 16px rgba(0,0,0,.35) !important;
    transition: all .25s ease !important;
}
div.cta-wrap [data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 0 36px rgba(0,200,255,.22), 0 8px 24px rgba(0,0,0,.45) !important;
}

/* ── Pipeline row ───────────────────────────────────────────────────────── */
.pipe-box {
    background: #0d0d16;
    border: 1px solid #2a2a40;
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
    color: #c8c8d8;
    margin-top: .3rem;
}
.pipe-count {
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    color: #8888a0;
    margin-top: .2rem;
}

/* ── Section headers ────────────────────────────────────────────────────── */
.sec-over {
    font-family: 'JetBrains Mono', monospace;
    font-size: .65rem;
    font-weight: 600;
    letter-spacing: .15em;
    text-transform: uppercase;
    color: #9090aa;
    text-align: center;
}
.sec-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.5rem;
    font-weight: 700;
    color: #e8e8f0;
    text-align: center;
    letter-spacing: -.02em;
}

/* ── Feature cards ──────────────────────────────────────────────────────── */
div[data-testid="stVerticalBlock"] .feature-card {
    background: #0d0d16;
    border: 1px solid #1a1a2e;
    border-radius: 10px;
    padding: 1.5rem;
    height: 100%;
    transition: background .2s ease, border-color .2s ease;
}
.feature-card:hover {
    background: #13131f;
    border-color: #252540;
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
    color: #e8e8f0;
    margin-bottom: .35rem;
}
.fc-desc {
    font-family: 'DM Sans', sans-serif;
    font-size: .85rem;
    color: #b0b0c8;
    line-height: 1.55;
    margin-bottom: .8rem;
}
.fc-list {
    list-style: none;
    padding: 0;
    margin: 0;
}
.fc-list li {
    font-family: 'DM Sans', sans-serif;
    font-size: .78rem;
    color: #9898b0;
    line-height: 1.6;
    padding-left: .9rem;
    position: relative;
}
.fc-list li::before {
    content: '\203a';
    position: absolute;
    left: 0;
    font-weight: 700;
}

/* ── Stats metric overrides ─────────────────────────────────────────────── */
div[data-testid="stMetric"] {
    background: #0d0d16;
    border: 1px solid #1a1a2e;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
}
div[data-testid="stMetric"] label {
    font-family: 'DM Sans', sans-serif !important;
    color: #9090aa !important;
    font-size: .75rem !important;
    letter-spacing: .08em !important;
    text-transform: uppercase !important;
}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    color: #e8e8f0 !important;
    font-size: 1.8rem !important;
    font-weight: 700 !important;
}

/* ── Bottom tagline ─────────────────────────────────────────────────────── */
.bottom-tag {
    font-family: 'DM Sans', sans-serif;
    font-size: .9rem;
    color: #9898b0;
    text-align: center;
    margin-bottom: 1rem;
}

/* ── Divider subtle ─────────────────────────────────────────────────────── */
hr {
    border-color: #1a1a2e !important;
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
    '<div class="hero-badge">AG-UC-1128 &middot; Multi-Agent Platform</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-title">AI Code<span class="acc"> Maniac</span></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="hero-sub">'
    "13 specialized AI agents dissect your code across bugs, design, "
    "flow, security, dependencies, threat modelling, and more &mdash; "
    "then synthesize everything into polished, professional reports."
    "</div>",
    unsafe_allow_html=True,
)

st.markdown("")  # spacer

# ── Primary CTA ──────────────────────────────────────────────────────────────
with st.container():
    st.markdown('<div class="cta-wrap">', unsafe_allow_html=True)
    if st.button("\u2002Start Analysis  \u2192", type="primary"):
        st.switch_page("pages/1_Analysis.py")
    st.markdown("</div>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
#  PIPELINE STRIP
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("")
st.divider()
st.markdown("")

_pipe_data = [
    ("Phase 0", "Security Gate", "Pre-flight scan", "#ff6080"),
    ("Phase 1", "Foundation", "5 agents", "#00c8ff"),
    ("Phase 2", "Context-Aware", "2 agents", "#ffb020"),
    ("Phase 3", "Synthesis", "2 agents", "#22d68a"),
    ("Phase 4", "Threat Model", "1 agent", "#ff4060"),
    ("Phase 5", "Reporting", "2 agents", "#a37eff"),
    ("Standalone", "Commits", "1 agent", "#c080ff"),
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
    c4.metric("AI Agents", 13)

    st.markdown("")


# ═══════════════════════════════════════════════════════════════════════════════
#  FEATURE CARDS
# ═══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown("")
st.markdown('<div class="sec-over">Capabilities</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sec-title">13 Agents. One Pipeline.</div>',
    unsafe_allow_html=True,
)
st.markdown("")

_FEATURES = [
    {
        "icon": "\U0001f41b",
        "name": "Bug Analysis",
        "phase": "Phase 1 \u2014 Foundation",
        "color": "#00c8ff",
        "desc": "Detects bugs across severity levels with precise line attribution.",
        "points": [
            "Critical / Major / Minor severity",
            "Root cause and runtime impact",
            "Side-by-side Original vs Fixed code",
            "Narrative assessment before issues",
        ],
    },
    {
        "icon": "\U0001f50d",
        "name": "Static Analysis",
        "phase": "Phase 1 \u2014 Foundation",
        "color": "#00c8ff",
        "desc": "Combines flake8 linting with AI semantic checks.",
        "points": [
            "Flake8 findings with rule codes",
            "Dead code and anti-pattern detection",
            "Narrative quality assessment",
            "Feeds downstream agents",
        ],
    },
    {
        "icon": "\U0001f30a",
        "name": "Code Flow",
        "phase": "Phase 1 \u2014 Foundation",
        "color": "#00c8ff",
        "desc": "Maps execution paths from entry points to outputs.",
        "points": [
            "Entry-point identification",
            "Step-by-step execution walkthrough",
            "Structured Markdown output",
            "Provides context to Mermaid agent",
        ],
    },
    {
        "icon": "\U0001f4cb",
        "name": "Requirements",
        "phase": "Phase 1 \u2014 Foundation",
        "color": "#00c8ff",
        "desc": "Reverse-engineers structured requirements from code.",
        "points": [
            "Unique IDs: REQ-001, REQ-002 ...",
            "Maps to components and source lines",
            "Formatted Markdown requirements doc",
            "Ideal for legacy / undocumented code",
        ],
    },
    {
        "icon": "\U0001f3d7\ufe0f",
        "name": "Code Design",
        "phase": "Phase 2 \u2014 Context-Aware",
        "color": "#ffb020",
        "desc": "Architecture review with full bug and static context.",
        "points": [
            "Purpose, patterns, responsibilities",
            "Design issues: High / Medium / Low",
            "Improvement roadmap",
            "Public API docs and dependencies",
        ],
    },
    {
        "icon": "\U0001f4d0",
        "name": "Mermaid Diagram",
        "phase": "Phase 2 \u2014 Context-Aware",
        "color": "#ffb020",
        "desc": "Generates live-rendered architecture diagrams.",
        "points": [
            "Flowchart, Sequence, Class diagrams",
            "Uses code-flow for accuracy",
            "Source alongside rendered diagram",
            "Inline Mermaid.js v10 rendering",
        ],
    },
    {
        "icon": "\U0001f510",
        "name": "Secret Scan",
        "phase": "Phase 0 + 3 \u2014 Security",
        "color": "#ff6080",
        "desc": "Two-layer secret detection: regex pre-flight gate + AI deep scan.",
        "points": [
            "Phase 0: regex scan before Bedrock",
            "Block / Redact / Warn modes",
            "AI finds encoded & split secrets",
            "Validates pre-flight findings",
        ],
    },
    {
        "icon": "\U0001f4e6",
        "name": "Dependency Analysis",
        "phase": "Phase 1 \u2014 Foundation",
        "color": "#00c8ff",
        "desc": "Multi-ecosystem SCA with 5 pluggable CVE backends.",
        "points": [
            "Python, JS, Java, C#, Go, Rust, C/C++",
            "OSV, NVD, GitHub Advisory, LLM, Hybrid",
            "Auto-discovers dependency files",
            "Prioritized remediation plan",
        ],
    },
    {
        "icon": "\U0001f6e1\ufe0f",
        "name": "Threat Model",
        "phase": "Phase 4 \u2014 Threat Model",
        "color": "#ff4060",
        "desc": "STRIDE formal analysis or attacker-narrative reports.",
        "points": [
            "Trust boundaries & attack surface",
            "STRIDE-per-element threat table",
            "Attacker narrative with PoC code",
            "Original vs Fixed code comparison",
        ],
    },
    {
        "icon": "\U0001f4ac",
        "name": "PR Comments",
        "phase": "Phase 3 \u2014 Synthesis",
        "color": "#22d68a",
        "desc": "Generates human-quality GitHub PR reviews.",
        "points": [
            "Inline comments with file and line",
            "Engineering insight, not just findings",
            "Top-level summary of must-fixes",
            "Constructive, collegial tone",
        ],
    },
    {
        "icon": "\U0001f4dc",
        "name": "Commit Analysis",
        "phase": "Standalone",
        "color": "#c080ff",
        "desc": "Assesses commit history for risk and quality.",
        "points": [
            "Risk: High / Medium / Low",
            "Auto-generated changelog",
            "Per-commit quality rating",
            "Clone, GitHub API, or Gitea",
        ],
    },
    {
        "icon": "\U0001f4c4",
        "name": "Per-File Report",
        "phase": "Phase 5 \u2014 Reporting",
        "color": "#a37eff",
        "desc": "Assembles all results per file into one document.",
        "points": [
            "All features in one Markdown report",
            "Logical section ordering",
            "No extra LLM calls \u2014 instant",
            "Optional HTML with pro styling",
        ],
    },
    {
        "icon": "\U0001f4da",
        "name": "Consolidated Report",
        "phase": "Phase 5 \u2014 Reporting",
        "color": "#a37eff",
        "desc": "Synthesizes everything into a cohesive narrative.",
        "points": [
            "Executive summary & architecture",
            "Three modes: template, hybrid, llm",
            "Cross-cutting concerns & patterns",
            "Self-contained HTML output",
        ],
    },
]

# Render in rows of 2
for i in range(0, len(_FEATURES), 2):
    row = st.columns(2)
    for col, feat in zip(row, _FEATURES[i : i + 2]):
        with col:
            li_html = "".join(f"<li>{p}</li>" for p in feat["points"])
            st.markdown(
                f'<div class="feature-card">'
                f'<div class="fc-phase" style="color:{feat["color"]};">'
                f'<span class="fc-phase-dot" style="background:{feat["color"]};"></span>'
                f'{feat["phase"]}</div>'
                f'<span class="fc-icon">{feat["icon"]}</span>'
                f'<div class="fc-name">{feat["name"]}</div>'
                f'<div class="fc-desc">{feat["desc"]}</div>'
                f'<ul class="fc-list">{li_html}</ul>'
                f"</div>",
                unsafe_allow_html=True,
            )


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
            st.switch_page("pages/1_Analysis.py")
        st.markdown("</div>", unsafe_allow_html=True)

st.markdown("")
