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
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"Added to path: {project_root}")

# Import components
from src.web.components.status_bar import render_status_bar
from src.web.components.tabs import (
    render_dashboard_tab,
    render_browse_tab,
    render_settings_tab,
    render_discoveries_tab,
)
from src.web.components.automation_tab import render_automation_tab
from src.web.components.telegram_tab import render_telegram_tab
from src.web.components.unified_feed_tab import render_unified_feed
from src.web.components.publishing_page import render_publishing_page
from src.web.components.settings_page import render_settings_page
from src.web.components.collection_tab import render_collection_tab
from src.web.components.persona_pipeline_tab import render_persona_pipeline_tab
from src.web.components.system_status_tab import render_system_status_tab
from src.pipeline.orchestrator import get_orchestrator
from src.services.analysis_runner import analyze_recent_posts
from src.publishing.worker import get_publisher_worker

# Load environment variables from .env file
load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Use shared database manager
from src.services.new_database_manager import get_database_manager as _get_db_manager


@st.cache_resource
def get_database_manager():
    return _get_db_manager()


@st.cache_data(ttl=60)  # Cache for 1 minute to avoid too frequent DB calls
def check_unanalyzed_posts():
    """Check for posts that haven't been analyzed yet"""
    try:
        db_manager = get_database_manager()

        # Get all posts
        all_posts = db_manager.get_posts(limit=1000)  # Get sufficient posts to check

        if not all_posts:
            return 0, []

        # Filter for unanalyzed posts (no analyzed_at field or empty)
        unanalyzed_posts = []
        for post in all_posts:
            if not isinstance(post, dict):
                continue

            analyzed_at = post.get("analyzed_at") or post.get("analysis_timestamp")
            ai_summary = (
                post.get("ai_summary")
                or post.get("summary")
                or post.get("content_summary")
            )

            # Consider unanalyzed if no analyzed_at and no ai_summary
            # Also check if analysis fields are empty strings
            has_analysis = (
                analyzed_at and str(analyzed_at).strip() and analyzed_at != "None"
            ) or (ai_summary and str(ai_summary).strip() and ai_summary != "None")

            if not has_analysis:
                unanalyzed_posts.append(post)

        return len(unanalyzed_posts), unanalyzed_posts[:5]  # Return count and sample

    except Exception as e:
        st.error(f"Error checking unanalyzed posts: {e}")
        return 0, []


def render_analysis_reminder():
    """Render a reminder banner for unanalyzed posts"""
    unanalyzed_count, sample_posts = check_unanalyzed_posts()

    # Check if user dismissed the reminder for this session
    if "analysis_reminder_dismissed" not in st.session_state:
        st.session_state.analysis_reminder_dismissed = False

    if unanalyzed_count > 0 and not st.session_state.analysis_reminder_dismissed:
        # Create a container with banner and action buttons
        with st.container():
            col1, col2, col3 = st.columns([4, 1, 1])

            with col1:
                st.markdown(
                    """
                <div style="background: linear-gradient(90deg, #ff6b6b, #ff8e8e); padding: 15px; border-radius: 10px; margin: 10px 0; border-left: 5px solid #ff4757;">
                    <h4 style="color: white; margin: 0; display: flex; align-items: center;">
                        🔔 <span style="margin-left: 10px;">You have {count} unanalyzed posts waiting for AI analysis!</span>
                    </h4>
                    <p style="color: white; margin: 5px 0 0 35px; font-size: 14px;">
                        Process your new bookmarks to get AI insights, summaries, and value scores.
                    </p>
                </div>
                """.format(count=unanalyzed_count),
                    unsafe_allow_html=True,
                )

            with col2:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("🤖 Analyze Now", key="quick_analyze_btn", type="primary"):
                    st.info(
                        "Please use the 🎭 Persona Pipeline tab to start analyzing posts."
                    )

            with col3:
                st.write("")  # Spacing
                st.write("")  # Spacing
                if st.button("✕ Dismiss", key="dismiss_reminder_btn"):
                    st.session_state.analysis_reminder_dismissed = True
                    st.rerun()

            # Show sample of unanalyzed posts
            if sample_posts:
                with st.expander(
                    f"📋 Preview of {min(5, len(sample_posts))} unanalyzed posts"
                ):
                    for i, post in enumerate(sample_posts):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            content_preview = post.get("content", "No content")[:100]
                            st.write(
                                f"**{post.get('author', 'Unknown')}** ({post.get('platform', 'Unknown')})"
                            )
                            st.write(
                                f"*{content_preview}{'...' if len(post.get('content', '')) > 100 else ''}*"
                            )
                        with col2:
                            created = (
                                post.get("created_at", "")[:10]
                                if post.get("created_at")
                                else "Unknown"
                            )
                            st.caption(f"📅 {created}")
                        if i < len(sample_posts) - 1:
                            st.divider()


def init_session_state():
    """Initialize the session state variables"""
    if "initialized" not in st.session_state:
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
        result = {"collected": count}

        # Update collection stats
        if "collected" in result:
            st.session_state.collection_stats[platform] = result["collected"]
        return result
    except Exception as e:
        return {"error": f"Error running {platform} collection: {str(e)}"}


async def run_automated_collection():
    """Run automated collection in the background"""
    while st.session_state.automation_enabled:
        try:
            # Run collection for each platform
            for platform in ["twitter", "reddit", "threads"]:
                result = run_collection(platform)
                if "error" in result:
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
        initial_sidebar_state="expanded",
    )

    # Custom CSS for better styling
    st.markdown(
        """
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
    """,
        unsafe_allow_html=True,
    )

    # Top status bar
    render_status_bar()
    
    # Useful sidebar with credentials, stats, and quick actions
    from src.web.components.sidebar_new import render_useful_sidebar
    render_useful_sidebar()

    # Start autoposter worker if enabled (only once per session)
    if "publisher_worker_started" not in st.session_state:
        st.session_state.publisher_worker_started = False

    if (
        os.getenv("AUTO_PUBLISHER_ENABLED", "true").lower() in ("true", "1", "yes")
        and not st.session_state.publisher_worker_started
    ):
        try:
            get_publisher_worker().start()
            st.session_state.publisher_worker_started = True
            # Log to console (Streamlit doesn't show this in UI, but it will appear in terminal)
            import logging

            logging.basicConfig(level=logging.INFO)
            logging.info("🚀 Publisher worker started automatically")
        except Exception as e:
            logging.error(f"Failed to start publisher worker: {e}")

    # Main title
    st.title("🧠 PrisMind - Intelligent Bookmark Platform")
    st.markdown("*Transform your social media bookmarks into structured intelligence*")

    # Check for unanalyzed posts and show reminder
    render_analysis_reminder()

    # New minimal navigation: Feed, Collect, Persona Pipeline, Publishing, Settings
    tab_feed, tab_collect, tab_persona, tab_pub, tab_perf, tab_system, tab_settings = st.tabs(
        ["📰 Feed", "📥 Collect", "🎭 Persona Pipeline", "📝 Publishing", "📈 Perf", "🩺 System", "⚙️ Settings"]
    )

    with tab_feed:
        render_unified_feed()

    with tab_collect:
        render_collection_tab()

    with tab_persona:
        render_persona_pipeline_tab()

    with tab_pub:
        render_publishing_page()

    with tab_perf:
        from src.web.components.publishing_analytics_tab import render_publishing_analytics_tab
        render_publishing_analytics_tab()

    with tab_system:
        render_system_status_tab()

    with tab_settings:
        render_settings_tab()

    # Handle collection triggers
    if st.session_state.get("run_twitter_collection", False):
        with st.spinner("Collecting from Twitter..."):
            result = run_collection("twitter")
            if "error" in result:
                st.error(f"Error collecting from Twitter: {result['error']}")
            else:
                st.success(f"Collected {result.get('collected', 0)} posts from Twitter")
        st.session_state.run_twitter_collection = False

    if st.session_state.get("run_reddit_collection", False):
        with st.spinner("Collecting from Reddit..."):
            result = run_collection("reddit")
            if "error" in result:
                st.error(f"Error collecting from Reddit: {result['error']}")
            else:
                st.success(f"Collected {result.get('collected', 0)} posts from Reddit")
        st.session_state.run_reddit_collection = False

    if st.session_state.get("run_threads_collection", False):
        with st.spinner("Collecting from Threads..."):
            result = run_collection("threads")
            if "error" in result:
                st.error(f"Error collecting from Threads: {result['error']}")
            else:
                st.success(f"Collected {result.get('collected', 0)} posts from Threads")
        st.session_state.run_threads_collection = False

    # Start/stop background collection
    if st.session_state.automation_enabled and not st.session_state.background_running:
        st.session_state.background_running = True
        asyncio.run(run_automated_collection())
    elif (
        not st.session_state.automation_enabled and st.session_state.background_running
    ):
        st.session_state.background_running = False


if __name__ == "__main__":
    main()

    # This ensures the app doesn't run multiple times in Streamlit
    if "main_ran" not in st.session_state:
        st.session_state.main_ran = True
        st.rerun()
