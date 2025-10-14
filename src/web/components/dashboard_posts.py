"""
Dashboard Posts Components for PrisMind
Handles posts display and filtering
"""

import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional


def render_posts_tab():
    """Render the posts tab with filtering and pagination"""
    from src.services.new_database_manager import get_database_manager
    
    db_manager = get_database_manager()
    
    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    
    # Platform filter
    platforms = db_manager.get_platforms()
    selected_platforms = st.sidebar.multiselect(
        "Platforms", 
        platforms, 
        default=platforms
    )
    
    # Date range filter
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(),
        help="Select date range for posts"
    )
    
    # Value score filter
    min_score = st.sidebar.slider(
        "Minimum Value Score",
        min_value=0.0,
        max_value=1.0,
        value=0.0,
        step=0.1
    )
    
    # Search filter
    search_query = st.sidebar.text_input(
        "Search Posts",
        placeholder="Search in titles and content..."
    )
    
    # Get filtered posts
    posts = db_manager.get_posts(
        platforms=selected_platforms,
        min_score=min_score,
        search_query=search_query,
        limit=100
    )
    
    if not posts:
        st.info("No posts found matching your criteria.")
        return
    
    # Display posts count
    st.subheader(f"📚 Found {len(posts)} posts")
    
    # Pagination
    posts_per_page = 10
    total_pages = (len(posts) - 1) // posts_per_page + 1
    
    if total_pages > 1:
        page = st.selectbox(
            "Page",
            range(1, total_pages + 1),
            format_func=lambda x: f"Page {x} of {total_pages}"
        )
    else:
        page = 1
    
    # Display posts for current page
    start_idx = (page - 1) * posts_per_page
    end_idx = start_idx + posts_per_page
    page_posts = posts[start_idx:end_idx]
    
    for post in page_posts:
        display_post_card(post)
    
    # Show pagination info
    if total_pages > 1:
        st.info(f"Showing posts {start_idx + 1}-{min(end_idx, len(posts))} of {len(posts)}")


def display_post_card(post: Dict[str, Any]):
    """Display a single post as a card"""
    with st.container():
        # Create columns for layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Post title
            st.markdown(f"### {post.get('smart_title', 'Untitled')}")
            
            # Post metadata
            metadata_cols = st.columns(4)
            with metadata_cols[0]:
                st.caption(f"👤 {post.get('author', 'Unknown')}")
            with metadata_cols[1]:
                st.caption(f"🌐 {post.get('platform', 'Unknown')}")
            with metadata_cols[2]:
                st.caption(f"📅 {post.get('created_at', 'Unknown')}")
            with metadata_cols[3]:
                st.caption(f"🏷️ {post.get('topic', 'General')}")
            
            # Post content preview
            content = post.get('content', '')
            if content:
                preview_length = 200
                if len(content) > preview_length:
                    content_preview = content[:preview_length] + "..."
                else:
                    content_preview = content
                st.markdown(content_preview)
            
            # Tags
            tags = post.get('smart_tags', [])
            if tags:
                tag_str = " ".join([f"`{tag}`" for tag in tags[:5]])
                st.markdown(f"**Tags:** {tag_str}")
        
        with col2:
            # Value score
            value_score = post.get('value_score', 0.0)
            score_color = "green" if value_score > 0.7 else "orange" if value_score > 0.4 else "red"
            st.markdown(f"**Value Score:** :{score_color}[{value_score:.2f}]")
            
            # Engagement metrics
            engagement = post.get('engagement', {})
            if engagement:
                st.markdown("**Engagement:**")
                st.markdown(f"👍 {engagement.get('likes', 0)}")
                st.markdown(f"🔄 {engagement.get('retweets', 0)}")
                st.markdown(f"💬 {engagement.get('replies', 0)}")
            
            # Action buttons
            if st.button("View Full", key=f"view_{post.get('id')}"):
                st.session_state['selected_post'] = post
            
            if st.button("Analyze", key=f"analyze_{post.get('id')}"):
                st.session_state['analyze_post'] = post
        
        # Show full post if selected
        if st.session_state.get('selected_post') == post:
            with st.expander("Full Post Content", expanded=True):
                st.markdown(post.get('content', 'No content available'))
                if post.get('url'):
                    st.markdown(f"**Original URL:** {post['url']}")
        
        # Show analysis if requested
        if st.session_state.get('analyze_post') == post:
            with st.expander("Post Analysis", expanded=True):
                show_post_analysis(post)
        
        st.divider()


def show_post_analysis(post: Dict[str, Any]):
    """Show detailed analysis of a post"""
    # Content type analysis
    content_type = post.get('content_type', 'Unknown')
    st.markdown(f"**Content Type:** {content_type}")
    
    # Quality metrics
    quality_score = post.get('quality_score', 0.0)
    st.markdown(f"**Quality Score:** {quality_score:.2f}")
    
    # Sentiment analysis
    sentiment = post.get('sentiment', 'neutral')
    sentiment_emoji = "😊" if sentiment == "positive" else "😐" if sentiment == "neutral" else "😞"
    st.markdown(f"**Sentiment:** {sentiment_emoji} {sentiment}")
    
    # Key topics
    topics = post.get('key_topics', [])
    if topics:
        st.markdown(f"**Key Topics:** {', '.join(topics)}")
    
    # Media analysis
    media_analysis = post.get('media_analysis', [])
    if media_analysis:
        st.markdown("**Media Analysis:**")
        for i, media in enumerate(media_analysis):
            st.markdown(f"- Media {i+1}: {media.get('content_type', 'Unknown')}")
            if media.get('text_content'):
                st.markdown(f"  Text: {media['text_content'][:100]}...")
    
    # Recommendations
    recommendations = post.get('recommendations', [])
    if recommendations:
        st.markdown("**Recommendations:**")
        for rec in recommendations:
            st.markdown(f"- {rec}")





