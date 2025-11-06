import streamlit as st
import os

from src.web.components.mimesis_overview_tab import render as overview
from src.web.components.mimesis_queue_tab import render as queue
from src.web.components.mimesis_editor_tab import render as editor
from src.web.components.mimesis_scheduler_tab import render as scheduler
from src.web.components.mimesis_analytics_tab import render as analytics
from src.web.components.status_bar import render_status_bar
from src.web.components.review_tab import render_review_tab
from src.web.components.trends_tab import render_trends_tab
from src.web.components.triage_tab import render_triage_tab
from src.web.components.collection_tab import render_collection_tab


def render_publishing_page():
    render_status_bar()

    # Feature flag to enable new UI layout
    # Default NEW_UI on; can disable via NEW_UI=false
    new_ui = os.getenv("NEW_UI", "true").lower() in ("true", "1", "yes")

    if new_ui:
        # New IA: Inbox (Collection) is first; Triage prominent
        tab_inbox, tab_triage, tab_queue, tab_editor, tab_analytics = st.tabs([
            "📥 Inbox", "🧹 Triage", "📝 Rewrite Queue", "✏️ Editor", "📊 Analytics"
        ])

        with tab_inbox:
            render_collection_tab()

        with tab_triage:
            render_triage_tab()

        with tab_queue:
            queue()

        with tab_editor:
            editor()

        with tab_analytics:
            analytics()
        return

    # Legacy layout (default)
    tab1, tab2, tab_triage, tab3, tab4, tab5, tab6 = st.tabs(["🔍 Review & Approve", "📈 Trends", "🧹 Triage", "📝 Quick Post", "📊 Status", "✏️ Editor", "📊 Analytics"])

    with tab1:
        render_review_tab()

    with tab2:
        render_trends_tab()

    with tab_triage:
        render_triage_tab()

    with tab3:
        queue()

    with tab4:
        overview()

    with tab5:
        editor()

    with tab6:
        analytics()


