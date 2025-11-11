"""
Rewriter Lab Tab - Intelligent drafting assistant with multiple versions and suggestions
"""
import streamlit as st
import asyncio
from datetime import datetime
from src.publishing.rewriter import ContentRewriter
from supabase import create_client
import os
import json
import requests

async def generate_writing_suggestions(source_content, rewrites, persona, platform):
    """Generate intelligent writing suggestions using Gemini"""
    try:
        # Get first available Gemini key
        gemini_keys = [
            os.getenv('GEMINI_API_KEY'),
            os.getenv('GEMINI_API_KEY_1'),
            os.getenv('GEMINI_API_KEY_2'),
            os.getenv('GEMINI_API_KEY_3'),
        ]
        api_key = next((k for k in gemini_keys if k), None)
        if not api_key:
            return {"error": "No Gemini API key available"}

        prompt = f"""Analyze these rewrites and provide intelligent writing suggestions.

ORIGINAL:
{source_content}

REWRITES:
Version A (Direct): {rewrites['direct']}
Version B (Engaging): {rewrites['engaging']}
Version C (Personal): {rewrites['personal']}

PERSONA: {persona}
PLATFORM: {platform}

Provide suggestions in Russian as a JSON object with these fields:
- "what_works": Array of 2-3 strengths (what makes these rewrites effective)
- "to_make_banger": Array of 2-3 concrete suggestions to make it viral/engaging
- "platform_tips": Array of 1-2 platform-specific optimization tips
- "best_version": Which version (A/B/C) works best and why

Write in Russian, be specific and actionable."""

        # Call Gemini API
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1000,
            }
        }

        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        text = result['candidates'][0]['content']['parts'][0]['text'].strip()

        # Parse JSON from response
        if text.startswith('```json'):
            text = text[7:]
        if text.endswith('```'):
            text = text[:-3]

        return json.loads(text.strip())

    except Exception as e:
        return {"error": str(e)}


def render_rewriter_lab_tab():
    """
    Rewriter Lab - Intelligent drafting assistant with multiple versions and suggestions
    """
    st.header("🔬 Rewriter Lab")
    st.markdown("**Creative drafting workshop with multiple versions and AI suggestions**")

    # Initialize
    rewriter = ContentRewriter()

    if 'lab_results' not in st.session_state:
        st.session_state.lab_results = None
    if 'lab_suggestions' not in st.session_state:
        st.session_state.lab_suggestions = None

    # ===  SOURCE POST SELECTION ===
    st.subheader("1️⃣ Select Source Post")

    col1, col2 = st.columns([2, 1])

    with col1:
        source_type = st.radio(
            "Source",
            ["Recent Posts from Supabase", "Custom Text"],
            horizontal=True,
            key="lab_source_type"
        )

    with col2:
        platform_filter = st.selectbox(
            "Platform Filter",
            ["All Platforms", "reddit", "twitter", "threads", "telegram"],
            key="lab_platform_filter"
        )

    source_post = None
    source_content = ""

    if source_type == "Recent Posts from Supabase":
        try:
            supabase = create_client(
                os.getenv('SUPABASE_URL'),
                os.getenv('SUPABASE_KEY')
            )

            query = supabase.table('posts')\
                .select('post_id, platform, title, content, created_at')\
                .not_.is_('content', 'null')

            if platform_filter != "All Platforms":
                query = query.eq('platform', platform_filter)

            response = query.order('created_at', desc=True)\
                .limit(50)\
                .execute()

            posts = response.data

            post_options = [
                f"[{p['platform'].upper()}] {p['title'][:60]}... ({p['post_id'][:8]})"
                for p in posts
            ]

            selected_idx = st.selectbox(
                "Select post",
                range(len(post_options)),
                format_func=lambda i: post_options[i],
                key="lab_post_select"
            )

            source_post = posts[selected_idx]
            source_content = source_post['content']

            st.text_area(
                "Source content preview",
                source_content[:500] + ("..." if len(source_content) > 500 else ""),
                height=100,
                disabled=True,
                key="lab_source_preview"
            )

        except Exception as e:
            st.error(f"Error loading posts: {e}")

    else:  # Custom text
        source_content = st.text_area(
            "Enter content to rewrite",
            placeholder="Paste any text here...",
            height=150,
            key="lab_custom_content"
        )

    if not source_content:
        st.info("👆 Select or enter source content to begin")
        return

    # === PERSONA & PLATFORM SETTINGS ===
    st.subheader("2️⃣ Persona & Platform")

    col1, col2 = st.columns(2)

    with col1:
        persona = st.selectbox(
            "Persona",
            ["qronoya", "aspandead", "claimzilla"],
            key="lab_persona"
        )

    with col2:
        platform = st.selectbox(
            "Target Platform",
            ["twitter", "threads", "telegram"],
            key="lab_platform"
        )

    # === VOICE EXAMPLES VIEWER ===
    with st.expander(f"👁️ View Voice Examples ({len(rewriter.voice_examples.get(persona, []))} loaded)", expanded=False):
        examples = rewriter.voice_examples.get(persona, [])
        if examples:
            st.markdown(f"**Showing all {len(examples)} voice examples for {persona}:**")
            for i, ex in enumerate(examples, 1):
                with st.container():
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        content = ex if isinstance(ex, str) else ex.get('content', str(ex))
                        st.text_area(
                            f"Example {i}",
                            content,
                            height=100,
                            key=f"example_{persona}_{i}",
                            disabled=True
                        )
                    with col2:
                        if isinstance(ex, dict):
                            st.caption(f"Type: {ex.get('content_type', 'N/A')}")
                            st.caption(f"Tone: {ex.get('tone', 'N/A')}")
                    if i < len(examples):
                        st.divider()
        else:
            st.warning(f"No voice examples loaded for {persona}")

    # === GENERATE BUTTON ===
    st.markdown("---")

    if st.button("🚀 **Generate Multiple Versions**", type="primary", key="lab_generate"):
        with st.spinner("Generating 3 versions + suggestions..."):
            # Prepare base analyzed_content
            base_content = {
                'post_id': source_post.get('post_id', 'lab_custom') if source_post else 'lab_custom',
                'platform': source_post.get('platform', 'custom') if source_post else 'custom',
                'content': source_content,
                'title': source_post.get('title', '') if source_post else '',
                'summary': source_content[:200],
                'category': 'general',
                'topics': ['general'],
                'key_concepts': [],
            }

            # Generate 3 versions with different angles
            versions = []
            angles = [
                ('short', 'Short & Punchy - line breaks after every sentence, 3-4 sentences max'),
                ('expanded', 'Expanded with Context - add data, examples, comparisons, 5-7 sentences'),
                ('story', 'Provocative/Story - personal admission, ends with question')
            ]

            for angle_key, angle_desc in angles:
                analyzed_content = {
                    **base_content,
                    'rewrite_angles': [{
                        'persona': persona,
                        'angle': angle_desc,
                        'tone': 'analytical',
                        'platform_fit': 'single_post'
                    }]
                }

                result = asyncio.run(
                    rewriter.rewrite_analyzed_post(
                        analyzed_content=analyzed_content,
                        persona=persona,
                        platform=platform
                    )
                )

                versions.append({
                    'key': angle_key,
                    'label': angle_desc,
                    'result': result
                })

            st.session_state.lab_results = versions

            # Generate suggestions
            if all('error' not in v['result'] for v in versions):
                rewrites_dict = {
                    v['key']: v['result'].get('rewritten_content', '')
                    for v in versions
                }
                suggestions = asyncio.run(
                    generate_writing_suggestions(
                        source_content,
                        rewrites_dict,
                        persona,
                        platform
                    )
                )
                st.session_state.lab_suggestions = suggestions

    # === RESULTS ===
    if st.session_state.lab_results:
        st.markdown("---")
        st.subheader("✨ Generated Versions")

        # Create tabs for each version
        versions = st.session_state.lab_results
        tab_labels = [
            f"Version A: Short & Punchy",
            f"Version B: Expanded with Context",
            f"Version C: Provocative/Story"
        ]
        tabs = st.tabs(tab_labels)

        for i, (tab, version) in enumerate(zip(tabs, versions)):
            with tab:
                result = version['result']

                if 'error' in result:
                    st.error(f"❌ Error: {result['error']}")
                else:
                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Quality", f"{result.get('quality_score', 0)}/100")
                    with col2:
                        st.metric("Length", f"{result.get('content_length', 0)} chars")
                    with col3:
                        st.metric("Model", result.get('model_used', 'unknown'))

                    # Rewritten content
                    rewritten = result.get('rewritten_content', '')
                    st.markdown("**Generated Content:**")
                    st.info(rewritten)

                    # Editable version
                    edited_content = st.text_area(
                        "Edit this version",
                        value=rewritten,
                        height=120,
                        key=f"edit_{version['key']}"
                    )

                    # Actions
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("📋 Copy", key=f"copy_{version['key']}"):
                            st.code(edited_content)
                            st.success("✅ Ready to copy!")
                    with col2:
                        if st.button("💾 Save", key=f"save_{version['key']}"):
                            from pathlib import Path
                            curation_dir = Path("data/curated_posts")
                            curation_dir.mkdir(parents=True, exist_ok=True)
                            curation_file = curation_dir / f"{persona}_curated.jsonl"

                            curated_entry = {
                                "created_at": datetime.now().isoformat(),
                                "persona": persona,
                                "platform": platform,
                                "content": edited_content,
                                "quality_score": result.get('quality_score', 100),
                                "version": version['key'],
                                "source": "rewriter_lab"
                            }

                            with open(curation_file, 'a', encoding='utf-8') as f:
                                f.write(json.dumps(curated_entry, ensure_ascii=False) + '\n')

                            st.success(f"✅ Saved!")

                    # Quick Feedback
                    st.markdown("**Quick Feedback:**")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("👍 Approve", key=f"approve_{version['key']}", use_container_width=True):
                            try:
                                from src.publishing.feedback_tracker import FeedbackTracker
                                import hashlib
                                tracker = FeedbackTracker()
                                rewrite_id = hashlib.md5(rewritten.encode()).hexdigest()
                                asyncio.run(tracker.store_feedback(
                                    rewrite_id=rewrite_id,
                                    rating=1,
                                    feedback_type="thumbs",
                                    metadata={
                                        "persona": persona,
                                        "platform": platform,
                                        "version": version['key'],
                                        "length": len(rewritten),
                                        "quality_score": result.get('quality_score', 0)
                                    }
                                ))
                                st.success("✅ Feedback recorded!")
                            except Exception as e:
                                st.error(f"Failed to save feedback: {e}")
                    with col2:
                        if st.button("👎 Reject", key=f"reject_{version['key']}", use_container_width=True):
                            try:
                                from src.publishing.feedback_tracker import FeedbackTracker
                                import hashlib
                                tracker = FeedbackTracker()
                                rewrite_id = hashlib.md5(rewritten.encode()).hexdigest()
                                asyncio.run(tracker.store_feedback(
                                    rewrite_id=rewrite_id,
                                    rating=-1,
                                    feedback_type="thumbs",
                                    metadata={
                                        "persona": persona,
                                        "platform": platform,
                                        "version": version['key'],
                                        "length": len(rewritten),
                                        "quality_score": result.get('quality_score', 0)
                                    }
                                ))
                                st.success("✅ Feedback recorded!")
                            except Exception as e:
                                st.error(f"Failed to save feedback: {e}")
                    with col3:
                        rating_stars = st.selectbox(
                            "⭐ Rate",
                            options=[None, 1, 2, 3, 4, 5],
                            format_func=lambda x: "Rate..." if x is None else f"{'⭐' * x}",
                            key=f"stars_{version['key']}"
                        )
                        if rating_stars:
                            try:
                                from src.publishing.feedback_tracker import FeedbackTracker
                                import hashlib
                                tracker = FeedbackTracker()
                                rewrite_id = hashlib.md5(rewritten.encode()).hexdigest()
                                asyncio.run(tracker.store_feedback(
                                    rewrite_id=rewrite_id,
                                    rating=rating_stars,
                                    feedback_type="rating",
                                    metadata={
                                        "persona": persona,
                                        "platform": platform,
                                        "version": version['key'],
                                        "length": len(rewritten),
                                        "quality_score": result.get('quality_score', 0)
                                    }
                                ))
                                st.success(f"✅ Rated {rating_stars}⭐!")
                            except Exception as e:
                                st.error(f"Failed to save rating: {e}")

        # === WRITING SUGGESTIONS ===
        if st.session_state.lab_suggestions:
            st.markdown("---")
            st.subheader("💡 Writing Suggestions")

            suggestions = st.session_state.lab_suggestions

            if 'error' not in suggestions:
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("### ✅ What Works")
                    for item in suggestions.get('what_works', []):
                        st.markdown(f"- {item}")

                    st.markdown("### 🎯 Platform Tips")
                    for item in suggestions.get('platform_tips', []):
                        st.markdown(f"- {item}")

                with col2:
                    st.markdown("### 🚀 To Make It a Banger")
                    for item in suggestions.get('to_make_banger', []):
                        st.markdown(f"- {item}")

                    st.markdown("### 🏆 Best Version")
                    st.info(suggestions.get('best_version', 'No recommendation'))
            else:
                st.warning(f"Could not generate suggestions: {suggestions.get('error', 'Unknown error')}")

        # === COMPARISON VIEW ===
        with st.expander("🔍 Compare Original vs Rewrites"):
            st.markdown("**Original:**")
            st.text_area("", source_content, height=150, disabled=True, key="compare_orig")

            st.markdown("**All Versions:**")
            for version in versions:
                if 'error' not in version['result']:
                    st.markdown(f"**{version['label']}:**")
                    st.text_area("", version['result'].get('rewritten_content', ''),
                               height=100, disabled=True, key=f"compare_{version['key']}")

        # Regenerate button
        st.markdown("---")
        if st.button("🔄 Regenerate All", key="lab_regenerate"):
            st.session_state.lab_results = None
            st.session_state.lab_suggestions = None
            st.rerun()
