import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st
import pandas as pd
from db.connection import get_connection
from db.queries.history import list_history

st.set_page_config(page_title="History — AI Code Maniac", layout="wide")
st.title("Analysis History")

conn = get_connection()
history = list_history(conn, limit=200)

if not history:
    st.info("No analyses run yet. Go to the Analysis page to get started.")
else:
    df = pd.DataFrame(history)
    df["created_at"] = pd.to_datetime(df["created_at"])

    col1, col2 = st.columns(2)
    feature_filter = col1.selectbox("Feature", ["All"] + sorted(df["feature"].unique().tolist()))
    lang_filter = col2.selectbox("Language", ["All"] + sorted(df["language"].dropna().unique().tolist()))

    if feature_filter != "All":
        df = df[df["feature"] == feature_filter]
    if lang_filter != "All":
        df = df[df["language"] == lang_filter]

    st.dataframe(df[["created_at", "feature", "language", "source_ref", "summary"]],
                 use_container_width=True)
