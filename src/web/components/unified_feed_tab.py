"""
Unified Intelligence Feed - Main Dashboard
Beautiful feed showing ALL discovered content from all sources
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path('.env'), override=True)

from supabase import create_client
from src.core.learning.intelligent_curator import IntelligentCurator


def get_supabase():
    """Get Supabase client"""
    url = os.getenv('SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    return create_client(url, key)


@st.cache_resource
def get_curator():
    """Get intelligent curator instance"""
    supabase = get_supabase()
    return IntelligentCurator(supabase)


def render_unified_feed():
    """Render the main unified intelligence feed"""
    
    # Session state for temporary dismissals (until page refresh saves to DB)
    if 'dismissed_items' not in st.session_state:
        st.session_state.dismissed_items = set()
    
    # Custom CSS for beautiful feed
    st.markdown("""
    <style>
    .feed-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .feed-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .feed-title {
        font-size: 1.2em;
        font-weight: 600;
        color: #1a1a1a;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .feed-meta {
        display: flex;
        gap: 15px;
        font-size: 0.85em;
        color: #666;
        margin-bottom: 10px;
    }
    .feed-summary {
        color: #444;
        line-height: 1.6;
        margin-bottom: 12px;
        max-height: none;
        overflow: visible;
    }
    .feed-link {
        color: #667eea;
        text-decoration: none;
        font-size: 0.85em;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        margin-top: 8px;
    }
    .feed-link:hover {
        text-decoration: underline;
    }
    .source-badge {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.75em;
        font-weight: 600;
        display: inline-block;
    }
    .category-tag {
        background: #f0f0f0;
        color: #555;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.75em;
        display: inline-block;
        margin-right: 5px;
    }
    .score-badge {
        background: #10b981;
        color: white;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.75em;
        font-weight: 600;
    }
    .alpha-badge {
        background: #ef4444;
        color: white;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 0.75em;
        font-weight: 600;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title("🧠 Intelligence Feed")
        st.markdown("*Your unified discovery dashboard - all sources, one feed*")
    
    with col2:
        if st.button("🔄 Refresh Feed", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("🚀 Collect New", use_container_width=True):
            with st.spinner("Collecting new content..."):
                import subprocess
                import sys
                result = subprocess.run(
                    [sys.executable, "run_full_collection.py"],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                if result.returncode == 0:
                    st.success("✅ Collection complete! Refreshing...")
                    st.rerun()
                else:
                    st.error(f"Collection failed: {result.stderr}")
    
    # Get data
    supabase = get_supabase()
    curator = get_curator()
    
    # Sidebar filters
    with st.sidebar:
        st.subheader("🔍 Filters")
        
        # Time range
        time_range = st.selectbox(
            "Time Range",
            ["Last 24 hours", "Last 3 days", "Last week", "Last month", "All time"],
            index=0
        )
        
        time_map = {
            "Last 24 hours": 1,
            "Last 3 days": 3,
            "Last week": 7,
            "Last month": 30,
            "All time": 365
        }
        days = time_map[time_range]
        
        # Source filter
        sources = st.multiselect(
            "Sources",
            ["RSS", "Reddit", "GitHub"],
            default=["RSS", "Reddit", "GitHub"]
        )
        
        # Category filter
        categories = st.multiselect(
            "Categories",
            ["AI", "Crypto", "Business", "Space", "Mystery", "All"],
            default=["All"]
        )
        
        # Quality filter
        min_score = st.slider("Min Quality Score", 0, 10, 5)
        
        # Note: Telegram has its own dedicated tab
    
    # Fetch data from multiple sources
    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
    
    all_items = []
    
    # 1. Get RSS/Reddit discoveries
    if "RSS" in sources or "Reddit" in sources or "GitHub" in sources:
        try:
            query = supabase.table('discoveries')\
                .select('*')\
                .gte('created_at', cutoff_date)\
                .order('created_at', desc=True)\
                .limit(100)
            
            result = query.execute()
            
            for item in result.data:
                # Skip dismissed items from database
                if item.get('dismissed', False):
                    continue
                    
                all_items.append({
                    'id': item.get('id'),
                    'title': item.get('title', 'No title'),
                    'url': item.get('url', ''),
                    'summary': item.get('tldr', '') or item.get('content_summary', ''),
                    'source': item.get('source', 'rss').upper(),
                    'category': item.get('category') or item.get('topic', 'General'),
                    'date': item.get('created_at', ''),
                    'score': 7,  # Default score
                    'is_alpha': False,
                    'is_airdrop': False,
                    'dismissed': item.get('dismissed', False),
                    'type': 'discovery'
                })
        except Exception as e:
            st.error(f"Error loading discoveries: {e}")
    
    # 2. Telegram is in its own dedicated tab - not here!
    # 3. TODO: Get Twitter/Threads discoveries (future)
    
    # Apply category filter
    if "All" not in categories:
        all_items = [item for item in all_items if item.get('category') in categories]
    
    # Filter out dismissed items from session state
    all_items = [item for item in all_items if item['id'] not in st.session_state.dismissed_items]
    
    # Apply intelligent filtering and ranking
    all_items = curator.filter_and_rank_feed(all_items)
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📰 Total Discoveries", len(all_items))
    with col2:
        # Count by source
        rss_count = len([i for i in all_items if i.get('source') == 'RSS'])
        reddit_count = len([i for i in all_items if i.get('source') == 'REDDIT'])
        st.metric("RSS / Reddit", f"{rss_count} / {reddit_count}")
    with col3:
        # Count by category
        categories_present = set([i.get('category', 'General') for i in all_items])
        st.metric("Categories", len(categories_present))
    with col4:
        # Quality distribution
        high_quality = len([i for i in all_items if i.get('score', 0) >= 7])
        st.metric("High Quality (7+)", high_quality)
    
    st.markdown("---")
    
    # Render feed
    if not all_items:
        st.info("No items found. Adjust your filters or run the collection pipeline.")
    else:
        # DEBUG: Show breakdown before rendering
        sources_debug = {}
        for item in all_items:
            src = item.get('source', 'unknown')
            sources_debug[src] = sources_debug.get(src, 0) + 1
        
        st.info(f"📊 Rendering: {sources_debug}")
        
        for item in all_items:
            render_feed_card(item, curator)
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(60)
        st.rerun()


def render_feed_card(item: Dict[str, Any], curator: IntelligentCurator):
    """Render a single feed card"""
    
    title = item.get('title', 'No title')
    url = item.get('url', '')
    summary = item.get('summary', '')
    source = item.get('source', 'Unknown')
    category = item.get('category', 'General')
    date = item.get('date', '')[:10]
    score = item.get('score', 0)
    is_alpha = item.get('is_alpha', False)
    is_airdrop = item.get('is_airdrop', False)
    item_type = item.get('type', 'discovery')
    
    # Get full content if available
    full_content = item.get('content', '') or item.get('content_en', '') or summary
    
    # Truncate only if very long (show more characters)
    display_summary = full_content if len(full_content) < 500 else full_content[:500] + '...'
    
    with st.container():
        # Badges
        badges_html = f'<span class="source-badge">{source}</span> '
        badges_html += f'<span class="category-tag">{category}</span> '
        
        if score >= 7:
            badges_html += f'<span class="score-badge">⭐ {score}/10</span> '
        
        if is_alpha:
            badges_html += '<span class="alpha-badge">🔥 ALPHA</span> '
        
        if is_airdrop:
            badges_html += '<span class="alpha-badge">💰 AIRDROP</span> '
        
        # Build link display
        link_display = ''
        if url:
            # Clean URL for display (remove http/https, www)
            clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
            if len(clean_url) > 60:
                clean_url = clean_url[:60] + '...'
            link_display = f'<a href="{url}" target="_blank" class="feed-link">🔗 {clean_url}</a>'
        
        st.markdown(f"""
        <div class="feed-card">
            <div>{badges_html}</div>
            <div class="feed-title">
                <a href="{url}" target="_blank" style="text-decoration: none; color: inherit;">
                    {title}
                </a>
            </div>
            <div class="feed-meta">
                <span>📅 {date}</span>
            </div>
            {f'<div class="feed-summary">{display_summary}</div>' if display_summary else ''}
            {link_display}
        </div>
        """, unsafe_allow_html=True)
        
        # Action buttons
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("💾 Save", key=f"save_{item['id']}"):
                curator.log_interaction(item['id'], 'save')
                curator.learn_from_action(item, 'save')
                st.success("✅ Saved! System learned you like this.")
                st.rerun()
        
        with col2:
            if st.button("✍️ Rewrite", key=f"rewrite_{item['id']}"):
                curator.log_interaction(item['id'], 'view')
                st.session_state.rewriter_content = summary or title
                st.success("✅ Sent to Rewriter!")
        
        with col3:
            if item_type == 'telegram' and not item.get('content_en'):
                if st.button("🌐 Translate", key=f"translate_{item['id']}"):
                    curator.log_interaction(item['id'], 'view')
                    st.info("Translation starting...")
            else:
                if st.button("⏭️ Skip", key=f"skip_{item['id']}"):
                    curator.log_interaction(item['id'], 'skip')
                    curator.learn_from_action(item, 'skip')
                    st.info("Skipped")
        
        with col4:
            if st.button("🗑️ Dismiss", key=f"dismiss_{item['id']}"):
                # Add to session state for immediate feedback
                st.session_state.dismissed_items.add(item['id'])
                
                # Save to database permanently
                try:
                    supabase = get_supabase()
                    supabase.table('discoveries')\
                        .update({'dismissed': True})\
                        .eq('id', item['id'])\
                        .execute()
                    
                    # Log interaction and learn
                    curator.log_interaction(item['id'], 'dismiss')
                    curator.learn_from_action(item, 'dismiss')
                    
                    st.success("✅ Dismissed forever! Won't see again.")
                except Exception as e:
                    st.error(f"Error dismissing: {e}")
                
                st.rerun()
        
        st.markdown("<br>", unsafe_allow_html=True)


if __name__ == "__main__":
    render_unified_feed()
