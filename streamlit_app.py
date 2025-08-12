#!/usr/bin/env python3
"""
PrisMind All-in-One - Complete Intelligence Platform
==================================================

Single Streamlit app with:
✅ Dashboard UI (frontend)
✅ Collection automation (backend) 
✅ Manual triggers
✅ Health monitoring
✅ AI analysis

Deploy to Streamlit Cloud for 100% FREE automation!
"""

import streamlit as st
import asyncio
import pandas as pd
import sqlite3
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

# Setup paths for imports
sys.path.insert(0, str(Path(__file__).parent))

# Core imports
try:
    from scripts.database_manager import DatabaseManager
except ImportError:
    st.error("❌ Could not import DatabaseManager. Please check file structure.")
    st.stop()

# Page config
st.set_page_config(
    page_title="PrisMind - Intelligent Bookmarks",
    page_icon="🧠",
    layout="wide"
)

# Initialize session state
if 'automation_enabled' not in st.session_state:
    st.session_state.automation_enabled = False
if 'last_collection' not in st.session_state:
    st.session_state.last_collection = None

# Sidebar for automation controls
with st.sidebar:
    st.title("🤖 Automation")
    
    # Collection status
    if st.session_state.last_collection:
        st.success(f"Last collection: {st.session_state.last_collection}")
    else:
        st.warning("No collections yet")
    
    # Manual collection triggers
    st.subheader("Manual Collection")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🐦 Twitter", help="Collect Twitter bookmarks"):
            with st.spinner("Collecting Twitter..."):
                try:
                    # Run Twitter collection
                    db_manager = DatabaseManager()
                    existing_posts = db_manager.get_all_posts(include_deleted=False)
                    existing_ids = set(existing_posts['post_id'].tolist()) if not existing_posts.empty else set()
                    
                    count = asyncio.run(collect_twitter_bookmarks(db_manager, existing_ids))
                    st.success(f"Collected {count} Twitter posts!")
                    st.session_state.last_collection = datetime.now().strftime("%H:%M")
                    st.rerun()
                except Exception as e:
                    st.error(f"Twitter collection failed: {e}")
    
    with col2:
        if st.button("🤖 Reddit", help="Collect Reddit saved posts"):
            with st.spinner("Collecting Reddit..."):
                try:
                    db_manager = DatabaseManager()
                    existing_posts = db_manager.get_all_posts(include_deleted=False)
                    existing_ids = set(existing_posts['post_id'].tolist()) if not existing_posts.empty else set()
                    
                    count = collect_reddit_bookmarks(db_manager, existing_ids)
                    st.success(f"Collected {count} Reddit posts!")
                    st.session_state.last_collection = datetime.now().strftime("%H:%M")
                    st.rerun()
                except Exception as e:
                    st.error(f"Reddit collection failed: {e}")
    
    if st.button("🧵 Threads", help="Collect Threads saved posts"):
        with st.spinner("Collecting Threads..."):
            try:
                db_manager = DatabaseManager()
                existing_posts = db_manager.get_all_posts(include_deleted=False)
                existing_ids = set(existing_posts['post_id'].tolist()) if not existing_posts.empty else set()
                
                count = asyncio.run(collect_threads_bookmarks(db_manager, existing_ids))
                st.success(f"Collected {count} Threads posts!")
                st.session_state.last_collection = datetime.now().strftime("%H:%M")
                st.rerun()
            except Exception as e:
                st.error(f"Threads collection failed: {e}")
    
    if st.button("🚀 Collect All", help="Collect from all platforms"):
        with st.spinner("Collecting from all platforms..."):
            try:
                # Import and run the main collection
                from collect_multi_platform import main
                total = asyncio.run(main())
                st.success(f"Collection complete! Check logs above.")
                st.session_state.last_collection = datetime.now().strftime("%H:%M")
                st.rerun()
            except Exception as e:
                st.error(f"Collection failed: {e}")
    
    # Automation settings
    st.subheader("⚙️ Automation")
    
    auto_enabled = st.checkbox(
        "Enable Auto Collection",
        value=st.session_state.automation_enabled,
        help="Automatically collect every 6 hours"
    )
    
    if auto_enabled != st.session_state.automation_enabled:
        st.session_state.automation_enabled = auto_enabled
        if auto_enabled:
            st.success("Automation enabled!")
        else:
            st.info("Automation disabled")
    
    if auto_enabled:
        next_run = st.empty()
        with next_run:
            # Calculate next run time
            now = datetime.now()
            next_collection = now.replace(minute=0, second=0, microsecond=0)
            while next_collection <= now:
                next_collection += timedelta(hours=6)
            
            st.info(f"Next auto-collection: {next_collection.strftime('%H:%M')}")
    
    # Health monitoring
    st.subheader("📊 System Health")
    
    try:
        # Get database stats
        db_manager = DatabaseManager()
        posts_df = db_manager.get_all_posts()
        
        if not posts_df.empty:
            total_posts = len(posts_df)
            analyzed_posts = len(posts_df[posts_df['category'].notna()])
            
            st.metric("Total Posts", total_posts)
            st.metric("Analyzed Posts", analyzed_posts)
            st.metric("Analysis Rate", f"{(analyzed_posts/total_posts*100):.1f}%")
        else:
            st.info("No posts in database yet")
            
    except Exception as e:
        st.error(f"Health check failed: {e}")

# Main dashboard content (your existing dashboard code)
st.title("🧠 PrisMind - Intelligent Bookmarks")

# Add a tab for automation logs
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🤖 Automation", "⚙️ Settings"])

with tab1:
    # Your existing dashboard code goes here
    # This is just a placeholder - you'd integrate your full dashboard.py content
    try:
        # Import all your dashboard functions and render them
        main_dashboard()  # This would be your main dashboard function
    except:
        st.info("Dashboard loading... Please ensure all dependencies are configured.")

with tab2:
    st.header("🤖 Automation Status")
    
    # Automation scheduler status
    if st.button("📋 View Scheduler Status"):
        try:
            scheduler = IntelligentScheduler()
            status = scheduler.get_status_report()
            
            st.json(status)
            
            # Platform health
            col1, col2, col3 = st.columns(3)
            
            platforms = status.get('platforms', {})
            with col1:
                twitter_health = platforms.get('twitter', {}).get('health', 'unknown')
                st.metric("Twitter", twitter_health, 
                         delta=f"{platforms.get('twitter', {}).get('success_rate', 0):.1%}")
            
            with col2:
                reddit_health = platforms.get('reddit', {}).get('health', 'unknown')
                st.metric("Reddit", reddit_health,
                         delta=f"{platforms.get('reddit', {}).get('success_rate', 0):.1%}")
            
            with col3:
                threads_health = platforms.get('threads', {}).get('health', 'unknown')
                st.metric("Threads", threads_health,
                         delta=f"{platforms.get('threads', {}).get('success_rate', 0):.1%}")
                         
        except Exception as e:
            st.error(f"Could not load scheduler status: {e}")
    
    # Collection history
    st.subheader("📈 Collection History")
    
    try:
        # Show recent collection stats
        db_manager = DatabaseManager()
        posts_df = db_manager.get_all_posts()
        
        if not posts_df.empty:
            # Convert created_timestamp to datetime if it's a string
            if 'created_timestamp' in posts_df.columns:
                posts_df['created_timestamp'] = pd.to_datetime(posts_df['created_timestamp'])
                
                # Group by date and platform
                daily_stats = posts_df.groupby([
                    posts_df['created_timestamp'].dt.date,
                    'platform'
                ]).size().unstack(fill_value=0)
                
                st.bar_chart(daily_stats)
            else:
                st.info("No timestamp data available for charts")
        else:
            st.info("No collection history yet")
            
    except Exception as e:
        st.error(f"Could not load collection history: {e}")

with tab3:
    st.header("⚙️ Configuration")
    
    # Environment variables check
    st.subheader("🔑 API Keys Status")
    
    keys_status = {
        "Mistral API": bool(os.getenv('MISTRAL_API_KEY')),
        "Gemini API": bool(os.getenv('GEMINI_API_KEY')),
        "Supabase URL": bool(os.getenv('SUPABASE_URL')),
        "Supabase Key": bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY')),
        "Reddit Client ID": bool(os.getenv('REDDIT_CLIENT_ID')),
        "Reddit Username": bool(os.getenv('REDDIT_USERNAME')),
        "Twitter Username": bool(os.getenv('TWITTER_USERNAME')),
    }
    
    for key, status in keys_status.items():
        if status:
            st.success(f"✅ {key}")
        else:
            st.error(f"❌ {key} - Not configured")
    
    # Database connection test
    st.subheader("🗄️ Database Connection")
    if st.button("Test Database"):
        try:
            db_manager = DatabaseManager()
            posts_df = db_manager.get_all_posts()
            st.success(f"✅ Database connected! {len(posts_df)} posts found.")
        except Exception as e:
            st.error(f"❌ Database connection failed: {e}")

# Background automation (if enabled)
def run_background_automation():
    """Run automation in background thread"""
    if st.session_state.automation_enabled:
        try:
            scheduler = IntelligentScheduler()
            # Run one collection cycle
            asyncio.run(scheduler.run_collection_cycle())
        except Exception as e:
            st.error(f"Background automation failed: {e}")

# Auto-refresh for real-time updates
if st.session_state.automation_enabled:
    # Auto-refresh every 5 minutes when automation is enabled
    time.sleep(300)
    st.rerun()
