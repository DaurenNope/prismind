import os
import requests
import streamlit as st

from src.database.publishing.bridge import MimesisDB


def render():
    st.header("Publishing Overview")
    db = MimesisDB()
    try:
        ready = db.list_ready_transformations()
    except Exception as exc:
        st.warning(f"Could not load ready transformations: {exc}")
        ready = []
    try:
        due = db.list_due_posts()
    except Exception as exc:
        st.warning(f"Could not load due posts: {exc}")
        due = []

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Ready for posting", len(ready))
    with col2:
        st.metric("Due now", len(due))
