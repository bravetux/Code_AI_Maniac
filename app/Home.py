import streamlit as st
from db.connection import get_connection
from db.schema import init_schema
from db.queries.jobs import list_jobs

st.set_page_config(
    page_title="AI Arena — Code Analysis",
    page_icon="🏟",
    layout="wide",
    initial_sidebar_state="expanded"
)

conn = get_connection()
init_schema(conn)

st.title("AI Arena")
st.subheader("Multi-Agent Code Analysis Platform")

st.markdown("""
Navigate using the sidebar:
- **Analysis** — analyze files for bugs, design docs, flow, diagrams, and more
- **History** — browse and search past analyses
- **Commits** — analyze git commit history and changelogs
- **Presets** — manage saved prompt presets
- **Settings** — configure credentials, temperature, and database backup
""")

# Quick stats
jobs = list_jobs(conn, limit=1000)
if jobs:
    import pandas as pd
    df = pd.DataFrame(jobs)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Analyses Run", len(df))
    col2.metric("Completed", len(df[df["status"] == "completed"]))
    col3.metric("Languages Analyzed", df["language"].nunique())

    st.subheader("Recent Jobs")
    recent = df.head(10)[["created_at", "status", "source_type", "language", "features"]]
    st.dataframe(recent, use_container_width=True)
else:
    st.info("No analyses yet. Head to the Analysis page to get started.")
