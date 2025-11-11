import streamlit as st

from src.web.components.mimesis_overview_tab import render as overview
from src.web.components.mimesis_queue_tab import render as queue
from src.web.components.mimesis_editor_tab import render as editor
from src.web.components.mimesis_analytics_tab import render as analytics
from src.web.components.status_bar import render_status_bar
from src.web.components.review_tab import render_review_tab
from src.web.components.curated_posts_tab import render_curated_posts_tab


def render_publishing_page():
    render_status_bar()

    # Consolidated Publishing tabs (5 tabs instead of 8)
    # 1. Review & Approve - review posts and create rewrites
    # 2. Curated Posts - view/post from usable_posts table
    # 3. Queue & Schedule - queue management and scheduling (merged Quick Post + Status)
    # 4. Editor - edit transformations
    # 5. Analytics - publishing analytics (consolidated)
    tab_review, tab_curated, tab_queue, tab_editor, tab_analytics = st.tabs(
        ["🔍 Review & Approve", "💎 Curated Posts", "📅 Queue & Schedule", "✏️ Editor", "📊 Analytics"]
    )

    with tab_review:
        render_review_tab()

    with tab_curated:
        render_curated_posts_tab()

    with tab_queue:
        # Merged: Queue management (from mimesis_queue_tab) + Status/Overview
        st.header("📅 Queue & Schedule")
        
        # Sub-tabs for queue management
        queue_subtab1, queue_subtab2 = st.tabs(["📋 Queue", "📊 Status"])
        
        with queue_subtab1:
            queue()  # Queue management from mimesis_queue_tab
        
        with queue_subtab2:
            overview()  # Status/Overview from mimesis_overview_tab

    with tab_editor:
        editor()

    with tab_analytics:
        analytics()


