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

# Configure Streamlit page BEFORE importing any modules that might call Streamlit
st.set_page_config(
    page_title="🧠 PrisMind - Intelligence Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Add the project root to the Python path before importing internal packages
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
    print(f"Added to path: {project_root}")

from src.utils.logging_config import get_logger

# Import components
from src.web.components.status_bar import render_status_bar
from src.web.components.tabs import render_settings_tab
from src.web.components.unified_feed_tab import render_unified_feed
from src.web.components.publishing_page import render_publishing_page
from src.web.components.collection_tab import render_collection_tab
from src.web.components.analysis_tab import render_analysis_tab
from src.web.components.dashboard_tab import render_dashboard_tab
from src.web.components.rewriter_lab_tab import render_rewriter_lab_tab
from src.web.components.profile_manager_tab import render_profile_manager_tab
from src.web.components.profile_wizard_tab import render_profile_wizard_tab
from src.web.components.daily_builder_tab import render_daily_builder_tab
from src.web.components.feedback_tab import render_feedback_tab
from src.web.components.diary_tab import render_diary_tab
from src.web.components.production_pipeline_tab import render_production_pipeline_tab
from src.pipeline.orchestrator import get_orchestrator
from src.publishing.worker import get_publisher_worker

# Load environment variables from .env file
load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

# Use shared database manager
from src.services.new_database_manager import get_database_manager as _get_db_manager


logger = get_logger(__name__)


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
                    # Trigger in-app analysis with orchestrator
                    st.session_state.run_global_analysis = True

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
            # Check cancel
            try:
                from src.services.cancel_manager import is_cancelled
                if is_cancelled("all"):
                    break
            except Exception:
                pass
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

    # Professional, clean CSS that works with Streamlit's dark mode
    st.markdown(
        """
    <style>
        /* Force light theme for better visibility */
        .stApp {
            background-color: #ffffff !important;
        }
        
        /* Main content area */
        .main .block-container {
            background-color: #ffffff !important;
            color: #1f2937 !important;
            padding: 2rem;
        }
        
        /* All text elements - ensure visibility */
        h1, h2, h3, h4, h5, h6, p, span, div, label, .stMarkdown, .stText {
            color: #1f2937 !important;
        }
        
        /* Headers - clean and professional */
        h1 {
            color: #111827 !important;
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 1rem;
        }
        
        h2 {
            color: #111827 !important;
            font-size: 1.5rem;
            font-weight: 600;
            margin-top: 2rem;
            margin-bottom: 1rem;
        }
        
        h3 {
            color: #374151 !important;
            font-size: 1.25rem;
            font-weight: 600;
        }

        /* Metrics - clean and readable */
        [data-testid="stMetricValue"] {
            font-size: 2rem !important;
            font-weight: 700 !important;
            color: #111827 !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.875rem !important;
            color: #6b7280 !important;
            font-weight: 500;
        }

        /* Buttons - professional, minimal */
        .stButton > button {
            background-color: #2563eb !important;
            color: #ffffff !important;
            border: 1px solid #2563eb !important;
            border-radius: 6px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            font-size: 0.875rem;
            transition: background-color 0.2s;
        }

        .stButton > button:hover {
            background-color: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
        }

        .stButton > button[kind="secondary"] {
            background-color: #f9fafb !important;
            color: #374151 !important;
            border: 1px solid #d1d5db !important;
        }

        .stButton > button[kind="secondary"]:hover {
            background-color: #f3f4f6 !important;
        }

        /* Input fields - clean borders */
        .stSelectbox > div > div {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            border-radius: 6px;
            color: #111827 !important;
        }
        
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            background-color: #ffffff !important;
            border: 1px solid #d1d5db !important;
            color: #111827 !important;
        }
        
        .stSelectbox label,
        .stTextInput label,
        .stTextArea label {
            color: #374151 !important;
            font-weight: 500;
        }

        /* Expanders */
        .streamlit-expanderHeader {
            background-color: #f9fafb !important;
            border: 1px solid #e5e7eb !important;
            border-radius: 6px;
            padding: 0.75rem 1rem;
            color: #111827 !important;
        }

        .streamlit-expanderHeader:hover {
            background-color: #f3f4f6 !important;
        }

        /* Dividers - subtle */
        hr {
            border: none;
            height: 1px;
            background-color: #e5e7eb;
            margin: 2rem 0;
        }

        /* Progress bars - subtle blue */
        .stProgress > div > div > div {
            background-color: #2563eb !important;
        }

        /* Alerts - clean and professional */
        .stAlert {
            border-radius: 6px;
            border-left: 4px solid;
            padding: 1rem;
            background-color: #f9fafb !important;
        }

        .stAlert[data-base="info"] {
            border-left-color: #3b82f6;
            background-color: #eff6ff !important;
            color: #1e40af !important;
        }

        .stAlert[data-base="success"] {
            border-left-color: #10b981;
            background-color: #f0fdf4 !important;
            color: #065f46 !important;
        }

        .stAlert[data-base="warning"] {
            border-left-color: #f59e0b;
            background-color: #fffbeb !important;
            color: #92400e !important;
        }

        .stAlert[data-base="error"] {
            border-left-color: #ef4444;
            background-color: #fef2f2 !important;
            color: #991b1b !important;
        }
        
        /* Dataframes - clean tables */
        .stDataFrame {
            background-color: #ffffff !important;
        }
        
        /* Sidebar - light background */
        [data-testid="stSidebar"] {
            background-color: #f9fafb !important;
        }
        
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #111827 !important;
        }
        
        [data-testid="stSidebar"] .stMetric [data-testid="stMetricValue"] {
            color: #111827 !important;
        }
        
        [data-testid="stSidebar"] .stMetric [data-testid="stMetricLabel"] {
            color: #6b7280 !important;
        }

        /* Tabs - clean and minimal */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0.25rem;
            border-bottom: 2px solid #e5e7eb;
        }

        .stTabs [data-baseweb="tab"] {
            padding: 0.75rem 1.5rem;
            font-weight: 500;
            color: #6b7280 !important;
            border-bottom: 2px solid transparent;
        }

        .stTabs [aria-selected="true"] {
            background-color: transparent !important;
            color: #111827 !important;
            border-bottom-color: #2563eb !important;
            font-weight: 600;
        }

        /* Hero Section - minimal, no gradients */
        .hero-section {
            background-color: #f9fafb;
            padding: 2rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            text-align: center;
            border: 1px solid #e5e7eb;
        }

        .hero-title {
            color: #111827 !important;
            margin: 0;
            font-size: 2rem;
            font-weight: 700;
        }

        .hero-subtitle {
            color: #6b7280 !important;
            font-size: 1rem;
            margin-top: 0.5rem;
        }
        
        /* Code blocks */
        .stCodeBlock {
            background-color: #f9fafb !important;
            border: 1px solid #e5e7eb !important;
        }
        
        /* Captions and labels */
        .stCaption {
            color: #6b7280 !important;
        }
        
        /* Remove any gradient backgrounds */
        * {
            background-image: none !important;
        }
        
        /* Ensure Streamlit default elements use light theme */
        section[data-testid="stSidebar"] {
            background-color: #f9fafb !important;
        }
        
        /* Make sure all text in sidebar is readable */
        section[data-testid="stSidebar"] * {
            color: #111827 !important;
        }
        
        /* Ensure selectboxes and dropdowns are visible */
        .stSelectbox [data-baseweb="select"] {
            background-color: #ffffff !important;
        }
        
        /* Tables and dataframes */
        table {
            background-color: #ffffff !important;
            color: #111827 !important;
        }
        
        /* Ensure all Streamlit widgets are visible */
        .element-container {
            color: #111827 !important;
        }
        
        /* JSON displays */
        .stJson {
            background-color: #f9fafb !important;
            border: 1px solid #e5e7eb !important;
        }
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
            logger.debug("🚀 Publisher worker started automatically")
        except Exception as e:
            logger.error(f"Failed to start publisher worker: {e}")

    # Minimal Hero Section - professional and clean
    st.markdown("""
    <div class="hero-section">
        <h1 class="hero-title">PrisMind</h1>
        <p class="hero-subtitle">Transform your social media bookmarks into structured intelligence</p>
    </div>
    """, unsafe_allow_html=True)

    # Check for unanalyzed posts and show reminder
    render_analysis_reminder()

    # Simplified tab structure - removed Persona Pipeline, Perf, System, Sources (merged into Settings)
    tab_dashboard, tab_feed, tab_diary, tab_daily, tab_pipeline, tab_collect, tab_analysis, tab_pub, tab_rewriter_lab, tab_wizard, tab_profile_mgr, tab_feedback, tab_settings = st.tabs(
        ["📊 Dashboard", "📰 Feed", "📓 Diary", "🏗️ Daily", "🚀 Pipeline", "📥 Collect", "🤖 Analysis", "📝 Publishing", "🔬 Rewriter Lab", "🧙 AI Wizard", "👤 Profiles", "📝 Feedback", "⚙️ Settings"]
    )

    with tab_dashboard:
        render_dashboard_tab()

    with tab_feed:
        render_unified_feed()

    with tab_diary:
        render_diary_tab()

    with tab_daily:
        render_daily_builder_tab()

    with tab_pipeline:
        render_production_pipeline_tab()

    with tab_collect:
        render_collection_tab()

    with tab_analysis:
        render_analysis_tab()

    with tab_pub:
        render_publishing_page()

    with tab_rewriter_lab:
        render_rewriter_lab_tab()

    with tab_wizard:
        render_profile_wizard_tab()

    with tab_profile_mgr:
        render_profile_manager_tab()

    with tab_feedback:
        render_feedback_tab()

    with tab_settings:
        render_settings_tab()

    # Handle global analysis trigger
    if st.session_state.get("run_global_analysis", False):
        try:
            with st.spinner("Analyzing recent posts with AI..."):
                orch = get_orchestrator()
                analyzed = asyncio.run(orch.analyze_batch(limit=st.session_state.get("analysis_batch_size", 10)))
            st.success(f"Analyzed {analyzed} posts")
        except Exception as e:
            st.error(f"Analysis failed: {e}")
        finally:
            st.session_state.run_global_analysis = False

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
