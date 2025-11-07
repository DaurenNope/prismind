"""
New useful sidebar with credentials, stats, and quick actions
"""
import os
import streamlit as st
from pathlib import Path
from datetime import datetime

from src.services.new_database_manager import NewDatabaseManager
from src.database.database_agent import DatabaseAgent


def render_useful_sidebar():
    """Render a useful sidebar with credentials, stats, and quick actions"""
    
    # === CREDENTIALS STATUS ===
    st.sidebar.markdown("### 🔐 Credentials")
    
    # Check Twitter
    twitter_username = os.getenv("TWITTER_USERNAME", "")
    twitter_api_key = os.getenv("TWITTER_API_KEY", "")
    # Prefer TWITTER_COOKIE_FILE; support legacy TWITTER_COOKIES_FILE
    twitter_cookies = os.getenv("TWITTER_COOKIE_FILE", "") or os.getenv("TWITTER_COOKIES_FILE", "")
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
        agent = DatabaseAgent()
        
        # Total posts
        all_posts = db_manager.get_posts(limit=1000)
        total_posts = len(all_posts) if all_posts else 0
        st.sidebar.metric("Total Posts", total_posts)

        # Unanalyzed posts
        unanalyzed = 0
        with_personas = 0
        for post in all_posts or []:
            analyzed_at = post.get("analyzed_at") or post.get("analysis_timestamp")
            ai_summary = post.get("ai_summary") or post.get("summary") or post.get("content_summary")
            has_analysis = (analyzed_at and str(analyzed_at).strip() and analyzed_at != "None") or (ai_summary and str(ai_summary).strip() and ai_summary != "None")
            if not has_analysis:
                unanalyzed += 1

            rp = post.get("recommended_personas")
            pms = post.get("persona_match_scores")
            if isinstance(rp, str):
                import json
                try:
                    rp = json.loads(rp)
                except Exception:
                    rp = []
            if isinstance(pms, str):
                import json
                try:
                    pms = json.loads(pms)
                except Exception:
                    pms = {}
            if (isinstance(rp, list) and len(rp) > 0) or (isinstance(pms, dict) and len(pms) > 0):
                with_personas += 1

        st.sidebar.caption(f"Unanalyzed: {unanalyzed} | With personas: {with_personas}")
        
        # Posts by platform
        if all_posts:
            platforms = {}
            for post in all_posts:
                platform = post.get('platform', 'unknown')
                platforms[platform] = platforms.get(platform, 0) + 1
            
            for platform, count in sorted(platforms.items(), key=lambda x: x[1], reverse=True)[:3]:
                st.sidebar.caption(f"  {platform.title()}: {count}")
        
        # Collection freshness (compact)
        try:
            metrics = [
                (plat, (agent.get_collection_metrics(plat) or {}).get("last_run_at") or "-")
                for plat in ["twitter", "reddit", "threads"]
            ]
            st.sidebar.caption("Last collections:")
            for plat, ts in metrics:
                st.sidebar.caption(f"  {plat.title()}: {ts}")
        except Exception:
            pass
        
        # Scheduled posts
        try:
            from src.database.publishing.bridge import MimesisDB
            db = MimesisDB()
            scheduled = db.list_scheduled_posts()
            pending = [p for p in scheduled if p.get('status') == 'pending']
            retry = [p for p in scheduled if p.get('status') == 'retry']
            posted = [p for p in scheduled if p.get('status') == 'posted']
            due_posts = db.list_due_posts()

            st.sidebar.metric("Scheduled Pending", len(pending))
            st.sidebar.caption(f"Retry: {len(retry)} | Posted: {len(posted)}")
            if due_posts:
                st.sidebar.caption(f"  {len(due_posts)} due now")
        except Exception:
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

    # Supabase status (ping)
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_status = "❌"
    if supabase_url:
        try:
            # lightweight ping via list last post id
            _ = NewDatabaseManager().get_posts(limit=1)
            supabase_status = "✅"
        except Exception:
            supabase_status = "⚠️"
    st.sidebar.caption(f"Supabase: {supabase_status}")

    # Cookie freshness
    try:
        tw = os.getenv("TWITTER_COOKIE_FILE", "config/twitter_cookies.json")
        th = os.getenv("THREADS_COOKIES_FILE", "config/threads_cookies.json")
        for label, path in [("Twitter", tw), ("Threads", th)]:
            p = Path(path)
            if p.exists():
                age_min = int((datetime.now().timestamp() - p.stat().st_mtime) / 60)
                icon = "⚠️" if age_min > 240 else "✅"
                st.sidebar.caption(f"{icon} {label} cookies: ~{age_min} min")
            else:
                st.sidebar.caption(f"❌ {label} cookies: missing")
    except Exception:
        pass
    
    # === AUTOMATION CONTROLS ===
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Automation")
    
    # Toggle for background collection
    automation_enabled = st.sidebar.toggle(
        "Background collection",
        value=st.session_state.get('automation_enabled', False),
        help="Enable to automatically collect posts in the background"
    )
    
    if automation_enabled != st.session_state.get('automation_enabled'):
        st.session_state.automation_enabled = automation_enabled
        st.rerun()
    
    # Collection interval
    if automation_enabled:
        collection_interval = st.sidebar.number_input(
            "Interval (minutes)",
            min_value=1,
            max_value=1440,
            value=60,
            help="How often to collect new posts",
            key="collection_interval"
        )
        st.session_state.collection_interval = collection_interval
    
    st.sidebar.markdown("---")
    st.sidebar.caption(f"PrisMind v1.0")

