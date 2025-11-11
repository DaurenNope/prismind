"""
Production Publishing Pipeline Tab

One-click interface to schedule and publish content for all profiles.
Shows today's queue, schedules posts, and publishes to platforms.
"""

import streamlit as st
import asyncio
import os
from datetime import datetime, timedelta
from typing import List, Dict
from supabase import create_client

# Import the rewriter
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from src.publishing.rewriter import ContentRewriter


# Profile configurations
PROFILES = {
    'qronoya': {
        'platforms': ['threads', 'telegram'],
        'daily_posts': 2,
        'language': 'ru',
        'display_name': 'Qronoya'
    },
    'aspandead': {
        'platforms': ['threads'],
        'daily_posts': 1,
        'language': 'ru',
        'display_name': 'Aspandead'
    }
}


def render_production_pipeline_tab():
    """Render the production publishing pipeline interface"""

    st.header("🚀 Production Pipeline")
    st.markdown("Schedule and publish content for all profiles with one click.")

    # Show current status
    show_pipeline_status()

    st.divider()

    # Profile selector
    selected_profile = st.selectbox(
        "Select Profile",
        options=list(PROFILES.keys()),
        format_func=lambda x: PROFILES[x]['display_name']
    )

    profile_config = PROFILES[selected_profile]

    # Show profile info
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Daily Posts", profile_config['daily_posts'])
    with col2:
        st.metric("Platforms", len(profile_config['platforms']))
    with col3:
        st.metric("Language", profile_config['language'].upper())

    st.markdown(f"**Platforms**: {', '.join(profile_config['platforms'])}")

    st.divider()

    # Show today's content queue
    st.subheader(f"📋 Today's Content for {profile_config['display_name']}")

    with st.spinner("Loading content queue..."):
        posts = asyncio.run(get_content_for_profile(selected_profile, profile_config['daily_posts'] * 2))

    if not posts:
        st.warning(f"No usable posts found for {selected_profile}")
        return

    # Show time-sensitive posts
    time_sensitive = [p for p in posts if p.get('time_sensitive')]
    evergreen = [p for p in posts if not p.get('time_sensitive')]

    if time_sensitive:
        st.markdown("### ⏰ Time-Sensitive (Post First!)")
        for i, post in enumerate(time_sensitive, 1):
            with st.expander(f"{i}. {post.get('topic', 'N/A')} - Quality: {post.get('quality_score', 0)}/10"):
                st.markdown(f"**Platform**: {post.get('platform', 'N/A')}")
                st.markdown(f"**Urgency**: {post.get('urgency_score', 0)}/10")
                st.markdown(f"**Window**: {post.get('relevance_window', 'N/A')}")
                st.markdown(f"**URL**: {post.get('url', 'N/A')}")

                st.markdown("**Summary**:")
                st.write(post.get('ai_summary', 'No summary')[:300] + '...')

                st.markdown("**Original Content**:")
                content = post.get('content', '')
                if len(content) > 500:
                    st.text_area("Content", content[:500] + '...', height=150, key=f"time_{i}")
                else:
                    st.text_area("Content", content, height=150, key=f"time_{i}")

    if evergreen:
        st.markdown("### 📚 High-Quality Evergreen")
        for i, post in enumerate(evergreen[:3], 1):
            with st.expander(f"{i}. {post.get('topic', 'N/A')} - Quality: {post.get('quality_score', 0)}/10"):
                st.markdown(f"**Platform**: {post.get('platform', 'N/A')}")
                st.markdown(f"**URL**: {post.get('url', 'N/A')}")
                st.markdown(f"**Summary**: {post.get('ai_summary', 'No summary')[:200]}...")

    st.divider()

    # Show rewrite preview if available
    if f'rewrites_{selected_profile}' in st.session_state:
        st.subheader("✍️ Rewrite Preview")

        rewrites = st.session_state[f'rewrites_{selected_profile}']

        st.success(f"Generated {len(rewrites)} rewrites - Review and schedule them!")

        for i, rewrite in enumerate(rewrites, 1):
            with st.expander(f"{i}. {rewrite['topic']} - {rewrite['platform'].upper()} - {rewrite['scheduled_time'].strftime('%H:%M')}"):
                st.markdown(f"**Original Topic**: {rewrite['topic']}")
                st.markdown(f"**Platform**: {rewrite['platform']}")
                st.markdown(f"**Scheduled Time**: {rewrite['scheduled_time'].strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown(f"**Quality Score**: {rewrite.get('quality', 'N/A')}/10")

                st.markdown("**Rewritten Content (Russian)**:")
                st.text_area("Rewrite", rewrite['content'], height=200, key=f"preview_{i}")

                st.caption(f"Character count: {len(rewrite['content'])}")

        # Schedule all button
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Schedule All These Posts", type="primary", use_container_width=True):
                with st.spinner("Scheduling posts..."):
                    result = asyncio.run(schedule_rewrites(selected_profile, rewrites))
                    if result['success']:
                        st.success(f"✅ Scheduled {result['count']} posts!")
                        del st.session_state[f'rewrites_{selected_profile}']
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Error: {result['error']}")

        with col2:
            if st.button("🗑️ Discard Rewrites"):
                del st.session_state[f'rewrites_{selected_profile}']
                st.rerun()

        st.divider()

    # Show scheduled rewrites
    st.subheader("📅 Scheduled Posts")

    scheduled_posts = asyncio.run(get_scheduled_posts(selected_profile))

    if scheduled_posts:
        st.success(f"Found {len(scheduled_posts)} scheduled posts for {profile_config['display_name']}")

        for i, post in enumerate(scheduled_posts, 1):
            scheduled_time = datetime.fromisoformat(post['scheduled_time'].replace('Z', '+00:00'))

            with st.expander(f"{i}. {post['platform'].upper()} - {scheduled_time.strftime('%H:%M on %b %d')} - Status: {post['status']}"):
                st.markdown(f"**Scheduled Time**: {scheduled_time.strftime('%Y-%m-%d %H:%M:%S')}")
                st.markdown(f"**Platform**: {post['platform']}")
                st.markdown(f"**Status**: {post['status']}")

                st.markdown("**Rewritten Content**:")
                st.text_area("Content", post['content'], height=200, key=f"sched_{i}", disabled=True)

                st.caption(f"Character count: {len(post['content'])}")

                # Action buttons for this post
                col1, col2 = st.columns(2)
                with col1:
                    if post['status'] == 'pending' and st.button(f"📤 Publish Now", key=f"pub_{i}"):
                        result = asyncio.run(publish_single_post(post['id']))
                        if result:
                            st.success("Published!")
                            st.rerun()

                with col2:
                    if st.button(f"🗑️ Delete", key=f"del_{i}"):
                        result = asyncio.run(delete_scheduled_post(post['id']))
                        if result:
                            st.success("Deleted!")
                            st.rerun()
    else:
        st.info(f"No scheduled posts for {profile_config['display_name']}. Click 'Schedule Posts Now' below to create some!")

    st.divider()

    # Action buttons
    st.subheader("🎯 Actions")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✍️ Generate Rewrites", type="primary", use_container_width=True):
            st.info("⚠️ Using local Vikhr model (Russian-specialized, cloud APIs rate limited). Takes ~30-40 seconds per rewrite.")
            with st.spinner(f"🐌 Rewriting {profile_config['daily_posts']} posts with Vikhr (Russian model)... Slow but better quality!"):
                result = asyncio.run(generate_rewrites_preview(selected_profile, profile_config['daily_posts']))
                if result['success']:
                    st.success(f"✅ Generated {len(result['rewrites'])} rewrites!")
                    st.session_state[f'rewrites_{selected_profile}'] = result['rewrites']
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result['error']}")

    with col2:
        if st.button("📤 Publish Due Posts", use_container_width=True):
            with st.spinner("Publishing posts that are due..."):
                result = asyncio.run(publish_due_posts())
                if result['success']:
                    st.success(f"✅ Published {result['count']} posts!")
                else:
                    st.info(result['message'])

    # Schedule all profiles button
    st.divider()

    if st.button("🚀 Schedule All Profiles", type="secondary", use_container_width=True):
        with st.spinner("Scheduling posts for all profiles..."):
            results = []
            for profile_key in PROFILES.keys():
                result = asyncio.run(schedule_posts_for_profile(profile_key))
                results.append((PROFILES[profile_key]['display_name'], result))

            for name, result in results:
                if result['success']:
                    st.success(f"✅ {name}: Scheduled {result['count']} posts")
                else:
                    st.error(f"❌ {name}: {result['error']}")


def show_pipeline_status():
    """Show current pipeline status"""

    try:
        client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

        # Get scheduled post counts
        pending = client.table('scheduled_posts').select('*', count='exact').eq('status', 'pending').execute()
        posted = client.table('scheduled_posts').select('*', count='exact').eq('status', 'posted').execute()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("⏳ Pending", pending.count or 0)
        with col2:
            st.metric("✅ Posted", posted.count or 0)
        with col3:
            st.metric("📊 Total", (pending.count or 0) + (posted.count or 0))

    except Exception as e:
        st.error(f"Error loading status: {e}")


async def get_content_for_profile(profile_key: str, count: int = 10) -> List[Dict]:
    """Get best content from usable_posts for a profile"""

    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

    # Get time-sensitive posts first
    time_sensitive = client.table('usable_posts')\
        .select('*')\
        .eq('best_persona_key', profile_key)\
        .eq('time_sensitive', True)\
        .in_('relevance_window', ['same-day', '24-72h'])\
        .order('urgency_score', desc=True)\
        .limit(5)\
        .execute()

    # Get high-quality evergreen posts
    evergreen = client.table('usable_posts')\
        .select('*')\
        .eq('best_persona_key', profile_key)\
        .in_('relevance_window', ['this-week', 'evergreen'])\
        .gte('quality_score', 7.0)\
        .order('quality_score', desc=True)\
        .limit(count)\
        .execute()

    # Combine: time-sensitive first
    all_posts = []
    if time_sensitive.data:
        all_posts.extend(time_sensitive.data)

    if evergreen.data:
        existing_ids = {p['id'] for p in all_posts}
        all_posts.extend([p for p in evergreen.data if p['id'] not in existing_ids])

    return all_posts[:count]


async def rewrite_for_profile(post: Dict, profile_key: str) -> str:
    """Rewrite a post for the profile's voice"""

    rewriter = ContentRewriter()

    # 🔥 FORCE OLLAMA FALLBACK to bypass rate limits
    # Use Vikhr (Russian-specialized) for Stage 2, Qwen for Stage 1
    # Temporarily clear cloud API keys to force local Ollama usage
    original_gemini_keys = rewriter.gemini_api_keys
    original_mistral_keys = rewriter.mistral_api_keys
    rewriter.gemini_api_keys = []  # Force skip Gemini (rate limited)
    rewriter.mistral_api_keys = []  # Force skip Mistral (rate limited)

    # Use Vikhr for Russian content (better quality than Qwen for Russian)
    # Vikhr is a Russian-language model fine-tuned for instruction following
    import os
    os.environ['OLLAMA_RUSSIAN_MODEL'] = 'hf.co/Vikhrmodels/QVikhr-3-4B-Instruction-GGUF:latest'

    config = PROFILES.get(profile_key, {})
    platform = config['platforms'][0]

    try:
        analyzed_content = {
            'post_id': post.get('id'),
            'content': post.get('content', ''),
            'summary': post.get('ai_summary', post.get('content', '')),
            'category': post.get('category', ''),
            'topics': post.get('tags', []),
            'key_concepts': post.get('key_concepts', []),
            'rewrite_angles': [{
                'persona': profile_key,
                'angle': 'direct',
                'why': 'Authentic voice',
                'platform_fit': platform
            }]
        }

        result = await rewriter.rewrite_analyzed_post(
            analyzed_content=analyzed_content,
            persona=profile_key,
            platform=platform
        )

        # Restore original keys
        rewriter.gemini_api_keys = original_gemini_keys
        rewriter.mistral_api_keys = original_mistral_keys

        if result.get('error'):
            return ""

        return result.get('rewritten_content', '')

    except Exception as e:
        # Restore keys even on error
        rewriter.gemini_api_keys = original_gemini_keys
        rewriter.mistral_api_keys = original_mistral_keys
        st.error(f"Rewrite error: {e}")
        return ""


async def schedule_posts_for_profile(profile_key: str) -> Dict:
    """Schedule posts for a profile"""

    try:
        config = PROFILES[profile_key]
        daily_posts = config['daily_posts']
        platforms = config['platforms']

        # Get content
        posts = await get_content_for_profile(profile_key, daily_posts * 2)

        if not posts:
            return {'success': False, 'error': 'No usable posts found', 'count': 0}

        # Separate time-sensitive and evergreen
        time_sensitive_posts = [p for p in posts if p.get('time_sensitive')]
        evergreen_posts = [p for p in posts if not p.get('time_sensitive')]

        # Generate posting times
        now = datetime.now()
        posting_times = []

        # Time-sensitive: ASAP
        for i in range(min(len(time_sensitive_posts), daily_posts)):
            post_time = now + timedelta(minutes=30 + (i * 120))
            posting_times.append(('time_sensitive', post_time))

        # Evergreen: spread throughout day
        remaining_slots = daily_posts - len(posting_times)
        for i in range(min(len(evergreen_posts), remaining_slots)):
            hour_offsets = [10, 14, 18, 20]
            target_hour = hour_offsets[i % len(hour_offsets)]

            post_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            if post_time < now:
                post_time += timedelta(days=1)

            posting_times.append(('evergreen', post_time))

        # Rewrite and schedule
        scheduled_count = 0

        for i, (content_type, post_time) in enumerate(posting_times):
            if content_type == 'time_sensitive' and time_sensitive_posts:
                post = time_sensitive_posts.pop(0)
            elif evergreen_posts:
                post = evergreen_posts.pop(0)
            else:
                continue

            # Rewrite
            rewritten = await rewrite_for_profile(post, profile_key)

            if not rewritten:
                continue

            # Schedule for each platform
            for platform in platforms:
                success = await schedule_post(profile_key, rewritten, platform, post_time, post.get('id'))
                if success:
                    scheduled_count += 1

        return {'success': True, 'count': scheduled_count, 'error': None}

    except Exception as e:
        return {'success': False, 'error': str(e), 'count': 0}


async def schedule_post(profile_key: str, content: str, platform: str, post_time: datetime, source_post_id: str = None) -> bool:
    """Schedule a post to the database"""

    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

    try:
        result = client.table('scheduled_posts').insert({
            'persona_key': profile_key,
            'platform': platform,
            'content': content,
            'content_type': 'single_post',
            'scheduled_time': post_time.isoformat(),
            'scheduled_at': post_time.isoformat(),
            'status': 'pending',
            'priority': 5,
            'retry_count': 0,
            'max_retries': 3,
            'metadata': {'source_post_id': source_post_id} if source_post_id else {}
        }).execute()

        return True

    except Exception as e:
        st.error(f"Schedule error: {e}")
        return False


async def publish_due_posts() -> Dict:
    """Publish posts that are due"""

    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

    now = datetime.now()

    # Get posts due for publishing
    result = client.table('scheduled_posts')\
        .select('*')\
        .eq('status', 'pending')\
        .lte('scheduled_time', now.isoformat())\
        .execute()

    if not result.data:
        return {'success': True, 'count': 0, 'message': 'No posts due for publishing'}

    published_count = 0

    for post in result.data:
        try:
            # TODO: Implement actual publishing to Threads/Telegram
            # For now, just mark as posted

            client.table('scheduled_posts')\
                .update({'status': 'posted', 'updated_at': now.isoformat()})\
                .eq('id', post['id'])\
                .execute()

            published_count += 1

        except Exception as e:
            client.table('scheduled_posts')\
                .update({
                    'status': 'failed',
                    'error_message': str(e),
                    'updated_at': now.isoformat()
                })\
                .eq('id', post['id'])\
                .execute()

    return {'success': True, 'count': published_count, 'message': f'Published {published_count} posts'}


async def get_scheduled_posts(profile_key: str) -> List[Dict]:
    """Get scheduled posts for a profile"""

    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

    try:
        result = client.table('scheduled_posts')\
            .select('*')\
            .eq('persona_key', profile_key)\
            .order('scheduled_time', desc=False)\
            .limit(20)\
            .execute()

        return result.data or []

    except Exception as e:
        st.error(f"Error loading scheduled posts: {e}")
        return []


async def publish_single_post(post_id: str) -> bool:
    """Publish a single post immediately"""

    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

    try:
        now = datetime.now()

        # TODO: Implement actual publishing to Threads/Telegram

        # Mark as published
        client.table('scheduled_posts')\
            .update({'status': 'posted', 'updated_at': now.isoformat()})\
            .eq('id', post_id)\
            .execute()

        return True

    except Exception as e:
        st.error(f"Error publishing post: {e}")
        return False


async def delete_scheduled_post(post_id: str) -> bool:
    """Delete a scheduled post"""

    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

    try:
        client.table('scheduled_posts')\
            .delete()\
            .eq('id', post_id)\
            .execute()

        return True

    except Exception as e:
        st.error(f"Error deleting post: {e}")
        return False


async def generate_rewrites_preview(profile_key: str, daily_posts: int) -> Dict:
    """Generate rewrites and return them for preview (don't schedule yet)"""

    try:
        config = PROFILES[profile_key]
        platforms = config['platforms']

        # Get content
        posts = await get_content_for_profile(profile_key, daily_posts * 2)

        if not posts:
            return {'success': False, 'error': 'No usable posts found', 'rewrites': []}

        # Separate time-sensitive and evergreen
        time_sensitive_posts = [p for p in posts if p.get('time_sensitive')]
        evergreen_posts = [p for p in posts if not p.get('time_sensitive')]

        # Generate posting times
        now = datetime.now()
        posting_times = []

        # Time-sensitive: ASAP
        for i in range(min(len(time_sensitive_posts), daily_posts)):
            post_time = now + timedelta(minutes=30 + (i * 120))
            posting_times.append(('time_sensitive', post_time))

        # Evergreen: spread throughout day
        remaining_slots = daily_posts - len(posting_times)
        for i in range(min(len(evergreen_posts), remaining_slots)):
            hour_offsets = [10, 14, 18, 20]
            target_hour = hour_offsets[i % len(hour_offsets)]

            post_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
            if post_time < now:
                post_time += timedelta(days=1)

            posting_times.append(('evergreen', post_time))

        # Rewrite
        rewrites = []

        for i, (content_type, post_time) in enumerate(posting_times):
            if content_type == 'time_sensitive' and time_sensitive_posts:
                post = time_sensitive_posts.pop(0)
            elif evergreen_posts:
                post = evergreen_posts.pop(0)
            else:
                continue

            # Rewrite
            rewritten = await rewrite_for_profile(post, profile_key)

            if not rewritten:
                continue

            # Add to rewrites list for each platform
            for platform in platforms:
                rewrites.append({
                    'source_post_id': post.get('id'),
                    'topic': post.get('topic', 'N/A'),
                    'quality': post.get('quality_score', 0),
                    'platform': platform,
                    'content': rewritten,
                    'scheduled_time': post_time
                })

        return {'success': True, 'rewrites': rewrites, 'error': None}

    except Exception as e:
        return {'success': False, 'error': str(e), 'rewrites': []}


async def schedule_rewrites(profile_key: str, rewrites: List[Dict]) -> Dict:
    """Schedule the pre-generated rewrites"""

    try:
        scheduled_count = 0

        for rewrite in rewrites:
            success = await schedule_post(
                profile_key,
                rewrite['content'],
                rewrite['platform'],
                rewrite['scheduled_time'],
                rewrite.get('source_post_id')
            )

            if success:
                scheduled_count += 1

        return {'success': True, 'count': scheduled_count, 'error': None}

    except Exception as e:
        return {'success': False, 'error': str(e), 'count': 0}
