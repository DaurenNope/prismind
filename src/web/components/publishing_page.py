import streamlit as st

from src.web.components.mimesis_overview_tab import render as overview
from src.web.components.mimesis_queue_tab import render as queue
from src.web.components.mimesis_editor_tab import render as editor
from src.web.components.mimesis_scheduler_tab import render as scheduler
from src.web.components.mimesis_analytics_tab import render as analytics
from src.web.components.status_bar import render_status_bar


def render_publishing_page():
    render_status_bar()
    
    # Simple tab-based navigation
    tab1, tab2, tab3, tab4 = st.tabs(["📝 Quick Post", "📊 Status", "✏️ Editor", "📈 Analytics"])
    
    with tab1:
        queue()
    
    with tab2:
        overview()
    
    with tab3:
        editor()
    
    with tab4:
        analytics()


