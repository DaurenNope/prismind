#!/usr/bin/env python3
"""
Curated Posts Tab - View and post from usable_posts table with ONE CLICK
"""
import streamlit as st
import json
import os
from pathlib import Path
from datetime import datetime
from src.database.manager import SupabaseManager


def _check_credentials():
    """Check which platform credentials are available"""
    creds = {
        'twitter': False,
        'threads': False
    }

    # Check Twitter API
    twitter_key = os.getenv('TWITTER_API_KEY')
    if twitter_key:
        creds['twitter'] = True

    # Check Threads cookies
    threads_cookies = Path('cookies/threads_cookies.json')
    if threads_cookies.exists():
        creds['threads'] = True

    return creds


def _get_persona_platforms(persona):
    """Get available platforms for a persona based on account setup"""
    # Account mappings:
    # - cryptoniard: Twitter (but not used for curated posting)
    # - qronoya: Threads only
    # - aspandead: None configured yet

    persona_accounts = {
        'qronoya': ['threads'],  # qronoya only posts to Threads
        'aspandead': [],  # No accounts configured
        'claimzilla': []  # No accounts configured
    }

    return persona_accounts.get(persona, [])


def render_curated_posts_tab():
    """Render the curated posts viewer tab with direct posting from usable_posts table"""
    st.header("💎 Curated Posts")
    st.markdown("**Your high-quality, usable content from the usable_posts table - Post with one click!**")

    # Check available credentials
    available_creds = _check_credentials()

    # Show credential status
    cred_status = []
    if available_creds['twitter']:
        cred_status.append("🐦 Twitter")
    if available_creds['threads']:
        cred_status.append("🧵 Threads")

    if cred_status:
        st.caption(f"Connected: {' • '.join(cred_status)}")
    else:
        st.warning("⚠️ No platform credentials configured. Configure Twitter API or Threads cookies to post.")

    # Load posts from usable_posts table
    try:
        supabase = SupabaseManager().client
        
        # Fetch all usable posts
        result = supabase.table("usable_posts").select("*").order("created_at", desc=True).limit(500).execute()
        all_posts = result.data if result.data else []
        
        if not all_posts:
            st.info("📭 No usable posts found. Run the curation script to populate the usable_posts table.")
            if st.button("🔄 Refresh"):
                st.rerun()
            return
        
        # Convert to dict format for compatibility
        for post in all_posts:
            # Map usable_posts fields to expected format
            post['_persona'] = post.get('best_persona_key') or 'unknown'
            post['platform'] = post.get('platform') or 'unknown'
            raw_quality = post.get('quality_score')
            post['quality_score'] = float(raw_quality) * 10 if raw_quality is not None else 0  # Convert 0-10 to 0-100
            post['rewritten_content'] = post.get('ai_summary') or post.get('content', '')  # Use AI summary as content
            post['original_content'] = post.get('content', '')
            post['original_url'] = post.get('url', '')
            post['original_author'] = post.get('author', '')
            post['content_type'] = (post.get('category') or 'unknown').lower()
        
    except Exception as e:
        st.error(f"❌ Error loading usable posts: {e}")
        st.info("💡 Make sure Supabase is configured and the usable_posts table exists.")
        return

    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📝 Total Posts", len(all_posts))
    with col2:
        personas = set(p['_persona'] for p in all_posts)
        st.metric("🎭 Personas", len(personas))
    with col3:
        platforms = set(p.get('platform', 'unknown') for p in all_posts)
        st.metric("📱 Platforms", len(platforms))
    with col4:
        avg_quality = sum(p.get('quality_score', 0) for p in all_posts) / len(all_posts) if all_posts else 0
        st.metric("⭐ Avg Quality", f"{avg_quality:.0f}/100")

    st.markdown("---")

    # Filters
    col_persona, col_platform, col_sort = st.columns(3)

    with col_persona:
        persona_options = sorted({p for p in personas if isinstance(p, str)})
        persona_filter = st.selectbox(
            "Filter by Persona",
            ["All"] + persona_options,
            key="curated_persona_filter"
        )

    with col_platform:
        platform_options = sorted({p for p in platforms if isinstance(p, str)})
        platform_filter = st.selectbox(
            "Filter by Platform",
            ["All"] + platform_options,
            key="curated_platform_filter"
        )

    with col_sort:
        sort_order = st.selectbox(
            "Sort by",
            ["Newest First", "Oldest First", "Highest Quality"],
            key="curated_sort"
        )

    # Apply filters
    filtered_posts = all_posts
    if persona_filter != "All":
        filtered_posts = [p for p in filtered_posts if p['_persona'] == persona_filter]
    if platform_filter != "All":
        filtered_posts = [p for p in filtered_posts if p.get('platform') == platform_filter]

    # Apply sorting
    if sort_order == "Oldest First":
        filtered_posts.sort(key=lambda x: x.get('created_at', ''))
    elif sort_order == "Highest Quality":
        filtered_posts.sort(key=lambda x: x.get('quality_score', 0), reverse=True)

    st.caption(f"Showing {len(filtered_posts)} of {len(all_posts)} posts")

    st.markdown("---")

    # Display posts as cards
    for i, post in enumerate(filtered_posts):
        # Persona metadata
        persona_emojis = {
            "qronoya": "💡",
            "aspandead": "🖤",
            "claimzilla": "💎"
        }
        persona_names = {
            "qronoya": "Qronoya",
            "aspandead": "Aspandead",
            "claimzilla": "Claimzilla"
        }

        persona_emoji = persona_emojis.get(post['_persona'], "🎭")
        persona_name = persona_names.get(post['_persona'], post['_persona'].title())

        # Platform icon
        platform_icons = {
            "twitter": "🐦",
            "threads": "🧵",
            "linkedin": "💼",
            "telegram": "📱"
        }
        platform_icon = platform_icons.get(post.get('platform', 'twitter'), "📱")

        # Quality rating
        quality = post.get('quality_score', 0)
        quality_rating = post.get('quality_rating', 'good')
        quality_emoji = "⭐⭐⭐" if quality >= 90 else "⭐⭐" if quality >= 70 else "⭐"

        # Time ago - handle both ISO format strings and datetime objects
        try:
            created_at = post.get('created_at', '')
            if isinstance(created_at, str):
                # Try parsing ISO format
                if 'T' in created_at:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    created_dt = datetime.fromisoformat(created_at)
            elif isinstance(created_at, datetime):
                created_dt = created_at
            else:
                created_dt = datetime.now()
            time_ago = _time_ago(created_dt)
        except Exception as e:
            time_ago = "recently"

        # Create a nice card with container
        with st.container():
            # Header with persona and quality
            col_header1, col_header2 = st.columns([3, 1])
            with col_header1:
                st.markdown(f"### {persona_emoji} {persona_name}")
                st.caption(f"{platform_icon} {post.get('platform', 'twitter').title()} • {time_ago} • {post.get('content_type', 'unknown').replace('_', ' ').title()}")
            with col_header2:
                st.markdown(f"**{quality_emoji}**")
                st.caption(f"{quality}/100")

            # Content displayed like a real social media post
            # For usable_posts, we use ai_summary as the postable content
            content = post.get('rewritten_content', '') or post.get('ai_summary', '') or post.get('content', '')
            
            # If content is too long, truncate it for display (social media posts should be concise)
            max_display_length = 500  # Display limit
            if len(content) > max_display_length:
                content_display = content[:max_display_length] + "..."
            else:
                content_display = content

            # Convert newlines to <br> tags and escape HTML
            import html
            content_html = html.escape(content_display).replace('\n', '<br>')

            # Display content in a clean, professional container
            st.markdown(
                f"""
                <div style="
                    background-color: #f9fafb;
                    padding: 20px;
                    border-radius: 8px;
                    border-left: 4px solid #2563eb;
                    margin: 16px 0;
                    border: 1px solid #e5e7eb;
                ">
                    <p style="
                        color: #111827;
                        font-size: 15px;
                        line-height: 1.6;
                        margin: 0;
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                    ">{content_html}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # Stats
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.caption(f"📏 {len(content)} chars")
            with col_stat2:
                # Detect language
                if content:
                    russian_chars = sum(1 for c in content if '\u0400' <= c <= '\u04FF')
                    latin_chars = sum(1 for c in content if 'a' <= c.lower() <= 'z')
                    lang = "🇷🇺 Russian" if russian_chars > latin_chars else "🇬🇧 English"
                    st.caption(lang)
            with col_stat3:
                st.caption(f"💯 {quality_rating.title()}")

            # Action buttons - THE MAIN POINT OF THIS PAGE!
            col_action1, col_action2, col_action3, col_action4 = st.columns(4)

            with col_action1:
                # POST NOW button - the main feature!
                if st.button(f"🚀 Post Now", key=f"post_{i}", use_container_width=True, type="primary"):
                    # Determine target platform from persona or post metadata
                    persona = post.get('_persona', 'qronoya')
                    target_platform = 'threads' if persona == 'qronoya' else 'twitter'
                    
                    # Use the full content (not truncated display version)
                    post_content = post.get('rewritten_content', '') or post.get('ai_summary', '') or post.get('content', '')

                    if target_platform == 'twitter':
                        try:
                            from src.publishing.platforms.twitter import TwitterPoster
                            poster = TwitterPoster()
                            # Post the tweet
                            result = poster.post_tweet(post_content)
                            if result and result.get('success'):
                                st.success(f"✅ Posted to Twitter as {persona_name}!")
                                st.balloons()
                            else:
                                error_msg = result.get('error', 'Unknown error') if result else 'No result returned'
                                st.error(f"❌ Failed to post: {error_msg}")
                        except ValueError as e:
                            st.error(f"❌ Twitter credentials missing: {e}")
                            st.info("💡 Configure Twitter API keys in .env file")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                            st.info("💡 Make sure Twitter API credentials are configured in .env")
                    else:
                        st.warning(f"⚠️ {platform.title()} posting not yet implemented")

            with col_action2:
                # Schedule for later
                if st.button(f"📅 Schedule", key=f"schedule_{i}", use_container_width=True):
                    st.info("💡 Go to 'Quick Post' tab to schedule this content")

            with col_action3:
                # Copy to clipboard
                if st.button(f"📋 Copy", key=f"copy_{i}", use_container_width=True):
                    # Show in code block for easy copying
                    with st.expander("📋 Content copied!", expanded=True):
                        st.code(content, language=None)

            with col_action4:
                # View original
                if st.button(f"👁️ Original", key=f"view_{i}", use_container_width=True):
                    with st.expander("📄 Original Post", expanded=True):
                        st.markdown(f"**Author:** {post.get('original_author', 'Unknown')}")
                        if post.get('original_url'):
                            st.markdown(f"**[View Source]({post['original_url']})**")
                        st.markdown("---")
                        st.text_area(
                            "Original Content",
                            value=post.get('original_content', 'N/A'),
                            height=100,
                            key=f"original_{i}",
                            label_visibility="collapsed"
                        )

            st.markdown("---")


def _time_ago(dt: datetime) -> str:
    """Convert datetime to human-readable 'time ago' format"""
    now = datetime.now()

    # Handle timezone-aware datetimes
    if dt.tzinfo is not None and now.tzinfo is None:
        from datetime import timezone
        now = now.replace(tzinfo=timezone.utc)
    elif dt.tzinfo is None and now.tzinfo is not None:
        dt = dt.replace(tzinfo=now.tzinfo)

    diff = now - dt
    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days}d ago"
    else:
        return dt.strftime("%b %d, %Y")
