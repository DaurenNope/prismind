#!/usr/bin/env python3
"""
Review Tab - Review and approve rewrites from database
Integrated into your existing Streamlit app
"""
import streamlit as st
import asyncio
from pathlib import Path
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

from src.services.new_database_manager import NewDatabaseManager
from src.database.manager import SupabaseManager
from src.publishing.rewriter import ContentRewriter
from src.publishing.scheduler import PublishingScheduler

# Language routing
LANGUAGE_MAP = {'threads': 'russian', 'twitter': 'english', 'telegram': 'russian', 'reddit': 'english'}
OUTPUT_PLATFORMS = {'threads': 'threads', 'twitter': 'twitter', 'reddit': 'threads', 'telegram': 'telegram'}


def render_review_tab():
    st.header("🔍 Review & Approve Rewrites")
    st.markdown("Review posts from your **673-post database** and approve/edit rewrites")

    # Initialize session state
    if 'review_queue' not in st.session_state:
        st.session_state.review_queue = []
        st.session_state.review_index = 0
        st.session_state.current_rewrite = None
        st.session_state.review_stats = {'approved': 0, 'rejected': 0, 'skipped': 0}

    # Top row: Load button + stats
    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
    with col1:
        load_from = st.selectbox("Load from", ["usable_posts (curated)", "posts (all)"], key="review_source")
        if st.button("📥 Load 5 Posts", type="primary"):
            try:
                if load_from == "usable_posts (curated)":
                    # Load from usable_posts table (curated, high-quality content)
                    supabase = SupabaseManager().client
                    result = supabase.table("usable_posts").select("*").order("created_at", desc=True).limit(15).execute()
                    posts = result.data if result.data else []
                else:
                    # Load from posts table (all posts)
                    db = NewDatabaseManager()
                    all_posts = db.get_posts(limit=15)
                    posts = [p for p in all_posts if p is not None]
                
                posts = posts[:5]  # Take first 5
                st.session_state.review_queue = posts
                st.session_state.review_index = 0
                st.session_state.current_rewrite = None
                st.success(f"Loaded {len(posts)} posts from {load_from}")
                st.rerun()
            except Exception as e:
                st.error(f"Error loading posts: {e}")
                st.info("💡 Make sure Supabase is configured and tables exist.")

    with col2:
        st.metric("✅ Approved", st.session_state.review_stats['approved'])
    with col3:
        st.metric("❌ Rejected", st.session_state.review_stats['rejected'])
    with col4:
        st.metric("⏭️ Skipped", st.session_state.review_stats['skipped'])

    # Check if queue is loaded
    if not st.session_state.review_queue:
        st.info("👆 Click 'Load Posts' to start reviewing")
        return

    # Check if we're done
    if st.session_state.review_index >= len(st.session_state.review_queue):
        st.success("✅ All posts reviewed! Load more to continue.")
        return

    # Get current post
    current_post = st.session_state.review_queue[st.session_state.review_index]
    source_platform = current_post.get('platform', 'unknown')
    output_platform = OUTPUT_PLATFORMS.get(source_platform, 'threads')
    language = LANGUAGE_MAP.get(output_platform, 'russian')

    # Progress
    progress = (st.session_state.review_index + 1) / len(st.session_state.review_queue)
    st.progress(progress)
    st.caption(f"Post {st.session_state.review_index + 1} of {len(st.session_state.review_queue)}")

    # Source post
    st.subheader("📝 Source Post")
    col1, col2 = st.columns([1, 3])
    with col1:
        st.info(f"**{source_platform.upper()}** → **{output_platform.upper()}**")
        st.caption(f"Language: **{language.upper()}**")
    with col2:
        if current_post.get('url'):
            st.caption(f"🔗 {current_post['url'][:60]}...")

    st.text_area("Content", current_post.get('content', current_post.get('title', ''))[:400] + "...", height=120, disabled=True)

    # Generate rewrite if needed
    if st.session_state.current_rewrite is None:
        with st.spinner(f"⏳ Generating {language} rewrite..."):
            rewriter = ContentRewriter()
            analyzed = {
                'content': current_post.get('content', ''),
                'category': 'Technology',
                'summary': current_post.get('content', '')[:200],
                'key_concepts': [],
                'topics': [],
                'rewrite_angles': [{'persona': 'qronoya', 'angle': 'Rewrite', 'tone': 'Natural', 'platform_fit': output_platform}]
            }
            try:
                result = asyncio.run(rewriter.rewrite_analyzed_post(analyzed, 'qronoya', output_platform))
                if 'error' not in result:
                    st.session_state.current_rewrite = {
                        'content': result.get('rewritten_content', ''),
                        'platform': output_platform,
                        'language': language,
                        'source_post': {'title': current_post.get('title', ''), 'url': current_post.get('url', ''), 'platform': source_platform}
                    }
                    st.rerun()
                else:
                    # Check if it was skipped (truncated/incomplete content)
                    if result.get('skipped'):
                        st.warning(f"⚠️ Skipped: {result['error']}")
                        st.info("This post has incomplete content and was automatically skipped. Click **Skip** to move to the next post.")
                        # Auto-skip this post
                        if st.button("Skip to Next Post", key="auto_skip"):
                            st.session_state.review_queue.pop(0)
                            st.session_state.stats['skipped'] += 1
                            st.session_state.current_rewrite = None
                            st.rerun()
                        return
                    else:
                        st.error(f"Error: {result['error']}")
                        return
            except Exception as e:
                st.error(f"Error: {e}")
                return

    # Show rewrite
    if st.session_state.current_rewrite:
        st.subheader("✨ Rewritten Content")
        edited_content = st.text_area("Edit if needed:", st.session_state.current_rewrite['content'], height=200)

        # Actions
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Approve & Schedule", type="primary", use_container_width=True):
                # Save scheduled post
                scheduler = PublishingScheduler()
                decision = scheduler.schedule_rewritten_post({'rewritten_content': edited_content, 'viral_potential': 50, 'time_sensitivity': 'evergreen', 'platform': st.session_state.current_rewrite['platform']}, platform_override=st.session_state.current_rewrite['platform'])

                scheduled_dir = Path("scheduled_posts")
                scheduled_dir.mkdir(exist_ok=True)
                filepath = scheduled_dir / f"{st.session_state.current_rewrite['platform']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump({'id': filepath.stem, 'rewritten_content': edited_content, 'platform': st.session_state.current_rewrite['platform'], 'language': st.session_state.current_rewrite['language'], 'scheduled_for': decision.when.isoformat(), 'priority': decision.priority, 'status': 'approved'}, f, ensure_ascii=False, indent=2)

                st.session_state.review_stats['approved'] += 1
                st.success(f"✅ Scheduled for {decision.when.strftime('%Y-%m-%d %H:%M')}")
                st.session_state.review_index += 1
                st.session_state.current_rewrite = None
                st.rerun()

        with col2:
            if st.button("❌ Reject", use_container_width=True):
                st.session_state.review_stats['rejected'] += 1
                st.session_state.review_index += 1
                st.session_state.current_rewrite = None
                st.rerun()

        with col3:
            if st.button("⏭️ Skip", use_container_width=True):
                st.session_state.review_stats['skipped'] += 1
                st.session_state.review_index += 1
                st.session_state.current_rewrite = None
                st.rerun()


