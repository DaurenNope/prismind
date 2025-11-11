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
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 20px;
        border-left: 4px solid #2563eb;
    }
    .feed-title {
        font-size: 1.2em;
        font-weight: 600;
        color: #111827;
        margin-bottom: 8px;
        line-height: 1.4;
    }
    .feed-meta {
        display: flex;
        gap: 15px;
        font-size: 0.85em;
        color: #6b7280;
        margin-bottom: 10px;
    }
    .feed-summary {
        color: #374151;
        line-height: 1.6;
        margin-bottom: 12px;
        max-height: none;
        overflow: visible;
    }
    .feed-link {
        color: #2563eb;
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
        background-color: #f3f4f6;
        color: #374151;
        padding: 4px 12px;
        border-radius: 6px;
        font-size: 0.75em;
        font-weight: 500;
        display: inline-block;
        border: 1px solid #d1d5db;
        margin-right: 4px;
    }
    .category-tag {
        background-color: #f9fafb;
        color: #6b7280;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75em;
        display: inline-block;
        margin-right: 4px;
        border: 1px solid #e5e7eb;
    }
    .score-badge {
        background-color: #d1fae5;
        color: #065f46;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75em;
        font-weight: 500;
        border: 1px solid #10b981;
    }
    .alpha-badge {
        background-color: #fee2e2;
        color: #991b1b;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.75em;
        font-weight: 500;
        border: 1px solid #ef4444;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header with better layout
    st.title("🧠 Intelligence Feed")
    st.markdown("*Your unified discovery dashboard - all sources, one feed*")
    
    # Action buttons row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🔄 Refresh Feed", use_container_width=True, type="primary"):
            st.rerun()
    
    with col2:
        if st.button("📥 Collect New", use_container_width=True, type="secondary"):
            st.info("💡 Navigate to the **Collect** tab to start collecting posts")
    
    with col3:
        if st.button("🤖 Analyze Pending", use_container_width=True, type="secondary"):
            st.info("💡 Navigate to the **Analysis** tab to analyze posts")
    
    with col4:
        if st.button("📊 View Dashboard", use_container_width=True, type="secondary"):
            st.info("💡 Navigate to the **Dashboard** tab for overview")
    
    # Get data
    supabase = get_supabase()
    curator = get_curator()
    
    # Filters in main content area (more useful than sidebar)
    col1, col2, col3 = st.columns(3)
        
    with col1:
        time_range = st.selectbox(
            "📅 Time Range",
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
        
    with col2:
        sources = st.multiselect(
            "📰 Sources",
            ["RSS", "Reddit", "GitHub"],
            default=["RSS", "Reddit", "GitHub"]
        )
        
    with col3:
        min_score = st.slider("⭐ Min Quality Score", 0, 10, 5)
    
    # Category filter (if needed)
        categories = st.multiselect(
        "📂 Categories",
            ["AI", "Crypto", "Business", "Space", "Mystery", "All"],
        default=["All"],
        key="feed_categories"
        )
    
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
    
    # Stats with modern cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{len(all_items)}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">📰 Total Discoveries</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        rss_count = len([i for i in all_items if i.get('source') == 'RSS'])
        reddit_count = len([i for i in all_items if i.get('source') == 'REDDIT'])
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{rss_count} / {reddit_count}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">RSS / Reddit</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        categories_present = set([i.get('category', 'General') for i in all_items])
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{len(categories_present)}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">📂 Categories</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        high_quality = len([i for i in all_items if i.get('score', 0) >= 7])
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{high_quality}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">⭐ High Quality (7+)</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Render feed
    if not all_items:
        st.info("📭 No items found. Adjust your filters or run the collection pipeline.")
        st.markdown("""
        <div style="text-align: center; padding: 3rem; color: #64748b;">
            <h3>No content to display</h3>
            <p>Try adjusting your filters or collecting new content from the <strong>Collect</strong> tab.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Show count and pagination info
        st.markdown(f"**Showing {len(all_items)} items**")
        st.divider()
        
        # Render feed cards
        for item in all_items:
            render_feed_card(item, curator)
    
    # Auto-refresh (optional feature - disabled by default)
    # Uncomment to enable auto-refresh every 60 seconds
    # if st.checkbox("Auto-refresh feed", value=False):
    #     import time
    #     time.sleep(60)
    #     st.rerun()


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
