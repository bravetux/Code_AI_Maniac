import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import list_jobs

st.set_page_config(
    page_title="AI Code Maniac — Code Analysis",
    page_icon="🏟",
    layout="wide",
    initial_sidebar_state="expanded"
)

conn = get_connection()
init_schema(conn)

st.title("AI Code Maniac")
st.subheader("Multi-Agent Code Analysis Platform")

tab_dashboard, tab_features = st.tabs(["📊 Dashboard", "✨ Features"])

# ── Dashboard ─────────────────────────────────────────────────────────────────
with tab_dashboard:
    st.markdown("""
Navigate using the sidebar:
- **Analysis** — analyze files for bugs, design docs, flow, diagrams, and more
- **History** — browse and search past analyses
- **Commits** — analyze git commit history and changelogs
- **Presets** — manage saved prompt presets
- **Settings** — configure credentials, temperature, and database backup
""")

    jobs = list_jobs(conn, limit=1000)
    if jobs:
        import pandas as pd
        df = pd.DataFrame(jobs)
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Analyses Run", len(df))
        col2.metric("Completed", len(df[df["status"] == "completed"]))
        col3.metric("Languages Analyzed", df["language"].nunique())

        st.subheader("Recent Jobs")
        recent = df.head(10)[["created_at", "completed_at", "status", "source_type", "language", "features"]]
        st.dataframe(recent, use_container_width=True)
    else:
        st.info("No analyses yet. Head to the Analysis page to get started.")

# ── Features ──────────────────────────────────────────────────────────────────
with tab_features:
    st.markdown(
        "AI Code Maniac runs **8 specialized AI agents** in a coordinated 3-phase pipeline. "
        "Each agent focuses on a distinct dimension of code quality."
    )
    st.divider()

    _FEATURES = [
        {
            "icon": "🐛",
            "name": "Bug Analysis",
            "phase": "Phase 1 — Foundation",
            "description": "Detects bugs across severity levels with precise line attribution.",
            "highlights": [
                "Critical / Major / Minor severity classification",
                "Root cause and runtime impact for every finding",
                "Side-by-side **Original vs Fixed** code comparison",
                "Configurable context lines around each bug (`BUG_CONTEXT_LINES`)",
                "Narrative overall assessment before the issue list",
            ],
        },
        {
            "icon": "🔍",
            "name": "Static Analysis",
            "phase": "Phase 1 — Foundation",
            "description": "Combines a real linter (flake8) with AI-powered semantic checks.",
            "highlights": [
                "Flake8 linter findings with rule codes and line numbers",
                "AI semantic findings: dead code, unreachable paths, anti-patterns",
                "Narrative overall quality assessment",
                "Feeds downstream agents (Code Design, PR Comments)",
            ],
        },
        {
            "icon": "🌊",
            "name": "Code Flow",
            "phase": "Phase 1 — Foundation",
            "description": "Maps the execution path through a file from entry points to outputs.",
            "highlights": [
                "Entry-point identification (main functions, event handlers, etc.)",
                "Step-by-step execution walkthrough with callee references",
                "Exported as structured Markdown for documentation",
                "Provides flow context to the Mermaid Diagram agent",
            ],
        },
        {
            "icon": "📋",
            "name": "Requirement Design",
            "phase": "Phase 1 — Foundation",
            "description": "Reverse-engineers structured software requirements from existing code.",
            "highlights": [
                "Assigns unique requirement IDs (REQ-001, REQ-002 …)",
                "Maps each requirement to its component and source lines",
                "Outputs a formatted Markdown requirements document",
                "Useful for generating specs from legacy or undocumented code",
            ],
        },
        {
            "icon": "🏗️",
            "name": "Code Design",
            "phase": "Phase 2 — Context-Aware",
            "description": "Reviews architecture, patterns, and design quality with full bug/static context.",
            "highlights": [
                "Full design document: purpose, patterns, responsibilities",
                "Design issues prioritised High / Medium / Low",
                "Improvement roadmap with actionable recommendations",
                "Public API documentation with signatures and descriptions",
                "Dependency and data-contract inventory",
            ],
        },
        {
            "icon": "📐",
            "name": "Mermaid Diagram",
            "phase": "Phase 2 — Context-Aware",
            "description": "Generates live-rendered architecture diagrams from code structure.",
            "highlights": [
                "Flowchart, Sequence, and Class diagram types",
                "Uses code-flow context for accurate call relationships",
                "Mermaid source always visible alongside rendered diagram",
                "Inline rendering via Mermaid.js v10 — no external tools needed",
            ],
        },
        {
            "icon": "💬",
            "name": "PR Comment Generator",
            "phase": "Phase 3 — Synthesis",
            "description": "Turns automated findings into human-quality GitHub pull request reviews.",
            "highlights": [
                "Inline comments with file, line, and severity",
                "Adds engineering insight beyond just restating the finding",
                "Top-level PR summary: must-fix items, nice-to-haves, positives",
                "Constructive, collegial tone suitable for real code reviews",
            ],
        },
        {
            "icon": "📜",
            "name": "Commit Analysis",
            "phase": "Standalone",
            "description": "Assesses git commit history for risk, quality, and change impact.",
            "highlights": [
                "Risk level: High / Medium / Low with concern breakdown",
                "Auto-generated changelog: Added / Changed / Removed",
                "Per-commit quality rating: Good / Needs Improvement / Poor",
                "Works directly from a GitHub or Gitea repository",
            ],
        },
    ]

    _PHASE_COLOR = {
        "Phase 1 — Foundation":    "#1f77b4",
        "Phase 2 — Context-Aware": "#ff7f0e",
        "Phase 3 — Synthesis":     "#2ca02c",
        "Standalone":              "#9467bd",
    }

    # Render in rows of 2
    for i in range(0, len(_FEATURES), 2):
        cols = st.columns(2)
        for col, feat in zip(cols, _FEATURES[i:i + 2]):
            phase_color = _PHASE_COLOR.get(feat["phase"], "#888")
            bullet_md = "\n".join(f"- {h}" for h in feat["highlights"])
            with col:
                with st.container(border=True):
                    st.markdown(
                        f"## {feat['icon']} {feat['name']}\n"
                        f"<span style='font-size:12px;color:{phase_color};font-weight:600'>"
                        f"● {feat['phase']}</span>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"_{feat['description']}_")
                    st.markdown(bullet_md)
