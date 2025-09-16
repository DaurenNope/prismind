#!/usr/bin/env python3
"""
🧠 PrisMind - Personal Intelligence Engine
========================================

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
from src.web.components.dashboard import render_dashboard
from src.services.collection_service import (
    run_twitter_collection,
    run_reddit_collection,
    run_threads_collection
)

# Load environment variables from .env file
load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Database manager
class InMemoryDatabaseManager:
    """Simple in-memory storage for demo purposes"""
    def __init__(self):
        self.posts = []
    
    def get_all_posts(self, include_deleted=False):
        return [p for p in self.posts if include_deleted or not p.get('deleted', False)]
    
    def get_posts(self, limit=100):
        return self.get_all_posts()[:limit]
    
    def add_post(self, post_data):
        post_data['id'] = len(self.posts) + 1
        post_data['created_at'] = datetime.now().isoformat()
        self.posts.append(post_data)
        return post_data

# Initialize database manager
db_manager = InMemoryDatabaseManager()

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

def run_collection(platform: str) -> dict:
    """Run collection for a specific platform"""
    try:
        if platform == 'twitter':
            result = run_twitter_collection()
        elif platform == 'reddit':
            result = run_reddit_collection()
        elif platform == 'threads':
            result = run_threads_collection()
        else:
            return {'error': f'Unsupported platform: {platform}'}
        
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

def render_dashboard():
    """Render the dashboard view"""
    st.header("📊 Intelligence Dashboard")
    
    # Get posts data
    posts = db_manager.get_all_posts()
    
    if posts:
        df = pd.DataFrame(posts)
        
        # Calculate metrics
        total_posts = len(df)
        ai_analyzed = len(df[df.get('ai_analyzed', False)])
        avg_score = df.get('score', pd.Series([0])).mean()
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📚 Total Posts", total_posts)
        with col2:
            st.metric("🤖 AI Analyzed", f"{ai_analyzed} ({int((ai_analyzed/total_posts)*100)}%)" if total_posts > 0 else "0 (0%)")
        with col3:
            st.metric("🌐 Platforms", df['platform'].nunique() if 'platform' in df.columns else 0)
        with col4:
            st.metric("⭐ Avg Score", f"{avg_score:.1f}/10" if 'score' in df.columns else "N/A")
        
        # Platform distribution
        st.subheader("📈 Platform Distribution")
        if 'platform' in df.columns:
            platform_counts = df['platform'].value_counts()
            st.bar_chart(platform_counts)
            
            # Display platform counts
            for platform, count in platform_counts.items():
                st.write(f"- {platform}: {count}")
        
        # Recent posts
        st.subheader("🆕 Recent Posts")
        recent_posts = df.sort_values('created_at', ascending=False).head(5)
        for _, post in recent_posts.iterrows():
            st.write(f"**{post.get('title', 'No title')}**")
            st.caption(f"From {post.get('platform', 'unknown')} • {post.get('created_at', '')}")
            st.write("---")
    else:
        st.info("No posts found. Try collecting some posts first!")

def render_browse():
    """Render the browse posts view"""
    st.header("🎯 Browse Posts")
    st.write("Browse and filter your collected posts.")
    
    # Add filtering options
    st.subheader("🔍 Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        platform_filter = st.multiselect(
            "Filter by Platform",
            options=["Twitter", "Reddit", "Threads"],
            default=[]
        )
    
    with col2:
        date_filter = st.date_input(
            "Filter by Date",
            value=[datetime.now().date() - timedelta(days=7), datetime.now().date()],
            max_value=datetime.now().date(),
            key="date_filter"
        )
    
    # Add search functionality
    search_query = st.text_input("Search posts", "", placeholder="Enter keywords to search...")
    
    # Display filtered posts
    st.subheader("📝 Posts")
    st.write("Post list will be displayed here based on filters.")

def render_settings():
    """Render the settings view"""
    st.header("⚙️ Settings")
    
    # General Settings
    with st.expander("General Settings", expanded=True):
        st.selectbox("Theme", ["Light", "Dark", "System"], key="theme_setting")
        st.slider("Posts per page", 10, 100, 20, key="posts_per_page")
    
    # API Settings
    with st.expander("API Settings"):
        st.text_input("Reddit API Key", type="password", key="reddit_api_key")
        st.text_input("Twitter API Key", type="password", key="twitter_api_key")
    
    # Save settings button
    if st.button("💾 Save Settings"):
        st.success("Settings saved successfully!")

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
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🎯 Browse Posts", "⚙️ Settings"])
    
    with tab1:
        render_dashboard()
    
    with tab2:
        render_browse()
    
    with tab3:
        render_settings()
    
    # Handle collection triggers
    if st.session_state.get('run_twitter_collection', False):
        with st.spinner("Collecting from Twitter..."):
            result = run_twitter_collection()
            if 'error' in result:
                st.error(f"Error collecting from Twitter: {result['error']}")
            else:
                st.success(f"Collected {result.get('collected', 0)} posts from Twitter")
        st.session_state.run_twitter_collection = False
    
    if st.session_state.get('run_reddit_collection', False):
        with st.spinner("Collecting from Reddit..."):
            result = run_reddit_collection()
            if 'error' in result:
                st.error(f"Error collecting from Reddit: {result['error']}")
            else:
                st.success(f"Collected {result.get('collected', 0)} posts from Reddit")
        st.session_state.run_reddit_collection = False
    
    if st.session_state.get('run_threads_collection', False):
        with st.spinner("Collecting from Threads..."):
            result = run_threads_collection()
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
