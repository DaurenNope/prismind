#!/usr/bin/env python3
"""
Tabs components for PrisMind Streamlit app
"""

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

# Use shared database manager without importing new_app to avoid circular deps
from src.services.new_database_manager import get_database_manager as _get_db_manager

@st.cache_resource
def get_database_manager():
    return _get_db_manager()


def render_dashboard_tab():
    """Render the dashboard view"""
    st.header("📊 Intelligence Dashboard")

    db_manager = get_database_manager()
    df = pd.DataFrame()
    try:
        if hasattr(db_manager, 'get_all_posts'):
            posts_any = db_manager.get_all_posts(include_deleted=False)
            if isinstance(posts_any, pd.DataFrame):
                df = posts_any
            else:
                df = pd.DataFrame(posts_any)
        elif hasattr(db_manager, 'get_posts'):
            posts_list = db_manager.get_posts(limit=1000)
            df = pd.DataFrame(posts_list)
    except Exception as e:
        st.error(f"Error fetching posts: {e}")
        df = pd.DataFrame()

    if not df.empty:
        total_posts = len(df)
        ai_analyzed = 0
        try:
            if 'analysis_timestamp' in df.columns:
                ai_analyzed = df['analysis_timestamp'].notna().sum()
            elif 'ai_summary' in df.columns:
                ai_analyzed = df['ai_summary'].notna().sum()
            elif 'category' in df.columns:
                ai_analyzed = df['category'].notna().sum()
        except Exception:
            ai_analyzed = 0

        avg_score = None
        has_value_scores = 'value_score' in df.columns and df['value_score'].notna().any()
        if has_value_scores:
            with pd.option_context('mode.use_inf_as_na', True):
                try:
                    avg_score = df['value_score'].astype(float).mean()
                except Exception:
                    avg_score = None

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📚 Total Posts", total_posts)
        with col2:
            percentage = int((ai_analyzed / total_posts) * 100) if total_posts else 0
            st.metric("🤖 AI Analyzed", f"{ai_analyzed} ({percentage}%)")
        with col3:
            st.metric("🌐 Platforms", df['platform'].nunique() if 'platform' in df.columns else 0)
        with col4:
            if has_value_scores and avg_score is not None:
                st.metric("⭐ Avg Value Score", f"{avg_score:.2f}")
            else:
                st.metric("⭐ Avg Value Score", "N/A")

        st.subheader("📈 Platform Distribution")
        if 'platform' in df.columns:
            platform_counts = df['platform'].value_counts()
            st.bar_chart(platform_counts)
            for platform, count in platform_counts.items():
                st.write(f"- {platform}: {count}")

        st.subheader("🆕 Recent Posts")
        date_col = 'created_timestamp' if 'created_timestamp' in df.columns else (
            'created_at' if 'created_at' in df.columns else None
        )
        recent_posts = df
        if date_col:
            with pd.option_context('mode.use_inf_as_na', True):
                try:
                    recent_posts = df.sort_values(date_col, ascending=False).head(5)
                except Exception:
                    recent_posts = df.head(5)
        else:
            recent_posts = df.head(5)
        for _, post in recent_posts.iterrows():
            st.write(f"**{post.get('title', 'No title')}**")
            stamp = post.get('created_at') or post.get('created_timestamp') or ''
            st.caption(f"From {post.get('platform', 'unknown')} • {stamp}")
            st.write("---")
    else:
        st.info("No posts found. Try collecting some posts first!")


def render_browse_tab():
    """Render the browse posts view"""
    st.header("🎯 Browse Posts")
    st.write("Browse and filter your collected posts.")

    db_manager = get_database_manager()

    try:
        available_platforms = db_manager.get_platforms()
    except Exception as exc:
        st.warning(f"Unable to load platforms: {exc}")
        available_platforms = []

    if not available_platforms:
        available_platforms = ["twitter", "reddit", "threads"]

    platform_options = {platform.title(): platform for platform in available_platforms}

    st.subheader("🔍 Filters")
    col1, col2 = st.columns(2)

    with col1:
        selected_platform_labels = st.multiselect(
            "Filter by Platform",
            options=list(platform_options.keys()),
            default=list(platform_options.keys()),
            help="Select which platforms to include"
        )

    with col2:
        default_start = datetime.now().date() - timedelta(days=7)
        default_end = datetime.now().date()
        date_range = st.date_input(
            "Filter by Date",
            value=(default_start, default_end),
            max_value=datetime.now().date(),
            key="date_filter"
        )

    col3, col4 = st.columns(2)
    with col3:
        min_score = st.slider(
            "Minimum Value Score",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
            help="Only show posts with a value score at or above this threshold"
        )

    with col4:
        search_query = st.text_input(
            "Search",
            placeholder="Search titles and content",
            help="Enter keywords to search across titles and content"
        )

    selected_platforms = [platform_options[label] for label in selected_platform_labels] if selected_platform_labels else None
    min_score_filter = min_score if min_score > 0 else None
    search_filter = search_query.strip() or None

    posts = []
    try:
        posts = db_manager.get_posts(
            limit=1000,
            platforms=selected_platforms,
            min_score=min_score_filter,
            search_query=search_filter
        )
    except Exception as exc:
        st.error(f"Unable to load posts: {exc}")

    if not posts:
        st.info("No posts found for the selected filters.")
        return

    df = pd.DataFrame(posts)

    if 'created_at' in df.columns:
        with pd.option_context('mode.use_inf_as_na', True):
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    elif isinstance(date_range, list) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = datetime.now().date() - timedelta(days=7)
        end_date = datetime.now().date()

    if 'created_at' in df.columns:
        try:
            # Convert to timezone-aware timestamps for comparison
            start_ts = pd.Timestamp(start_date, tz='UTC')
            end_ts = pd.Timestamp(end_date, tz='UTC') + pd.Timedelta(days=1)
            
            # Ensure created_at column is timezone-aware UTC
            if df['created_at'].dt.tz is None:
                df['created_at'] = df['created_at'].dt.tz_localize('UTC')
            elif str(df['created_at'].dt.tz) != 'UTC':
                df['created_at'] = df['created_at'].dt.tz_convert('UTC')
            
            # Now do the comparison
            df = df[(df['created_at'] >= start_ts) & (df['created_at'] < end_ts)]
        except Exception as e:
            st.warning(f"Date filtering skipped due to: {e}")
            # Continue without date filtering

    if df.empty:
        st.info("No posts found for the selected filters.")
        return

    df_display = df.copy()
    # Prefer collected_at for recency if available
    if 'collected_at' in df.columns:
        try:
            df['collected_at'] = pd.to_datetime(df['collected_at'], errors='coerce', utc=True)
            df.sort_values(by=['collected_at'], ascending=False, inplace=True, kind='mergesort')
        except Exception:
            pass
        if 'collected_at' in df_display.columns:
            try:
                df_display['collected_at'] = pd.to_datetime(df_display['collected_at'], errors='coerce', utc=True)
                df_display['collected_at'] = df_display['collected_at'].dt.strftime('%Y-%m-%d %H:%M')
            except Exception:
                pass
    if 'created_at' in df_display.columns:
        df_display['created_at'] = df_display['created_at'].dt.strftime('%Y-%m-%d %H:%M')

    if 'platform' in df_display.columns:
        df_display['platform'] = df_display['platform'].str.title()

    if 'smart_title' in df_display.columns:
        if 'title' in df_display.columns:
            df_display['title'] = df_display['title'].fillna(df_display['smart_title'])
        else:
            df_display['title'] = df_display['smart_title']

    if 'author' in df_display.columns and 'author_handle' in df_display.columns:
        df_display['author'] = df_display['author'].fillna(df_display['author_handle'])
    elif 'author' not in df_display.columns and 'author_handle' in df_display.columns:
        df_display['author'] = df_display['author_handle']

    display_columns = [
        col for col in [
            'title',
            'platform',
            'author',
            'collected_at',
            'created_at',
            'value_score',
            'quality_score',
            'sentiment',
        ]
        if col in df_display.columns
    ]

    st.subheader(f"📝 Posts ({len(df_display)})")
    st.dataframe(
        df_display[display_columns].rename(columns={'title': 'Title', 'platform': 'Platform', 'author': 'Author', 'created_at': 'Created', 'collected_at': 'Collected', 'value_score': 'Value Score', 'quality_score': 'Quality Score', 'sentiment': 'Sentiment'}),
        use_container_width=True,
        hide_index=True
    )

    detail_options = df_display.index.tolist()
    selected_index = st.selectbox(
        "Select a post to view details",
        options=detail_options,
        format_func=lambda idx: _format_post_label(df_display.loc[idx])
    )

    selected_post = df.loc[selected_index]

    with st.expander("Post Details", expanded=True):
        platform_value = selected_post.get('platform')
        if isinstance(platform_value, str):
            platform_label = platform_value.title()
        elif pd.notna(platform_value):
            platform_label = str(platform_value)
        else:
            platform_label = 'Unknown'

        st.markdown(f"**Platform:** {platform_label}")
        st.markdown(f"**Author:** {selected_post.get('author', 'Unknown')}")
        created_at_value = selected_post.get('created_at')
        if isinstance(created_at_value, pd.Timestamp):
            created_at_value = created_at_value.strftime('%Y-%m-%d %H:%M')
        st.markdown(f"**Created:** {created_at_value or 'Unknown'}")
        if selected_post.get('url'):
            st.markdown(f"**Original URL:** {selected_post['url']}")
        if selected_post.get('content'):
            st.markdown("---")
            st.markdown(selected_post['content'])
        if selected_post.get('ai_summary'):
            st.markdown("---")
            st.markdown(f"**AI Summary:** {selected_post['ai_summary']}")


def render_settings_tab():
    """Render the settings view with Sources and System merged in"""
    st.header("⚙️ Settings")
    
    # Tabs for Settings: General, Sources, System
    settings_tab1, settings_tab2, settings_tab3 = st.tabs(["⚙️ General", "📡 Sources", "🩺 System"])
    
    with settings_tab1:
        st.subheader("General Settings")
        with st.expander("App Settings", expanded=True):
            st.selectbox("Theme", ["Light", "Dark", "System"], key="theme_setting")
            st.slider("Posts per page", 10, 100, 20, key="posts_per_page")
        
        with st.expander("API Settings"):
            st.text_input("Reddit API Key", type="password", key="reddit_api_key")
            st.text_input("Twitter API Key", type="password", key="twitter_api_key")
        
        if st.button("💾 Save Settings"):
            st.success("Settings saved successfully!")
    
    with settings_tab2:
        # Sources tab content (merged)
        try:
            from src.web.components.sources_tab import render_sources_tab
            render_sources_tab()
        except ImportError:
            st.info("Sources configuration not available")
    
    with settings_tab3:
        # System status tab content (merged)
        try:
            from src.web.components.system_status_tab import render_system_status_tab
            render_system_status_tab()
        except ImportError:
            st.info("System status not available")


def _format_post_label(row: pd.Series) -> str:
    """Format selectbox labels for posts"""
    title = row.get('title')
    if isinstance(title, str) and title.strip():
        return title.strip()

    for fallback in ('smart_title', 'post_id', 'id'):
        value = row.get(fallback)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return "Untitled Post"


# Discoveries tab
def render_discoveries_tab():
    """Import and render discoveries tab"""
    try:
        from src.web.components.discoveries_tab import render_discoveries_tab as render_disc
        render_disc()
    except ImportError as e:
        st.error(f"Discoveries tab not available: {e}")

