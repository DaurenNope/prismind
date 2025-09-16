"""
Dashboard components for the PrisMind application
"""
import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional


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


def render_posts_tab():
    """Render the posts tab with filtering and pagination"""
    from src.services.database_manager import get_database_manager
    
    # Get posts from database
    db = get_database_manager()
    posts_df = db.get_posts(limit=1000)  # Adjust limit as needed
    
    if posts_df is None or posts_df.empty:
        st.info("No posts found. Try collecting some posts first!")
        return
    
    # Search and filters
    st.subheader("🔍 Search & Filters")
    
    # Search bar
    search_query = st.text_input("Search posts", "", placeholder="Search by content, tags, etc.")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Platform filter
        platforms = ["All"] + sorted(posts_df['platform'].dropna().unique().tolist())
        selected_platform = st.selectbox("Platform", platforms, index=0)
    
    with col2:
        # Date range filter
        date_range = st.selectbox(
            "Date range",
            ["All time", "Last 7 days", "Last 30 days", "Last 90 days"]
        )
    
    with col3:
        # Sort order
        sort_order = st.selectbox(
            "Sort by",
            ["Newest first", "Oldest first", "Most relevant"]
        )
    
    # Apply filters
    if selected_platform != "All":
        posts_df = posts_df[posts_df['platform'] == selected_platform]
    
    # Apply search
    if search_query:
        search_columns = ['content', 'title', 'tags', 'author']
        search_columns = [col for col in search_columns if col in posts_df.columns]
        
        if search_columns:
            mask = posts_df[search_columns].apply(
                lambda x: x.astype(str).str.contains(search_query, case=False, na=False)
            ).any(axis=1)
            posts_df = posts_df[mask]
    
    # Apply date range filter
    if date_range != "All time" and 'created_at' in posts_df.columns:
        try:
            posts_df['created_at'] = pd.to_datetime(posts_df['created_at'])
            if date_range == "Last 7 days":
                cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=7)
                posts_df = posts_df[posts_df['created_at'] >= cutoff_date]
            elif date_range == "Last 30 days":
                cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=30)
                posts_df = posts_df[posts_df['created_at'] >= cutoff_date]
            elif date_range == "Last 90 days":
                cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=90)
                posts_df = posts_df[posts_df['created_at'] >= cutoff_date]
        except Exception as e:
            st.error(f"Error filtering by date: {e}")
    
    # Apply sorting
    if 'created_at' in posts_df.columns and sort_order != "Most relevant":
        ascending = sort_order == "Oldest first"
        posts_df = posts_df.sort_values('created_at', ascending=ascending)
    
    # Display posts
    if posts_df.empty:
        st.info("No posts match your filters.")
        return
    
    # Pagination
    posts_per_page = 10
    total_pages = (len(posts_df) - 1) // posts_per_page + 1
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    
    # Page controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⏮️ First") and st.session_state.current_page > 0:
            st.session_state.current_page = 0
            st.rerun()
    
    with col2:
        page = st.number_input(
            "Page",
            min_value=1,
            max_value=total_pages,
            value=st.session_state.current_page + 1,
            on_change=lambda: setattr(st.session_state, 'current_page', st.session_state['current_page'])
        )
        
        if page - 1 != st.session_state.current_page:
            st.session_state.current_page = page - 1
            st.rerun()
    
    with col3:
        if st.button("⏭️ Last") and st.session_state.current_page < total_pages - 1:
            st.session_state.current_page = total_pages - 1
            st.rerun()
    
    # Display current page of posts
    start_idx = st.session_state.current_page * posts_per_page
    end_idx = min((st.session_state.current_page + 1) * posts_per_page, len(posts_df))
    current_posts = posts_df.iloc[start_idx:end_idx]
    
    # Reset to first page if current page is out of bounds
    if st.session_state.current_page > 0 and start_idx >= len(posts_df):
        st.session_state.current_page = 0
        st.rerun()
    
    # Display posts
    for idx, post in current_posts.iterrows():
        display_post_card(post)
    
    # Page navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("⏪ Previous") and st.session_state.current_page > 0:
            st.session_state.current_page -= 1
            st.rerun()
    
    with col2:
        st.caption(f"Showing {start_idx + 1}-{end_idx} of {len(posts_df)} posts")
    
    with col3:
        if st.button("Next ⏩") and st.session_state.current_page < total_pages - 1:
            st.session_state.current_page += 1
            st.rerun()
    
    # Reset to page 1 button
    if st.session_state.current_page > 0:
        if st.button("🔄 Reset to Page 1"):
            st.session_state.current_page = 0
            st.rerun()


def display_post_card(post: Dict[str, Any]):
    """Display a single post as a card"""
    with st.container():
        # Post header with platform icon and metadata
        platform_icons = {
            'twitter': '🐦',
            'reddit': '🔴',
            'threads': '🧵',
            'default': '📄'
        }
        
        platform = post.get('platform', 'default').lower()
        platform_icon = platform_icons.get(platform, platform_icons['default'])
        
        # Get post date
        date_fields = ['created_timestamp', 'created_at', 'saved_at', 'timestamp']
        post_date = "Unknown"
        
        for field in date_fields:
            if field in post and post[field]:
                try:
                    if isinstance(post[field], str):
                        post_date = pd.to_datetime(post[field]).strftime('%Y-%m-%d %H:%M')
                    else:
                        post_date = post[field].strftime('%Y-%m-%d %H:%M')
                    break
                except (ValueError, TypeError):
                    continue
        
        # Post header
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown(f"**{platform_icon} {platform.capitalize()}**")
        
        with col2:
            st.caption(f"📅 {post_date}")
        
        # Post content
        content = post.get('content', '')
        if content and len(content) > 500:  # Truncate long content
            content = content[:500] + "..."
        
        st.markdown(f"""
        <div style="padding: 10px; border-radius: 10px; background-color: #f0f2f6; margin: 5px 0;">
            {content}
        </div>
        """, unsafe_allow_html=True)
        
        # Post actions
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🔖 Save", key=f"save_{post.get('id', '')}"):
                # Handle save action
                st.toast("Post saved!")
        
        with col2:
            if st.button("🗑️ Delete", key=f"delete_{post.get('id', '')}"):
                # Handle delete action
                st.toast("Post deleted!")
        
        with col3:
            if 'url' in post and post['url']:
                st.markdown(f"[🔗 Open Original]({post['url']})", unsafe_allow_html=True)
        
        st.markdown("---")


def render_analytics_tab():
    """Render the analytics tab"""
    st.header("📊 Analytics")
    
    # Placeholder for analytics
    st.info("Analytics dashboard coming soon!")
    
    # Example analytics (to be implemented)
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Posts", "1,234")
    
    with col2:
        st.metric("From Twitter", "567")
    
    with col3:
        st.metric("From Reddit", "432")
    
    # Add charts and visualizations here
    st.write("More analytics and visualizations will be added here.")


def render_settings_tab():
    """Render the settings tab"""
    st.header("⚙️ Settings")
    
    st.subheader("General")
    
    # Theme selection
    theme = st.selectbox(
        "Theme",
        ["Light", "Dark", "System"],
        index=0
    )
    
    # Posts per page
    posts_per_page = st.number_input(
        "Posts per page",
        min_value=5,
        max_value=50,
        value=10
    )
    
    st.subheader("Data Management")
    
    # Export data
    if st.button("📤 Export Data"):
        st.toast("Preparing your data for export...")
        # Implement export functionality
    
    # Import data
    uploaded_file = st.file_uploader("Import Data", type=["json", "csv"])
    if uploaded_file is not None:
        st.toast("Data imported successfully!")
        # Implement import functionality
    
    st.subheader("Danger Zone")
    
    # Clear data
    if st.button("🗑️ Clear All Data", type="primary"):
        if st.checkbox("I understand this will delete all my data"):
            st.warning("This action cannot be undone. All your data will be permanently deleted.")
            if st.button("⚠️ Confirm Delete All Data"):
                # Implement data deletion
                st.error("All data has been deleted.")
    
    # Reset to defaults
    if st.button("🔄 Reset to Defaults"):
        if st.checkbox("Reset all settings to their default values?"):
            # Implement reset
            st.success("Settings have been reset to defaults.")
