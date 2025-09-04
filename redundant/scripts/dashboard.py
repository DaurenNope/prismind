#!/usr/bin/env python3
"""
PrisMind Dashboard - Modern Social Media Style
"""

import streamlit as st
import pandas as pd
import warnings
import re
from urllib.parse import urlparse
import sqlite3
import ast
import sys
import os
from typing import Optional, List, Tuple

# Add the project root to the path so we can import scripts
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def get_database_connection():
    return sqlite3.connect('data/prismind.db')

# Quiet pandas concat FutureWarnings globally (safe for our use)
warnings.filterwarnings('ignore', category=FutureWarning)

def _series_or_dict_to_dict(obj):
    try:
        return obj.to_dict()  # pandas Series
    except AttributeError:
        return dict(obj)

def get_post_key(post) -> str:
    """Build a stable unique key for a post across views.
    Accepts pandas Series or dict. Uses platform + post_id, else url.
    """
    p = _series_or_dict_to_dict(post)
    platform = str(p.get('platform') or '').lower()
    post_id = str(p.get('post_id') or '')
    url_val = str(p.get('url') or '')
    return f"{platform}|{post_id or url_val}"

def _extract_urls(text: Optional[str]) -> List[str]:
    if not text:
        return []
    return re.findall(r"https?://\S+", text)

def _humanize_url(url: str) -> str:
    try:
        p = urlparse(url)
        host = p.netloc.replace('www.', '')
        path = p.path or ''
        if len(path) > 30:
            path = path[:30] + '…'
        return f"{host}{path}"
    except Exception:
        return url

def _display_text_and_links(text: Optional[str], max_length: int = 200) -> Tuple[str, List[str]]:
    urls = _extract_urls(text)
    clean = re.sub(r"https?://\S+", "", text or "").strip()
    clean = " ".join(clean.split())
    dense = st.session_state.get('feed_density', 'Comfy') == 'Compact'
    limit = 90 if dense else max_length
    if len(clean) > limit:
        clean = clean[:limit] + "..."
    return clean, urls

def resolve_platform(post) -> str:
    p = _series_or_dict_to_dict(post)
    name = str(p.get('platform') or '').strip().lower()
    if name in {"twitter", "x"}:
        return "twitter"
    if name in {"reddit"}:
        return "reddit"
    if name in {"threads", "threads.net"}:
        return "threads"
    if name in {"linkedin"}:
        return "linkedin"
    # Derive from URL as fallback
    url_val = str(p.get('url') or '')
    try:
        host = urlparse(url_val).netloc.lower()
        if any(h in host for h in ["reddit.com", "redd.it"]):
            return "reddit"
        if any(h in host for h in ["x.com", "twitter.com"]):
            return "twitter"
        if "threads.net" in host:
            return "threads"
        if "linkedin.com" in host:
            return "linkedin"
    except Exception:
        pass
    return name or "twitter"  # default to twitter style if unknown

def render_full_post(full_post: dict):
    """Render a full-width detailed view for a selected post."""
    post = _series_or_dict_to_dict(full_post)
    platform = (post.get('platform') or '').title()
    score_val = post.get('value_score')
    score_display = "N/A" if pd.isna(score_val) else f"{float(score_val):.1f}"

    st.markdown(
        """
        <style>
        .full-post {background:#0f1420;border:1px solid #2a3344;border-radius:12px;padding:18px;margin:8px 0;}
        .full-post h3{margin:0 0 6px 0}
        .meta{color:#9aa4b2;font-size:12px;margin-bottom:12px}
        .content{white-space:pre-wrap;line-height:1.6;font-size:15px}
        .comment{background:#111826;border:1px solid #2a3344;border-radius:8px;padding:10px;margin:6px 0}
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container():
        st.markdown('<div class="full-post">', unsafe_allow_html=True)
        st.markdown(f"### {post.get('author') or 'Unknown'} — {platform}")
        st.markdown(f"<div class='meta'>Score: <b>{score_display}</b> · {post.get('url','')}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='content'>{post.get('content') or '_No content available_'}</div>", unsafe_allow_html=True)
        # Comments
        post_id_for_comments = str(post.get('post_id') or post.get('id') or '')
        comments = get_comments_for_post(post_id_for_comments)
        if comments:
            st.markdown("#### Comments")
            for c in comments:
                st.markdown(f"<div class='comment'>{c}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    cols = st.columns([1,1])
    with cols[0]:
        if st.button("⬅️ Close", key="close_full_post"):
            st.session_state['full_post'] = None
            st.rerun()
    with cols[1]:
        if post.get('url') and st.button("🔗 Open Link", key="open_full_post"):
            import webbrowser
            webbrowser.open(post['url'])

def render_full_inline(full_post: dict, base_key: str):
    """Render full content inline on the same page, with a close action."""
    post = _series_or_dict_to_dict(full_post)
    platform = (post.get('platform') or '').title()
    score_val = post.get('value_score')
    score_display = "N/A" if pd.isna(score_val) else f"{float(score_val):.1f}"

    st.markdown(
        """
        <style>
        .inline-full {background:#0f1420;border:1px solid #2a3344;border-radius:12px;padding:16px;margin:10px 0;}
        .inline-full .meta{color:#9aa4b2;font-size:12px;margin-bottom:10px}
        .inline-full .content{white-space:pre-wrap;line-height:1.6;font-size:15px}
        .inline-full .comment{background:#111826;border:1px solid #2a3344;border-radius:8px;padding:10px;margin:6px 0}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="inline-full">', unsafe_allow_html=True)
    st.markdown(f"**{post.get('author') or 'Unknown'} — {platform}**  · Score: {score_display}")
    st.markdown(f"<div class='meta'>{post.get('url','')}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='content'>{post.get('content') or '_No content available_'}</div>", unsafe_allow_html=True)
    comments = get_comments_for_post(str(post.get('post_id') or post.get('id') or ''))
    if comments:
        st.markdown("**Comments**")
        for c in comments:
            st.markdown(f"<div class='comment'>{c}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("Close Full", key=f"close_full_{base_key}"):
            st.session_state['expanded_post'] = None
            st.rerun()
    with c2:
        if post.get('url') and st.button("Open Link", key=f"open_link_{base_key}"):
            import webbrowser
            webbrowser.open(post['url'])

def get_category_counts():
    """Get counts for all categories"""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_bookmarks'")
    tables = cursor.fetchall()

    counts = {}
    for table in tables:
        table_name = table[0]
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
        except Exception:
            count = 0
        category_name = table_name.replace('_bookmarks', '').replace('_', ' ').title()
        counts[category_name] = count

    # Fallback to posts table categories when no category tables exist or totals are zero
    if not counts or sum(counts.values()) == 0:
        try:
            cursor.execute("SELECT category, COUNT(*) FROM posts WHERE is_deleted = 0 GROUP BY category")
            rows = cursor.fetchall()
            counts = { (row[0] or 'Uncategorized').title(): row[1] for row in rows }
        except Exception:
            counts = {}

    conn.close()
    return counts

def get_available_categories():
    """Get list of available categories with their table names"""
    conn = get_database_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_bookmarks'")
    tables = cursor.fetchall()

    categories = {}
    for table in tables:
        table_name = table[0]
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
            count = cursor.fetchone()[0]
        except Exception:
            count = 0
        if count > 0:  # Only include categories with posts
            category_name = table_name.replace('_bookmarks', '').replace('_', ' ').title()
            categories[category_name] = table_name

    # Fallback to posts categories
    if not categories:
        try:
            df = pd.read_sql_query("SELECT category, COUNT(*) as c FROM posts WHERE is_deleted = 0 GROUP BY category HAVING c > 0", conn)
            for _, row in df.iterrows():
                name = (row['category'] or 'Uncategorized').title()
                categories[name] = 'posts'  # logical placeholder
        except Exception:
            pass

    conn.close()
    return categories

def get_manual_review_posts():
    """Get posts that need manual review"""
    conn = get_database_connection()
    query = """
        SELECT post_id, platform, author, content, url, created_at, value_score,
               ai_summary, key_concepts, smart_tags, tech_score, business_score, research_score
        FROM manual_review_bookmarks
        ORDER BY value_score DESC, created_at DESC
    """
    try:
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception:
        conn.close()
        return pd.DataFrame()

def get_posts_from_category(category: str, limit: int = 50):
    """Get posts from a specific category with full data"""
    conn = get_database_connection()
    table_name = f"{category.lower().replace(' ', '_')}_bookmarks"
    
    try:
        df = pd.read_sql_query(f"""
            SELECT post_id, platform, author, content, url, created_at, value_score,
                   ai_summary, key_concepts, smart_tags, tags
            FROM {table_name}
            ORDER BY COALESCE(value_score, 0) DESC, created_at DESC
            LIMIT {limit}
        """, conn)
        conn.close()
        return df
    except Exception:
        # Fallback to unified posts table using AI 'category'
        try:
            df = pd.read_sql_query(
                """
                SELECT post_id, platform, author, content, url, created_at, value_score,
                       ai_summary, key_concepts
                FROM posts
                WHERE is_deleted = 0 AND LOWER(COALESCE(category, 'uncategorized')) = ?
                ORDER BY COALESCE(value_score, 0) DESC, created_at DESC
                LIMIT ?
                """,
                conn,
                params=(category.lower(), limit),
            )
            # Ensure expected columns exist
            if 'smart_tags' not in df.columns:
                df['smart_tags'] = None
            if 'tags' not in df.columns:
                df['tags'] = None
            conn.close()
            return df
        except Exception:
            conn.close()
            return pd.DataFrame()

def move_post_to_category(post_id: str, target_category: str):
    """Move a post to a different category"""
    conn = get_database_connection()
    cursor = conn.cursor()
    
    try:
        # Get post data from manual review
        cursor.execute("""
            SELECT post_id, platform, author, content, url, created_at, value_score,
                   ai_summary, key_concepts, smart_tags
            FROM manual_review_bookmarks
            WHERE post_id = ?
        """, (post_id,))
        
        post_data = cursor.fetchone()
        if post_data:
            # Insert into target category
            target_table = f"{target_category.lower().replace(' ', '_')}_bookmarks"
            cursor.execute(f"""
                INSERT INTO {target_table} 
                (post_id, platform, author, content, url, created_at, value_score,
                 ai_summary, key_concepts, smart_tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, post_data)
            
            # Remove from manual review
            cursor.execute("DELETE FROM manual_review_bookmarks WHERE post_id = ?", (post_id,))
            
            conn.commit()
            conn.close()
            return True
    except Exception:
        conn.close()
        return False

def format_content(content, max_length=150):
    """Format content for display"""
    if content is None:
        return ""
    # Respect density preference
    dense = st.session_state.get('feed_density', 'Comfy') == 'Compact'
    limit = 90 if dense else max_length
    if len(content) > limit:
        return content[:limit] + "..."
    return content

def get_comments_for_post(post_id):
    """Get comments for a specific post"""
    try:
        # Check if we have comment data in the output directory
        comment_file = f"output/data/comments/{post_id}_comments.json"
        if os.path.exists(comment_file):
            with open(comment_file, 'r') as f:
                import json
                comments_data = json.load(f)
                return comments_data.get('comments', [])[:5]  # Return top 5 comments
        return []
    except Exception:
        return []

def create_streamlit_card(post, is_review: bool = False, unique_key: Optional[str] = None, widget_suffix: str = ""):
    """Create a beautiful, modern card with platform-specific styling.

    unique_key ensures Streamlit widget keys are stable and unique per card.
    """
    
    # Platform-specific styling with more prominent colors
    platform_config = {
        'twitter': {
            'icon': '🐦',
            'bg_color': '#E3F2FD',
            'border_color': '#1DA1F2',
            'text_color': '#1DA1F2',
            'header_bg': '#1DA1F2',
            'tint_bg': '#0e2331'  # bluish tint for dark theme
        },
        'reddit': {
            'icon': '📱',
            'bg_color': '#FFEBEE',
            'border_color': '#FF4500',
            'text_color': '#FF4500',
            'header_bg': '#FF4500',
            'tint_bg': '#2b140b'  # orange tint for dark theme
        },
        'threads': {
            'icon': '🧵',
            'bg_color': '#F5F5F5',
            'border_color': '#000000',
            'text_color': '#000000',
            'header_bg': '#000000',
            'tint_bg': '#141414'
        },
        'linkedin': {
            'icon': '💼',
            'bg_color': '#E3F2FD',
            'border_color': '#0077B5',
            'text_color': '#0077B5',
            'header_bg': '#0077B5',
            'tint_bg': '#0b1f2c'
        }
    }
    
    platform = resolve_platform(post)
    platform_info = platform_config.get(platform, {
        'icon': '📱', 
        'bg_color': '#FFFFFF',  # Changed to pure white for better visibility
        'border_color': '#666666', 
        'text_color': '#333333',  # Darker text for better contrast
        'header_bg': '#666666'
    })
    
    # Score styling
    score = post['value_score'] if pd.notna(post['value_score']) else None
    if score is None:
        score_emoji = "❓"
        score_color = "#999999"
        score_display = "N/A"
    elif score >= 8.0:
        score_emoji = "🔥"
        score_color = "#00AA88"  # Darker green for better visibility
        score_display = f"{score:.1f}"
    elif score >= 6.0:
        score_emoji = "⭐"
        score_color = "#FF9900"  # Darker orange for better visibility
        score_display = f"{score:.1f}"
    else:
        score_emoji = "📝"
        score_color = "#CC0000"  # Darker red for better visibility
        score_display = f"{score:.1f}"
    
    # Create card with simplified, consistent styling (pure HTML/Markdown)
    with st.container():
        content_text, content_links = _display_text_and_links(post.get('content'), 200)

        # Pull richer fields for the preview
        ai_summary = (post.get('ai_summary') or post.get('summary') or '').strip()
        key_concepts_raw = post.get('key_concepts')
        key_concepts: list[str] = []
        if key_concepts_raw is not None and not (isinstance(key_concepts_raw, float) and pd.isna(key_concepts_raw)):
            if isinstance(key_concepts_raw, str):
                try:
                    parsed = ast.literal_eval(key_concepts_raw)
                    if isinstance(parsed, (list, tuple)):
                        key_concepts = [str(x) for x in parsed]
                    else:
                        key_concepts = [str(parsed)]
                except Exception:
                    # Attempt JSON-like split fallback
                    if "," in key_concepts_raw:
                        key_concepts = [x.strip() for x in key_concepts_raw.split(",") if x.strip()]
                    else:
                        key_concepts = [key_concepts_raw]
            elif isinstance(key_concepts_raw, (list, tuple)):
                key_concepts = [str(x) for x in key_concepts_raw]

        card_bg = platform_info.get('tint_bg', '#0f1420')
        sentiment = str(post.get('sentiment') or '').lower()
        sentiment_color = {
            'positive': '#20c997',
            'negative': '#ff4d4f',
            'mixed': '#f59f00',
            'neutral': '#6c757d',
        }.get(sentiment, '#6c757d')

        # Parse actionable insights for quick preview
        actionable_raw = post.get('actionable_insights')
        actionable: list[str] = []
        if actionable_raw and not (isinstance(actionable_raw, float) and pd.isna(actionable_raw)):
            if isinstance(actionable_raw, str):
                try:
                    parsed = ast.literal_eval(actionable_raw)
                    if isinstance(parsed, (list, tuple)):
                        actionable = [str(x) for x in parsed][:2]
                except Exception:
                    pass
            elif isinstance(actionable_raw, (list, tuple)):
                actionable = [str(x) for x in actionable_raw][:2]

        text_color = platform_info['text_color']
        border_color = platform_info['border_color']

        # Build concise summary preview for immediate understanding
        def _one_liner(text: str, limit: int = 180) -> str:
            t = (text or '').strip()
            if len(t) <= limit:
                return t
            cut = t[:limit].rsplit(' ', 1)[0]
            return cut + '…'

        summary_preview = _one_liner(ai_summary or content_text, 180)

        html = f"""
        <style>
        .pm-card {{border-radius:12px;padding:16px;margin:10px 0;}}
        .pm-row {{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;}}
        .pm-avatar {{width:38px;height:38px;border-radius:50%;color:#fff;display:flex;align-items:center;justify-content:center;font-weight:700}}
        .pm-name {{font-weight:600;font-size:15px;color:#e6e6e6}}
        .pm-score {{background:{score_color}20;color:{score_color};border:1px solid {score_color}60;border-radius:14px;padding:4px 8px;font-weight:700;font-size:12px}}
        .pm-content {{margin-top:10px;font-size:15px;line-height:1.6;color:#e6e6e6}}
        .pm-subtle {{color:#9aa4b2;font-size:12px;margin-top:6px}}
        .pm-summary {{margin-top:8px;color:#e6e6e6;background:{text_color}10;border:1px solid {text_color}25;border-radius:8px;padding:8px 10px;font-size:14px;line-height:1.5}}
        .pm-bullets {{margin:6px 0 0 0;padding-left:18px;font-size:13px;color:#cbd3df}}
        .pm-chip {{border-radius:14px;padding:3px 8px;font-size:12px;margin-right:6px;display:inline-block;margin-top:6px}}
        </style>
        <div class='pm-card' style='background:{card_bg};border:1px solid {border_color}40;'>
          <div class='pm-row'>
            <div style='display:flex;align-items:center;gap:10px;'>
              <div class='pm-avatar' style='background:{platform_info['header_bg']};'>{(post['author'][:1].upper() if post['author'] else 'U')}</div>
              <div>
                <div class='pm-name'>{post['author'] if post['author'] else 'Unknown Author'}</div>
                <div class='pm-meta' style='font-size:12px;color:{text_color};'>{platform_info['icon']} {post['platform'].title()}</div>
              </div>
            </div>
            <div class='pm-score'>{score_emoji} {score_display}</div>
          </div>
          <div class='pm-content'>{content_text}</div>
          <div class='pm-summary'>{summary_preview}</div>
          <div style='margin-top:6px;display:flex;gap:8px;align-items:center;'>
            <span class='pm-chip' style='background:{sentiment_color}20;color:{sentiment_color};border:1px solid {sentiment_color}40;'>🧭 {sentiment.title() or 'Neutral'}</span>
          </div>
          {('<ul class="pm-bullets">' + ''.join([f"<li>{a}</li>" for a in actionable]) + '</ul>') if actionable else ''}
        """

        # Links
        if content_links:
            chips = "".join([f"<span class='pm-chip' style='background:{text_color}15;color:{text_color};border:1px solid {text_color}30;'>🔗 {_humanize_url(u)}</span>" for u in content_links[:3]])
            html += f"<div style='margin-top:6px'>{chips}</div>"

        # Category/tags and AI key concepts
        if 'category' in post and pd.notna(post['category']):
            html += f"<div class='pm-chip' style='background:{text_color}15;color:{text_color};border:1px solid {text_color}30;'>🏷️ {post['category']}</div>"

        tags_display = []
        if key_concepts and isinstance(key_concepts, (list, tuple)):
            tags_display.extend([str(k) for k in key_concepts][:5])
        if post.get('concepts') is not None and not (isinstance(post.get('concepts'), float) and pd.isna(post.get('concepts'))):
            concepts = post['concepts']
            if isinstance(concepts, str):
                try:
                    concepts_list = ast.literal_eval(concepts)
                    tags_display.extend(concepts_list[:4])
                except:
                    tags_display.append(concepts)
            else:
                tags_display.append(str(concepts))
        if tags_display:
            html += "<div>" + "".join([f"<span class='pm-chip' style='background:{text_color}15;color:{text_color};border:1px solid {text_color}30;'>{t}</span>" for t in tags_display]) + "</div>"

        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)
        
        # Build a stable unique key for widgets
        base_key = unique_key or get_post_key(post)
        key_sfx = f"_{widget_suffix}" if widget_suffix else ""

        # Actions: pinned in a clean row with consistent spacing
        col1, col2, col3 = st.columns([1,1,1], gap="small")
        is_reddit = str(post.get('platform','')).lower() == 'reddit'
        with col1:
            # Only show external source for non-Reddit to avoid page jumps
            if not is_reddit and st.button("🔗 Source", key=f"source_{base_key}{key_sfx}"):
                import webbrowser
                if post.get('url'):
                    webbrowser.open(post['url'])
        with col2:
            if st.button("📖 Full", key=f"full_{base_key}{key_sfx}"):
                # Toggle inline full: close if already open for this card
                current = st.session_state.get('expanded_post')
                if current is not None and get_post_key(current) == base_key:
                    st.session_state['expanded_post'] = None
                else:
                    st.session_state['expanded_post'] = post
                st.rerun()
        with col3:
            if is_reddit:
                if st.button("💬 Comments", key=f"comments_{base_key}{key_sfx}"):
                    post_id_for_comments = str(post.get('post_id') or post.get('id') or '')
                    comments = get_comments_for_post(post_id_for_comments)
                    if comments:
                        st.markdown("**Comments:**")
                        for comment in comments:
                            st.markdown(f"- {comment}")
                    else:
                        st.info("No cached comments available")

def main():
    st.set_page_config(
        page_title="PrisMind",
        page_icon="🧠",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Clean header
    st.title("🧠 PrisMind")
    st.caption("Your AI-powered knowledge base")
    # Subtle global style tweaks
    st.markdown(
        """
        <style>
        /* Tighter top spacing and consistent content width */
        .block-container { padding-top: 1rem; }
        /* Hide default Streamlit menu/footer for a cleaner look */
        footer { visibility: hidden; }
        #MainMenu { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # Full post modal-like view
    if 'full_post' not in st.session_state:
        st.session_state['full_post'] = None

    # Get data
    counts = get_category_counts()
    
    # Simple sidebar
    st.sidebar.title("Navigation")
    st.sidebar.caption("Use filters below to refine the feed.")
    
    # Global display mode (default OFF to show all posts with accordion preview)
    st.sidebar.checkbox("Single Post Mode", value=False, key="single_mode")

    # Quick stats
    total_posts = sum(counts.values())
    st.sidebar.metric("Total Posts", total_posts)
    if total_posts == 0:
        st.sidebar.info("No posts yet. Run the collector to populate the database.")
    
    # Navigation
    page = st.sidebar.radio(
        "Pages",
        ["🏠 Feed", "⚠️ Review", "📊 Browse", "🔍 Search"],
        label_visibility="collapsed"
    )
    
    # Inline full view state
    if 'expanded_post' not in st.session_state:
        st.session_state['expanded_post'] = None

    if st.session_state['full_post'] is not None:
        render_full_post(st.session_state['full_post'])
    elif page == "🏠 Feed":
        show_feed(counts)
    elif page == "⚠️ Review":
        show_manual_review()
    elif page == "📊 Browse":
        show_browse_categories(counts)
    elif page == "🔍 Search":
        show_advanced_search(counts)

def show_feed(counts):
    """Show clean, filtered feed"""
    
    # Get available categories
    available_categories = get_available_categories()
    
    # Simple filters
    st.sidebar.markdown("### Filters")
    
    # Filter columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Category filter
        category_options = ["All"] + list(available_categories.keys())
        selected_category = st.sidebar.selectbox("Category", category_options, key="filter_category")
    
    with col2:
        # Platform filter
        platform_options = ["All", "Twitter", "Reddit", "Threads"]
        selected_platform = st.sidebar.selectbox("Platform", platform_options, key="filter_platform")
    
    with col3:
        # Score filter
        min_score = st.sidebar.slider("Min Score", 0.0, 10.0, 0.0, 0.5, key="filter_min_score")
    
    with col4:
        # Search
        search_term = st.sidebar.text_input("Search", placeholder="Search content...", key="filter_search")

    # Display options
    st.sidebar.markdown("### Display")
    sort_by = st.sidebar.selectbox(
        "Sort by",
        ["Score (desc)", "Newest", "Oldest", "Platform"],
        index=0,
        key="feed_sort_by",
    )
    density = st.sidebar.radio("Density", ["Comfy", "Compact"], index=0, horizontal=True, key="feed_density")
    per_page = st.sidebar.slider("Posts per page", 5, 50, 20, 5, key="feed_per_page")
    if 'feed_page' not in st.session_state:
        st.session_state['feed_page'] = 0
    
    # Get posts based on selected category
    if selected_category == "All":
        # Get posts from all categories
        all_posts = []
        for category_name, table_name in available_categories.items():
            category_key = table_name.replace('_bookmarks', '')
            posts = get_posts_from_category(category_key, 10)  # Reduced to avoid too many posts
            if not posts.empty:
                # Add category column for tracking
                posts['category'] = category_name
                all_posts.append(posts)
        
        if all_posts:
            # Filter out empty and all-NA DataFrames before concatenation to avoid pandas warning
            non_empty_posts = []
            for df in all_posts:
                try:
                    if df is not None and not df.empty:
                        # Drop columns that are entirely NA to avoid dtype ambiguity
                        cleaned = df.dropna(axis=1, how='all')
                        if not cleaned.empty and not cleaned.isna().all().all():
                            non_empty_posts.append(cleaned)
                except Exception:
                    continue
            if non_empty_posts:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', category=FutureWarning)
                    posts_df = pd.concat(non_empty_posts, ignore_index=True)
            else:
                posts_df = pd.DataFrame()
        else:
            posts_df = pd.DataFrame()
    else:
        # Get posts from specific category
        table_name = available_categories[selected_category]
        category_key = table_name.replace('_bookmarks', '')
        posts_df = get_posts_from_category(category_key, 200)  # Increased limit significantly
        if not posts_df.empty:
            posts_df['category'] = selected_category
    
    # Debug: Show what we got (only if needed)
    if st.sidebar.checkbox("Show Debug Info", value=False):
        st.sidebar.markdown("### Debug Info")
        st.sidebar.write(f"Category: {selected_category}")
        st.sidebar.write(f"Posts found: {len(posts_df) if not posts_df.empty else 0}")
        if not posts_df.empty:
            st.sidebar.write(f"Platforms: {list(posts_df['platform'].unique())}")
            try:
                st.sidebar.write(f"Score range: {posts_df['value_score'].min():.1f} - {posts_df['value_score'].max():.1f}")
            except Exception:
                pass
    
    # Apply filters
    if not posts_df.empty:
        # Platform filter
        if selected_platform != "All":
            posts_df = posts_df[posts_df['platform'].str.lower() == selected_platform.lower()]
        
        # Score filter - handle NULL values
        if min_score > 0:
            # Only filter by score if min_score > 0, and handle NULL values
            posts_df = posts_df[(posts_df['value_score'] >= min_score) | (posts_df['value_score'].isna())]
        
        # Search filter
        if search_term:
            posts_df = posts_df[posts_df['content'].str.contains(search_term, case=False, na=False)]
        
        # Sorting
        if sort_by == "Score (desc)":
            posts_df = posts_df.sort_values('value_score', ascending=False, na_position='last')
        elif sort_by == "Newest":
            if 'created_at' in posts_df.columns:
                posts_df = posts_df.sort_values('created_at', ascending=False)
        elif sort_by == "Oldest":
            if 'created_at' in posts_df.columns:
                posts_df = posts_df.sort_values('created_at', ascending=True)
        elif sort_by == "Platform":
            posts_df = posts_df.sort_values('platform', ascending=True)
        
            # Display results with better info
        if not posts_df.empty:
            st.markdown(f"### 📊 {len(posts_df)} Posts Found")
            
            # Show category info if filtering by specific category
            if selected_category != "All":
                st.info(f"Showing posts from: **{selected_category}**")
            
            # Show filter info
            filter_info = []
            if selected_platform != "All":
                filter_info.append(f"Platform: {selected_platform}")
            if min_score > 0:
                filter_info.append(f"Min Score: {min_score}")
            if search_term:
                filter_info.append(f"Search: '{search_term}'")
            
            if filter_info:
                st.caption(f"Filters: {' | '.join(filter_info)}")
            
            # Pagination
            total = len(posts_df)
            start = st.session_state['feed_page'] * per_page
            if start >= total:
                st.session_state['feed_page'] = 0
                start = 0
            end = min(start + per_page, total)
            st.caption(f"Showing {start+1}-{end} of {total}")

            # One-column rendering with inline full content
            view_df = posts_df.iloc[start:end]
            for idx, post in view_df.iterrows():
                stable_key = get_post_key(post)
                # Add page/row suffix to guarantee uniqueness across rerenders
                suffix = f"_{st.session_state.get('feed_page',0)}_{idx}"
                create_streamlit_card(post, unique_key=stable_key, is_review=False, widget_suffix=suffix)
                ep = st.session_state.get('expanded_post')
                if ep is not None and get_post_key(ep) == stable_key:
                    render_full_inline(ep, base_key=stable_key)

            # Pagination controls
            nav_cols = st.columns([1,1,4])
            with nav_cols[0]:
                if st.button("◀ Prev Page", disabled=start == 0, key="feed_prev_page"):
                    st.session_state['feed_page'] = max(0, st.session_state['feed_page'] - 1)
                    st.rerun()
            with nav_cols[1]:
                if st.button("Next Page ▶", disabled=end >= total, key="feed_next_page"):
                    if end < total:
                        st.session_state['feed_page'] += 1
                        st.rerun()
            
            # Show more info if there are more posts
            if len(posts_df) > 20:
                st.info(f"Showing first 20 of {len(posts_df)} posts. Use filters to narrow down results.")
        else:
            st.info("No posts match your filters")
    else:
        st.info("No posts found in selected category")

def show_manual_review():
    """Show manual review section with modern cards"""
    st.markdown("### ⚠️ Manual Review")
    st.markdown("Posts that need your attention and categorization")
    
    df = get_manual_review_posts()
    
    if df.empty:
        st.success("🎉 No posts need manual review!")
        return
    
    st.write(f"Showing {len(df)} posts that need review")
    
    # Advanced filters
    st.markdown("#### 🔍 Advanced Filters")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        platform_filter = st.selectbox("Platform", ["All"] + list(df['platform'].unique()))
    with col2:
        score_filter = st.selectbox("Sort by", ["Value Score", "Tech Score", "Business Score", "Research Score"])
    with col3:
        search_term = st.text_input("Search content", "")
    with col4:
        min_score = st.slider("Min Value Score", 0.0, 10.0, 0.0, 0.5)
    
    # Apply filters
    filtered_df = df.copy()
    
    if platform_filter != "All":
        filtered_df = filtered_df[filtered_df['platform'] == platform_filter]
    
    if search_term:
        filtered_df = filtered_df[filtered_df['content'].str.contains(search_term, case=False, na=False)]
    
    filtered_df = filtered_df[filtered_df['value_score'] >= min_score]
    
    if score_filter == "Value Score":
        filtered_df = filtered_df.sort_values('value_score', ascending=False)
    elif score_filter == "Tech Score":
        filtered_df = filtered_df.sort_values('tech_score', ascending=False)
    elif score_filter == "Business Score":
        filtered_df = filtered_df.sort_values('business_score', ascending=False)
    elif score_filter == "Research Score":
        filtered_df = filtered_df.sort_values('research_score', ascending=False)
    
    st.write(f"Showing {len(filtered_df)} posts")
    
    # Display posts
    for idx, row in filtered_df.iterrows():
        stable_key = get_post_key(row)
        create_streamlit_card(row, is_review=True, unique_key=stable_key)
        ep = st.session_state.get('expanded_post')
        if ep is not None and get_post_key(ep) == stable_key:
            render_full_inline(ep, base_key=stable_key)
        
        # Categorization buttons
        st.markdown("**Move to Category:**")
        col_a, col_b, col_c, col_d = st.columns(4)
        
        with col_a:
            if st.button("🖥️ Tech", key=f"tech_{row['post_id']}", use_container_width=True):
                if move_post_to_category(row['post_id'], 'tech'):
                    st.success("Moved to Tech!")
                    st.rerun()
                else:
                    st.error("Failed to move post")
        
        with col_b:
            if st.button("💼 Business", key=f"bus_{row['post_id']}", use_container_width=True):
                if move_post_to_category(row['post_id'], 'business'):
                    st.success("Moved to Business!")
                    st.rerun()
                else:
                    st.error("Failed to move post")
        
        with col_c:
            if st.button("🔬 Research", key=f"res_{row['post_id']}", use_container_width=True):
                if move_post_to_category(row['post_id'], 'research'):
                    st.success("Moved to Research!")
                    st.rerun()
                else:
                    st.error("Failed to move post")
        
        with col_d:
            if st.button("🛠️ Tools", key=f"tools_{row['post_id']}", use_container_width=True):
                if move_post_to_category(row['post_id'], 'tools_to_try'):
                    st.success("Moved to Tools!")
                    st.rerun()
                else:
                    st.error("Failed to move post")

def show_browse_categories(counts):
    """Show category browsing with modern cards"""
    st.markdown("### 📊 Browse by Category")
    
    # Group categories logically
    categories = {
        "Learning & Skills": ["Step By Step Tutorials", "Video Tutorials", "Code Examples", "Best Practices"],
        "Tools & Resources": ["Tools To Try", "Ai Tools", "Development Tools", "Productivity Tools"],
        "Business & Growth": ["Marketing Strategies", "Startup Advice", "Monetization Guides"],
        "Quick Wins": ["Quick Tips", "Time Savers", "Money Savers"]
    }
    
    selected_group = st.selectbox("Choose a category group:", list(categories.keys()))
    
    if selected_group:
        group_categories = categories[selected_group]
        available_categories = [cat for cat in group_categories if cat in counts and counts[cat] > 0]
        
        if available_categories:
            selected_category = st.selectbox("Choose a specific category:", available_categories)
            
            if selected_category:
                posts = get_posts_from_category(selected_category, limit=20)
                if not posts.empty:
                    st.markdown(f"**{selected_category} ({len(posts)} posts)**")
                    
                    # Advanced filters
                    st.markdown("#### 🔍 Filters")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        platform_filter = st.selectbox("Platform", ["All"] + list(posts['platform'].unique()), key="cat_platform")
                    with col2:
                        search_term = st.text_input("Search content", key="cat_search")
                    with col3:
                        min_score = st.slider("Min Value Score", 0.0, 10.0, 0.0, 0.5, key="cat_score")
                    
                    # Apply filters
                    filtered_posts = posts.copy()
                    if platform_filter != "All":
                        filtered_posts = filtered_posts[filtered_posts['platform'] == platform_filter]
                    if search_term:
                        filtered_posts = filtered_posts[filtered_posts['content'].str.contains(search_term, case=False, na=False)]
                    
                    # Score filter - handle NULL values
                    if min_score > 0:
                        filtered_posts = filtered_posts[(filtered_posts['value_score'] >= min_score) | (filtered_posts['value_score'].isna())]
                    
                    # Display results
                    st.markdown(f"**Showing {len(filtered_posts)} of {len(posts)} posts**")
                    for idx, post in filtered_posts.iterrows():
                        stable_key = get_post_key(post)
                        create_streamlit_card(post, unique_key=stable_key)
                        ep = st.session_state.get('expanded_post')
                        if ep is not None and get_post_key(ep) == stable_key:
                            render_full_inline(ep, base_key=stable_key)

def show_advanced_search(counts):
    """Show advanced search functionality"""
    st.markdown("### 🔍 Advanced Search")
    
    # Search across all categories
    search_term = st.text_input("Search across all content:", placeholder="Enter keywords...")
    
    # Advanced search options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_in = st.multiselect(
            "Search in:",
            ["Content", "AI Summary", "Key Concepts", "Smart Tags"],
            default=["Content", "AI Summary"]
        )
    
    with col2:
        min_score = st.slider("Minimum Value Score", 0.0, 10.0, 0.0, 0.5)
    
    with col3:
        platforms = st.multiselect(
            "Platforms:",
            ["Twitter", "Reddit", "Threads"],
            default=["Twitter", "Reddit", "Threads"]
        )
    
    if search_term:
        # Search in all tables
        conn = get_database_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_bookmarks'")
        tables = cursor.fetchall()
        
        all_results = []
        for table in tables:
            table_name = table[0]
            try:
                # Build search conditions
                search_conditions = []
                if "Content" in search_in:
                    search_conditions.append("content LIKE ?")
                if "AI Summary" in search_in:
                    search_conditions.append("ai_summary LIKE ?")
                if "Key Concepts" in search_in:
                    search_conditions.append("key_concepts LIKE ?")
                if "Smart Tags" in search_in:
                    search_conditions.append("smart_tags LIKE ?")
                
                if search_conditions:
                    where_clause = " OR ".join(search_conditions)
                    query = f"""
                        SELECT post_id, platform, author, content, url, value_score, ai_summary, key_concepts, smart_tags
                        FROM {table_name}
                        WHERE ({where_clause}) AND value_score >= ? AND platform IN ({','.join(['?'] * len(platforms))})
                        ORDER BY value_score DESC
                        LIMIT 10
                    """
                    
                    params = [f'%{search_term}%'] * len(search_conditions) + [min_score] + platforms
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    for result in results:
                        all_results.append({
                            'table': table_name,
                            'post_id': result[0],
                            'platform': result[1],
                            'author': result[2],
                            'content': result[3],
                            'url': result[4],
                            'value_score': result[5],
                            'ai_summary': result[6],
                            'key_concepts': result[7],
                            'smart_tags': result[8]
                        })
            except:
                continue
        
        conn.close()
        
        if all_results:
            st.write(f"Found {len(all_results)} results")
            
            # Sort by value score
            all_results.sort(key=lambda x: x['value_score'], reverse=True)
            
            # Display results
            for idx, result in enumerate(all_results):
                # Convert tuple/list results to dict-like access if needed
                if isinstance(result, (list, tuple)) and len(result) >= 8:
                    result_obj = {
                        'table': 'unknown',
                        'post_id': result[0],
                        'platform': result[1],
                        'author': result[2],
                        'content': result[3],
                        'url': result[4],
                        'value_score': result[5],
                        'ai_summary': result[6],
                        'key_concepts': result[7],
                    }
                else:
                    result_obj = result
                stable_key = get_post_key(result_obj)
                create_streamlit_card(result_obj, unique_key=stable_key)
                ep = st.session_state.get('expanded_post')
                if ep is not None and get_post_key(ep) == stable_key:
                    render_full_inline(ep, base_key=stable_key)

def render_single_from_df(df: pd.DataFrame, session_prefix: str):
    """Render a single post at a time with navigation controls.
    session_prefix scopes the navigation state per page (feed/browse/review/search).
    """
    if df is None or df.empty:
        st.info("No posts to show")
        return

    index_key = f"{session_prefix}_index"
    total_key = f"{session_prefix}_total"
    total_posts = len(df)

    # Reset index if dataset changed in size
    if st.session_state.get(total_key) != total_posts:
        st.session_state[index_key] = 0
        st.session_state[total_key] = total_posts

    if index_key not in st.session_state:
        st.session_state[index_key] = 0

    current_index = st.session_state[index_key] % total_posts
    current_row = df.iloc[current_index]

    # Progress header
    st.caption(f"Post {current_index + 1} of {total_posts}")

    # Render card
    unique_key = f"{current_row.get('post_id','unknown')}_{session_prefix}_{current_index}"
    create_streamlit_card(current_row, unique_key=unique_key)

    # Navigation controls
    nav_cols = st.columns([1,1,1,5])
    with nav_cols[0]:
        if st.button("⏮ Prev", key=f"prev_{session_prefix}_{current_index}"):
            st.session_state[index_key] = (current_index - 1) % total_posts
            st.rerun()
    with nav_cols[1]:
        if st.button("⏭ Next", key=f"next_{session_prefix}_{current_index}"):
            st.session_state[index_key] = (current_index + 1) % total_posts
            st.rerun()
    with nav_cols[2]:
        if st.button("🔀 Random", key=f"rand_{session_prefix}_{current_index}"):
            import random
            st.session_state[index_key] = random.randrange(total_posts)
            st.rerun()
        else:
            st.info("No results found")

if __name__ == "__main__":
    main()