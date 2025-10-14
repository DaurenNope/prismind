#!/usr/bin/env python3
"""
🧠 PrisMind - Personal Intelligence Engine
========================================

> RULES COMPLIANCE: Follow RULES.md for all development guidelines
> CHANGE PROCESS: Use CHANGE_TEMPLATE.md for all modifications

Transform your social media bookmarks into a structured, searchable knowledge base.
PrisMind extracts saved content from Twitter, Reddit, and Threads, analyzes your interests with AI,
and organizes them into actionable insights.
"""

import asyncio
import os
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Import components
from src.web.components.sidebar import render_sidebar
from src.web.components.tabs import (
    render_dashboard_tab,
    render_browse_tab,
    render_settings_tab,
    render_discoveries_tab,
)
from src.web.components.automation_tab import render_automation_tab
from src.web.components.telegram_tab import render_telegram_tab
from src.web.components.unified_feed_tab import render_unified_feed
from src.pipeline.orchestrator import get_orchestrator
from src.services.analysis_service import analyze_recent_posts

# Load environment variables from .env file
load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Use shared database manager
from src.services.new_database_manager import get_database_manager as _get_db_manager

@st.cache_resource
def get_database_manager():
    return _get_db_manager()

def init_session_state():
    """Initialize the session state variables"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.automation_enabled = False
        st.session_state.last_collection = None
        st.session_state.collection_stats = {"twitter": 0, "reddit": 0, "threads": 0}
        st.session_state.background_collector = None
        st.session_state.background_running = False
        st.session_state.current_page = 0
        st.session_state.analysis_batch_size = 10
        st.session_state.analysis_last_result = None

def run_collection(platform: str) -> dict:
    """Run collection for a specific platform"""
    try:
        orch = get_orchestrator()
        # Call orchestrator per-platform and adapt to UI result shape
        count = asyncio.run(orch.collect_platform(platform))
        result = {'collected': count}
        
        # Update collection stats
        if 'collected' in result:
            st.session_state.collection_stats[platform] = result['collected']
        return result
    except Exception as e:
        return {'error': f'Error running {platform} collection: {str(e)}'}

async def run_automated_collection():
    """Run automated collection in the background"""
    while st.session_state.automation_enabled:
        try:
            # Run collection for each platform
            for platform in ['twitter', 'reddit', 'threads']:
                result = run_collection(platform)
                if 'error' in result:
                    print(f"Error in {platform} collection: {result['error']}")
            
            # Update last collection time
            st.session_state.last_collection = datetime.now().isoformat()
            
            # Wait for the next collection interval (60 minutes)
            await asyncio.sleep(60 * 60)
            
        except Exception as e:
            print(f"Error in automated collection: {e}")
            await asyncio.sleep(60)  # Wait a minute before retrying

## Tabs moved to src/web/components/tabs.py

def main():
    """Main application entry point"""
    # Initialize session state
    init_session_state()
    
    # Setup page configuration
    st.set_page_config(
        page_title="🧠 PrisMind - Intelligence Platform",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for better styling
    st.markdown("""
    <style>
        .main { padding-top: 1rem; }
        .stButton button { width: 100%; }
        .metric-container { 
            background: #f0f2f6; 
            padding: 1rem; 
            border-radius: 0.5rem; 
            margin: 0.5rem 0;
        }
        .success-message { color: #28a745; }
        .error-message { color: #dc3545; }
        .info-message { color: #17a2b8; }
    </style>
    """, unsafe_allow_html=True)
    
    # Render sidebar
    render_sidebar()
    
    # Main title
    st.title("🧠 PrisMind - Intelligent Bookmark Platform")
    st.markdown("*Transform your social media bookmarks into structured intelligence*")
    
    # Create tabs for different views
    tab1, tab_news, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📰 Discoveries", "🗞️ Digest", "🇷🇺 Telegram", "📡 Sources", "✍️ Rewriter", "🤖 Automation", "📚 Browse", "⚙️ Settings"])
    
    with tab1:
        render_unified_feed()  # Main discovery feed: RSS + Reddit + GitHub
    
    with tab2:
        render_discoveries_tab()

    with tab_news:
        st.subheader("Daily Digest")
        try:
            orch = get_orchestrator()
            col_x, col_y = st.columns([1, 1])
            with col_x:
                if st.button("Run Quick E2E Check", help="Collect → Analyze (10) → Build digest"):
                    with st.spinner("Running collect → analyze → digest..."):
                        _ = asyncio.run(orch.collect_all())
                        _ = asyncio.run(orch.analyze_batch(limit=10))
            with col_y:
                if st.button("Refresh Digest"):
                    pass
            with st.spinner("Building news feed..."):
                feed = asyncio.run(orch.build_news_feed(limit=50))
            if not feed:
                st.info("No items available yet. Try collecting content first.")
            else:
                for item in feed:
                    with st.container():
                        title = item.get("title") or "Untitled"
                        url = item.get("url") or ""
                        meta = f"{item.get('platform','')} • {item.get('source','')} • {item.get('created_at','')}"
                        st.markdown(f"### [{title}]({url})")
                        st.caption(meta)
                        if item.get("summary"):
                            st.write(item["summary"]) 
                        tags = item.get("tags") or []
                        if tags:
                            st.caption("Tags: " + ", ".join(tags))
                        st.divider()
        except Exception as e:
            st.error(f"Error building digest: {e}")

        st.subheader("Quick Actions")
        col_a, col_b = st.columns([1, 1])
        with col_a:
            if st.button("🤖 Analyze Recent Posts", help="Run AI analysis on recent or unanalyzed posts"):
                batch_size = st.session_state.get('analysis_batch_size', 10)
                with st.spinner(f"Analyzing up to {batch_size} posts..."):
                    analysis_result = analyze_recent_posts(limit=batch_size, unanalyzed_only=True)
                st.session_state.analysis_last_result = analysis_result
                processed = analysis_result.get('processed', 0)
                attempted = analysis_result.get('attempted', 0)
                errors = analysis_result.get('errors') or []
                if processed:
                    st.success(f"Analyzed {processed} of {attempted} posts.")
                elif attempted:
                    st.warning("No posts were successfully analyzed. Check logs for details.")
                else:
                    st.info("No posts available for analysis.")
                if errors:
                    with st.expander("Show analysis errors"):
                        for err in errors[:10]:
                            st.write(f"- {err}")
                        if len(errors) > 10:
                            st.write(f"...and {len(errors) - 10} more errors")
        with col_b:
            if st.session_state.analysis_last_result:
                last = st.session_state.analysis_last_result
                processed = last.get('processed', 0)
                attempted = last.get('attempted', 0)
                st.metric("Last Analysis", f"{processed}/{attempted} posts")
    
    with tab3:
        render_telegram_tab()
    
    with tab4:
        from src.web.components.sources_tab import render_sources_tab
        render_sources_tab()
    
    with tab5:
        from src.web.components.rewriter_tab import render_rewriter_tab
        render_rewriter_tab()
    
    with tab6:
        render_browse_tab()
    
    with tab7:
        render_settings_tab()
    
    # Handle collection triggers
    if st.session_state.get('run_twitter_collection', False):
        with st.spinner("Collecting from Twitter..."):
            result = run_collection('twitter')
            if 'error' in result:
                st.error(f"Error collecting from Twitter: {result['error']}")
            else:
                st.success(f"Collected {result.get('collected', 0)} posts from Twitter")
        st.session_state.run_twitter_collection = False
    
    if st.session_state.get('run_reddit_collection', False):
        with st.spinner("Collecting from Reddit..."):
            result = run_collection('reddit')
            if 'error' in result:
                st.error(f"Error collecting from Reddit: {result['error']}")
            else:
                st.success(f"Collected {result.get('collected', 0)} posts from Reddit")
        st.session_state.run_reddit_collection = False
    
    if st.session_state.get('run_threads_collection', False):
        with st.spinner("Collecting from Threads..."):
            result = run_collection('threads')
            if 'error' in result:
                st.error(f"Error collecting from Threads: {result['error']}")
            else:
                st.success(f"Collected {result.get('collected', 0)} posts from Threads")
        st.session_state.run_threads_collection = False
    
    # Start/stop background collection
    if st.session_state.automation_enabled and not st.session_state.background_running:
        st.session_state.background_running = True
        asyncio.run(run_automated_collection())
    elif not st.session_state.automation_enabled and st.session_state.background_running:
        st.session_state.background_running = False

if __name__ == "__main__":
    main()
    
    # This ensures the app doesn't run multiple times in Streamlit
    if 'main_ran' not in st.session_state:
        st.session_state.main_ran = True
        st.rerun()
