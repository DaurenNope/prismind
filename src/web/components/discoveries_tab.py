"""
Discoveries Tab - View and manage autonomous discoveries
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import List, Dict, Any


def render_discoveries_tab():
    """Render the discoveries tab"""
    st.header("🔍 Autonomous Discoveries")
    st.markdown("Content automatically discovered for you")
    
    # Get discoveries from Supabase
    try:
        from src.supabase_manager import SupabaseManager
        supabase = SupabaseManager()
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox(
                "Status",
                ["all", "new", "shown", "bookmarked", "dismissed"],
                index=0
            )
        
        with col2:
            source_filter = st.selectbox(
                "Source",
                ["all", "rss", "github", "reddit"],
                index=0
            )
        
        with col3:
            min_quality = st.slider("Min Quality", 0.0, 10.0, 5.0)
        
        # Build query
        query = supabase.client.table('discoveries').select('*')
        
        if status_filter != "all":
            query = query.eq('status', status_filter)
        
        if source_filter != "all":
            query = query.eq('source', source_filter)
        
        query = query.gte('quality_score', min_quality)
        query = query.order('discovered_at', desc=True).limit(50)
        
        result = query.execute()
        discoveries = result.data if result.data else []
        
        if not discoveries:
            st.info("No discoveries found. Run `/autonomous discover` in Telegram to start!")
            return
        
        # Stats
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total", len(discoveries))
        
        with col2:
            new_count = sum(1 for d in discoveries if d.get('status') == 'new')
            st.metric("New", new_count)
        
        with col3:
            avg_quality = sum(d.get('quality_score', 0) for d in discoveries) / len(discoveries) if discoveries else 0
            st.metric("Avg Quality", f"{avg_quality:.1f}")
        
        with col4:
            topics = set()
            for d in discoveries:
                if d.get('matched_topics'):
                    topics.update(d['matched_topics'])
            st.metric("Topics", len(topics))
        
        st.markdown("---")
        
        # Display discoveries
        for idx, discovery in enumerate(discoveries):
            render_discovery_card(discovery, supabase, idx)
        
    except Exception as e:
        st.error(f"Error loading discoveries: {e}")


def render_discovery_card(discovery: Dict[str, Any], supabase, idx: int = 0):
    """Render a single discovery card"""
    disc_id = discovery.get('id')
    unique_key = f"{idx}_{str(disc_id)[:8]}" if disc_id else str(idx)
    
    with st.expander(
        f"{'🆕 ' if discovery.get('status') == 'new' else ''}"
        f"{discovery.get('title', discovery.get('content', '')[:60])}...",
        expanded=discovery.get('status') == 'new'
    ):
        # Header
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**Source:** {discovery.get('platform', 'unknown')} / {discovery.get('source', 'unknown')}")
            st.markdown(f"**Author:** {discovery.get('author', 'Unknown')}")
            
            # Topics
            if discovery.get('matched_topics'):
                topics_str = " | ".join([f"`{t}`" for t in discovery['matched_topics']])
                st.markdown(f"**Topics:** {topics_str}")
        
        with col2:
            quality = discovery.get('quality_score', 0)
            st.metric("Quality", f"{quality:.1f}/10")
            
            # Status badge
            status = discovery.get('status', 'new')
            status_colors = {
                'new': '🟢',
                'shown': '🟡',
                'bookmarked': '🔵',
                'dismissed': '⚫'
            }
            st.markdown(f"{status_colors.get(status, '⚪')} {status.title()}")
        
        # Content
        st.markdown("### Content")
        content = discovery.get('content', '')
        if len(content) > 500:
            st.markdown(content[:500] + "...")
        else:
            st.markdown(content)
        
        # Summary
        if discovery.get('content_summary'):
            st.markdown("### Summary")
            st.info(discovery['content_summary'])
        
        # URL
        if discovery.get('url'):
            st.markdown(f"🔗 [View Original]({discovery['url']})")
        
        # Discovered time
        discovered_at = discovery.get('discovered_at', '')
        if discovered_at:
            st.caption(f"Discovered: {discovered_at}")
        
        # Actions
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💾 Save to Bookmarks", key=f"save_{unique_key}"):
                save_to_bookmarks(discovery, supabase)
                st.success("Saved to bookmarks!")
                st.rerun()
        
        with col2:
            if st.button("👎 Dismiss", key=f"dismiss_{unique_key}"):
                dismiss_discovery(discovery['id'], supabase)
                st.success("Dismissed!")
                st.rerun()
        
        with col3:
            if st.button("🔄 Mark as Shown", key=f"shown_{unique_key}"):
                mark_as_shown(discovery['id'], supabase)
                st.success("Marked as shown!")
                st.rerun()


def save_to_bookmarks(discovery: Dict[str, Any], supabase):
    """Save discovery to bookmarks table"""
    try:
        # Update discovery status
        supabase.client.table('discoveries').update({
            'status': 'bookmarked',
            'user_action': 'saved',
            'user_action_at': datetime.now().isoformat()
        }).eq('id', discovery['id']).execute()
        
        # Add to posts/bookmarks table
        bookmark_data = {
            'post_id': discovery.get('post_id', discovery['id']),
            'platform': discovery.get('platform'),
            'content': discovery.get('content'),
            'title': discovery.get('title'),
            'url': discovery.get('url'),
            'author': discovery.get('author'),
            'created_at': discovery.get('created_at'),
            'source': 'discovery_saved',
            'quality_score': discovery.get('quality_score'),
            'value_score': discovery.get('value_score'),
            'ai_summary': discovery.get('ai_summary'),
            'content_summary': discovery.get('content_summary'),
            'tags': discovery.get('tags'),
            'topic': discovery.get('topic'),
            'is_saved': True,
            'saved_at': datetime.now().isoformat()
        }
        
        supabase.client.table('posts').insert(bookmark_data).execute()
        
    except Exception as e:
        st.error(f"Error saving to bookmarks: {e}")


def dismiss_discovery(discovery_id: str, supabase):
    """Dismiss a discovery"""
    try:
        supabase.client.table('discoveries').update({
            'status': 'dismissed',
            'user_action': 'dismissed',
            'user_action_at': datetime.now().isoformat()
        }).eq('id', discovery_id).execute()
    except Exception as e:
        st.error(f"Error dismissing discovery: {e}")


def mark_as_shown(discovery_id: str, supabase):
    """Mark discovery as shown"""
    try:
        supabase.client.table('discoveries').update({
            'status': 'shown',
            'shown_to_user_at': datetime.now().isoformat()
        }).eq('id', discovery_id).execute()
    except Exception as e:
        st.error(f"Error marking as shown: {e}")
