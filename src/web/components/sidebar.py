"""
Sidebar components for the PrisMind dashboard
"""
import streamlit as st
from datetime import datetime


def render_sidebar():
    """Render the sidebar with navigation and settings"""
    with st.sidebar:
        st.title("🤖 Automation Hub")
        
        # System status
        st.subheader("📊 System Status")
        
        # Collection status
        if 'last_collection' in st.session_state:
            last_collection = st.session_state.last_collection
            if isinstance(last_collection, str):
                last_collection = datetime.fromisoformat(last_collection)
            st.caption(f"Last collection: {last_collection.strftime('%Y-%m-%d %H:%M') if last_collection else 'Never'}")
        
        # Collection stats
        if 'collection_stats' in st.session_state:
            stats = st.session_state.collection_stats
            if stats:
                st.caption("Last collection stats:")
                for platform, count in stats.items():
                    st.caption(f"- {platform.capitalize()}: {count} posts")
        
        # Automation controls
        st.subheader("⚙️ Automation")
        
        # Toggle for background collection
        automation_enabled = st.toggle(
            "Enable background collection",
            value=st.session_state.get('automation_enabled', False),
            help="Enable to automatically collect posts in the background"
        )
        
        if automation_enabled != st.session_state.get('automation_enabled'):
            st.session_state.automation_enabled = automation_enabled
            st.rerun()
        
        # Collection interval
        collection_interval = st.number_input(
            "Collection interval (minutes)",
            min_value=1,
            max_value=1440,
            value=60,
            help="How often to collect new posts (in minutes)"
        )
        
        # Manual collection buttons
        st.subheader("🔄 Manual Collection")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🕵️‍♂️ Collect from Twitter"):
                st.session_state.run_twitter_collection = True
                st.rerun()
            
            if st.button("📱 Collect from Threads"):
                st.session_state.run_threads_collection = True
                st.rerun()
        
        with col2:
            if st.button("📰 Collect from Reddit"):
                st.session_state.run_reddit_collection = True
                st.rerun()
        
        # Settings
        st.subheader("⚙️ Settings")
        
        # Theme selector
        theme = st.selectbox(
            "Theme",
            ["Light", "Dark", "System"],
            index=0,
            help="Change the app's color theme"
        )
        
        # Show advanced settings
        if st.checkbox("Show advanced settings"):
            st.text_area("Configuration", value="Add your configuration here")
        
        # Footer
        st.markdown("---")
        st.caption("PrisMind v1.0.0")
        st.caption("© 2023 PrisMind Team")
