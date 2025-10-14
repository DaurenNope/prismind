"""
Dashboard components for the PrisMind application - Modular Implementation
"""

import streamlit as st
from typing import Dict, Any, Optional

from .dashboard_posts import render_posts_tab
from .dashboard_analytics import render_analytics_tab
from .dashboard_settings import render_settings_tab


def render_dashboard():
    """Render the main dashboard view"""
    st.title("🧠 PrisMind - Intelligent Bookmark Platform")
    st.markdown("*Transform your social media bookmarks into structured intelligence*")
    
    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📚 All Posts", "📊 Analytics", "⚙️ Settings"])
    
    with tab1:
        render_posts_tab()
    
    with tab2:
        render_analytics_tab()
    
    with tab3:
        render_settings_tab()