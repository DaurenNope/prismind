"""
New useful sidebar with credentials, stats, and quick actions
"""
import os
import streamlit as st
from pathlib import Path
from datetime import datetime

from src.services.new_database_manager import NewDatabaseManager


def render_useful_sidebar():
    """Render a useful sidebar with credentials, stats, and quick actions"""
    
    # === CREDENTIALS STATUS ===
    st.sidebar.markdown("### 🔐 Credentials")
    
    # Check Twitter
    twitter_username = os.getenv("TWITTER_USERNAME", "")
    twitter_api_key = os.getenv("TWITTER_API_KEY", "")
    twitter_cookies = os.getenv("TWITTER_COOKIES_FILE", "")
    if not twitter_cookies and twitter_username:
        twitter_cookies = f"config/twitter_cookies_{twitter_username}.json"
    
    twitter_configured = twitter_api_key or (twitter_cookies and Path(twitter_cookies).exists())
    if twitter_username:
        twitter_status = f"{'✅' if twitter_configured else '⚠️'} Twitter: {twitter_username}"
    else:
        twitter_status = "❌ Twitter: Not configured"
    st.sidebar.text(twitter_status)
    
    # Check Threads
    threads_username = os.getenv("THREADS_USERNAME", "")
    threads_cookies = os.getenv("THREADS_COOKIES_FILE", "config/threads_cookies.json")
    threads_configured = Path(threads_cookies).exists() if threads_cookies else False
    
    if threads_username:
        threads_status = f"{'✅' if threads_configured else '⚠️'} Threads: {threads_username}"
    else:
        threads_status = "❌ Threads: Not configured"
    st.sidebar.text(threads_status)
    
    # Check Telegram
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_status = f"{'✅' if telegram_token else '❌'} Telegram: {'Configured' if telegram_token else 'Not configured'}"
    st.sidebar.text(telegram_status)
    
    st.sidebar.markdown("---")
    
    # === QUICK STATS ===
    st.sidebar.markdown("### 📊 Quick Stats")
    
    try:
        db_manager = NewDatabaseManager()
        
        # Total posts
        all_posts = db_manager.get_posts(limit=1000)
        total_posts = len(all_posts) if all_posts else 0
        st.sidebar.metric("Total Posts", total_posts)
        
        # Posts by platform
        if all_posts:
            platforms = {}
            for post in all_posts:
                platform = post.get('platform', 'unknown')
                platforms[platform] = platforms.get(platform, 0) + 1
            
            for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True)[:3]:
                st.sidebar.caption(f"  {platform.title()}: {count}")
        
        # Scheduled posts
        try:
            from src.database.publishing.bridge import MimesisDB
            db = MimesisDB()
            due_posts = db.list_due_posts()
            scheduled = db.list_scheduled_posts()
            pending = [p for p in scheduled if p.get('status') not in ['posted', 'failed']]
            
            st.sidebar.metric("Scheduled Posts", len(pending))
            if due_posts:
                st.sidebar.caption(f"  {len(due_posts)} due now")
        except:
            st.sidebar.caption("Scheduled: N/A")
    
    except Exception as e:
        st.sidebar.caption(f"Stats: Error loading")
    
    st.sidebar.markdown("---")
    
    # === QUICK ACTIONS ===
    st.sidebar.markdown("### ⚡ Quick Actions")
    
    if st.sidebar.button("📥 Collect All", use_container_width=True):
        st.session_state.collect_all_platforms = True
    
    if st.sidebar.button("📝 New Post", use_container_width=True):
        st.session_state.jump_to_publishing = True
    
    st.sidebar.markdown("---")
    
    # === SYSTEM INFO ===
    st.sidebar.markdown("### ℹ️ System")
    
    # Worker status
    worker_interval = os.getenv("PUBLISHER_WORKER_INTERVAL", "15")
    st.sidebar.caption(f"Worker interval: {worker_interval}s")
    
    # Supabase status
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_status = "✅" if supabase_url else "❌"
    st.sidebar.caption(f"Supabase: {supabase_status}")
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"PrisMind v1.0")

