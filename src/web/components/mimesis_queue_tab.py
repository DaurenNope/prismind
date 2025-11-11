from datetime import datetime, timedelta, timezone

import streamlit as st

from src.database.publishing.bridge import MimesisDB
from src.publishing.services.transformer import PersonaGenerator
from src.publishing.services.personalities import get_persona_keys, load_personalities
from src.web.components.tabs import get_database_manager  # reuse existing cache


def render():
    st.title("📝 Quick Post")
    st.markdown("Create and schedule a social media post")
    
    # === STEP 1: Check what platforms have credentials ===
    import os
    from pathlib import Path
    
    platform_accounts = {}
    
    # Twitter credentials
    twitter_username = os.getenv("TWITTER_USERNAME", "")
    twitter_api_key = os.getenv("TWITTER_API_KEY", "")
    # Prefer TWITTER_COOKIE_FILE; support legacy TWITTER_COOKIES_FILE
    twitter_cookies_file = os.getenv("TWITTER_COOKIE_FILE", "") or os.getenv("TWITTER_COOKIES_FILE", "")
    if not twitter_cookies_file and twitter_username:
        twitter_cookies_file = f"config/twitter_cookies_{twitter_username}.json"
    
    if twitter_username and twitter_api_key:
        platform_accounts["twitter"] = {"account": twitter_username, "status": "✅"}
    elif twitter_username and twitter_cookies_file and Path(twitter_cookies_file).exists():
        platform_accounts["twitter"] = {"account": twitter_username, "status": "✅"}
    elif twitter_api_key:
        platform_accounts["twitter"] = {"account": "API", "status": "✅"}
    else:
        platform_accounts["twitter"] = None
    
    # Threads credentials
    threads_username = os.getenv("THREADS_USERNAME", "")
    threads_cookies_file = os.getenv("THREADS_COOKIES_FILE", "config/threads_cookies.json")
    
    if threads_username and Path(threads_cookies_file).exists():
        platform_accounts["threads"] = {"account": threads_username, "status": "✅"}
    elif Path(threads_cookies_file).exists():
        platform_accounts["threads"] = {"account": "Unknown", "status": "✅"}
    else:
        platform_accounts["threads"] = None
    
    # Telegram credentials
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if telegram_bot_token:
        platform_accounts["telegram"] = {"account": "Bot", "status": "✅"}
    else:
        platform_accounts["telegram"] = None
    
    # Filter to only configured platforms
    configured_platforms = {k: v for k, v in platform_accounts.items() if v is not None}
    
    if not configured_platforms:
        st.error("❌ **No platforms configured!**")
        st.info("""
        You need to set up credentials in your `.env` file:
        - **Twitter**: `TWITTER_USERNAME` + `TWITTER_API_KEY` (or cookies)
        - **Threads**: `THREADS_USERNAME` + cookies file
        - **Telegram**: `TELEGRAM_BOT_TOKEN`
        """)
        return
    
    # === STEP 2: Platform selector ===
    st.subheader("📍 Where to post?")
    platform_options = [f"✅ {k.title()} ({v['account']})" for k, v in configured_platforms.items()]
    platform_labels_map = {f"✅ {k.title()} ({v['account']})": k for k, v in configured_platforms.items()}
    
    selected_platform_label = st.selectbox(
        "Choose platform", 
        platform_options,
        label_visibility="collapsed"
    )
    platform = platform_labels_map[selected_platform_label]
    
    st.markdown("---")
    
    # === STEP 3: Persona selector ===
    st.subheader("🎭 Who's posting?")
    persona_keys = get_persona_keys()
    personalities = load_personalities()
    persona_info = {p.get("key"): p for p in personalities if p.get("key")}
    
    if persona_keys:
        persona_options = [f"{persona_info.get(key, {}).get('name', key)} ({key})" for key in persona_keys]
        selected_persona_option = st.selectbox("Choose persona", persona_options, label_visibility="collapsed")
        persona = selected_persona_option.split(" (")[-1].rstrip(")")
    else:
        persona = st.text_input("Persona key", "skeptical_builder", label_visibility="visible")
    
    st.markdown("---")
    
    # === STEP 4: Content ===
    st.subheader("💬 What to post?")
    content = st.text_area(
        "Write your post", 
        "Hello world from Prismind!", 
        height=150,
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    
    # === STEP 5: Schedule ===
    st.subheader("⏰ When to post?")
    post_now = st.radio(
        "Post immediately or schedule?",
        ["🚀 Post Now", "⏱️ Schedule Later"],
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if post_now == "⏱️ Schedule Later":
        when = st.slider("Minutes from now", 1, 1440, 60)
    else:
        when = 0
    
    st.markdown("---")
    
    # === STEP 6: Post button ===
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("📤 **Post**", type="primary", use_container_width=True):
            try:
                # If posting now (when==0), post directly instead of scheduling
                if when == 0:
                    # Post directly using the posting service with logging
                    import logging
                    import sys
                    import time
                    from io import StringIO
                    from contextlib import redirect_stdout, redirect_stderr
                    
                    # Create log capture
                    log_capture = StringIO()
                    log_handler = logging.StreamHandler(log_capture)
                    log_handler.setLevel(logging.INFO)
                    formatter = logging.Formatter('%(levelname)s - %(message)s')
                    log_handler.setFormatter(formatter)
                    
                    # Get relevant loggers
                    posting_logger = logging.getLogger('src.services.posting_service')
                    threads_logger = logging.getLogger('src.publishing.platforms.threads_playwright')
                    twitter_logger = logging.getLogger('src.publishing.platforms.twitter_playwright')
                    
                    # Add handler to loggers
                    for logger in [posting_logger, threads_logger, twitter_logger]:
                        logger.addHandler(log_handler)
                        logger.setLevel(logging.INFO)
                    
                    # Create UI container for logs
                    log_container = st.container()
                    status_placeholder = st.empty()
                    timer_start = time.time()
                    
                    try:
                        with log_container:
                            st.markdown("### 📋 Posting Logs")
                            log_placeholder = st.empty()
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                        
                        # Post with logs (also capture print statements)
                        from src.services.posting_service import PostingService
                        posting_service = PostingService()
                        
                        # Also capture print statements
                        print_capture = StringIO()
                        old_stdout = sys.stdout
                        sys.stdout = print_capture
                        
                        try:
                            # Start posting
                            status_text.info("🚀 Starting post...")
                            progress_bar.progress(0.1)
                            
                            if platform == "twitter":
                                result = posting_service.post_to_twitter(content)
                            elif platform == "threads":
                                result = posting_service.post_to_threads(content)
                            elif platform == "telegram":
                                result = posting_service.post_to_telegram(content)
                            else:
                                result = {"success": False, "error": f"Unknown platform: {platform}"}
                            
                            elapsed_time = time.time() - timer_start
                            
                            # Restore stdout
                            sys.stdout = old_stdout
                            
                            # Combine logs and prints
                            log_output = log_capture.getvalue()
                            print_output = print_capture.getvalue()
                            combined_logs = f"{print_output}\n{log_output}"
                            
                            # Filter and format logs
                            all_log_lines = combined_logs.split('\n')
                            filtered_logs = []
                            for line in all_log_lines:
                                line_lower = line.lower()
                                if line.strip() and (
                                    any(keyword in line_lower for keyword in [
                                        'info', 'warning', 'error', 'success', 
                                        'post', 'click', 'button', 'authenticat', 
                                        'navigat', 'found', 'typed', 'compose',
                                        'waiting', 'screenshot', 'selected'
                                    ]) or
                                    line.startswith('✅') or 
                                    line.startswith('❌') or 
                                    line.startswith('⚠️') or
                                    line.startswith('🔐') or
                                    line.startswith('🚀') or
                                    line.startswith('🖱️') or
                                    line.startswith('⏳')
                                ):
                                    filtered_logs.append(line.strip())
                            
                            # Show filtered logs
                            if filtered_logs:
                                log_text = '\n'.join(filtered_logs[-30:])  # Show last 30 lines
                                log_placeholder.code(log_text, language=None)
                            
                            # Store full logs for error display
                            full_logs = combined_logs
                            
                        except Exception as e:
                            # Restore stdout on error
                            sys.stdout = old_stdout
                            raise
                        
                        # Remove handlers
                        for logger in [posting_logger, threads_logger, twitter_logger]:
                            logger.removeHandler(log_handler)
                        
                        progress_bar.progress(1.0)
                        status_text.empty()
                        
                        if result.get("success"):
                            post_url = result.get("url") or result.get("post_id")
                            if post_url:
                                st.success(f"🚀 **Posted!** ({elapsed_time:.1f}s) [View post]({post_url})")
                            else:
                                st.success(f"🚀 **Posted!** ({elapsed_time:.1f}s) Check your social media account.")
                            
                            with st.expander("📋 Post Details"):
                                st.json({
                                    "platform": platform,
                                    "persona": persona,
                                    "post_id": result.get("post_id") or result.get("tweet_id") or result.get("message_id"),
                                    "url": result.get("url"),
                                    "status": "Posted",
                                    "duration_seconds": f"{elapsed_time:.2f}",
                                })
                        else:
                            error = result.get("error", "Unknown error")
                            st.error(f"❌ **Posting failed:** ({elapsed_time:.1f}s) {error}")
                            if "screenshot" in error.lower():
                                st.info("💡 Check logs/threads_post_failed.png for debugging")
                            # Show full logs on error
                            if 'full_logs' in locals() and full_logs:
                                with st.expander("📋 Full Logs"):
                                    st.code(full_logs, language=None)
                    
                    except Exception as e:
                        # Remove handlers on error
                        for logger in [posting_logger, threads_logger, twitter_logger]:
                            if log_handler in logger.handlers:
                                logger.removeHandler(log_handler)
                        raise
                else:
                    # Schedule for later
                    db = MimesisDB()
                    dt = datetime.now(timezone.utc) + timedelta(minutes=when)

                    payload = {
                        "personality_key": persona,
                        "persona_key": persona,
                        "platform": platform,
                        "content": content,
                        "content_type": "single_tweet" if platform in ["twitter", "threads"] else "telegram_message",
                        "scheduled_time": dt.isoformat(),
                    }
                    row = db.insert_scheduled(payload)

                    st.success(f"⏱️ **Scheduled!** Will post in {when} minutes.")

                    with st.expander("📋 Post Details"):
                        st.json({
                            "id": row.get('id'),
                            "platform": platform,
                            "persona": persona,
                            "status": "Scheduled",
                        })
                    
            except ConnectionError as e:
                st.error("⚠️ **Connection Error**")
                st.info("Supabase might be temporarily down. Check https://status.supabase.com")
            except Exception as e:
                st.error(f"❌ **Error:** {str(e)}")
                import traceback
                with st.expander("🔍 Debug Info"):
                    st.code(traceback.format_exc())

    # === DRAFT ASSISTANT: Raw Ideas → Polished Post ===
    with st.expander("✍️ Draft Assistant: Write From Ideas"):
        st.markdown("**Got ideas but need help writing? I'll draft it and tailor it to your persona's voice**")

        st.markdown("### 💡 Your Ideas")
        st.caption("Just write your thoughts, bullet points, or rough ideas - don't worry about perfection")

        raw_ideas = st.text_area(
            "Raw ideas",
            placeholder="e.g.,\n- AI coding tools are making devs lazy\n- We're relying too much on autocomplete\n- Nobody reads docs anymore\n- But maybe that's okay?",
            height=150,
            key="draft_ideas",
            label_visibility="collapsed"
        )

        col_draft_persona, col_draft_platform, col_draft_style = st.columns(3)

        with col_draft_persona:
            draft_persona_options = [f"{persona_info.get(key, {}).get('name', key)} ({key})" for key in persona_keys]
            selected_draft_persona = st.selectbox("Persona", draft_persona_options, key="draft_persona")
            draft_persona = selected_draft_persona.split(" (")[-1].rstrip(")")

        with col_draft_platform:
            draft_platform = st.selectbox("Platform", list(configured_platforms.keys()), key="draft_platform")

        with col_draft_style:
            draft_style = st.selectbox(
                "Style",
                ["Natural (persona default)", "Spicy/Provocative", "Thoughtful/Deep", "Funny/Sarcastic"],
                key="draft_style"
            )

        if st.button("✨ **Write Draft**", type="primary", use_container_width=True, key="draft_btn"):
            if not raw_ideas or len(raw_ideas.strip()) < 10:
                st.warning("⚠️ Please write some ideas first (at least a few words)")
            else:
                try:
                    with st.spinner("✍️ Crafting your draft..."):
                        from src.publishing.rewriter import ContentRewriter
                        import asyncio

                        rewriter = ContentRewriter()

                        # Add style instructions to the ideas
                        style_instructions = {
                            "Natural (persona default)": "",
                            "Spicy/Provocative": "\n\n[STYLE]: Make this spicy and provocative - challenge conventional thinking",
                            "Thoughtful/Deep": "\n\n[STYLE]: Make this thoughtful and deep - explore the nuances and implications",
                            "Funny/Sarcastic": "\n\n[STYLE]: Make this funny and sarcastic - use humor to make the point"
                        }

                        styled_ideas = raw_ideas + style_instructions.get(draft_style, "")

                        # Create analyzed_content structure optimized for drafting
                        analyzed_content = {
                            "post_id": f"draft_{datetime.now().timestamp()}",
                            "platform": "draft",
                            "content": styled_ideas,
                            "summary": raw_ideas[:200],
                            "category": "draft",
                            "topics": ["user_draft"],
                            "key_concepts": [],
                            "rewrite_angles": [{
                                "persona": draft_persona,
                                "angle": "Polish and tailor user's raw ideas",
                                "tone": "authentic",
                                "platform_fit": "single_post"
                            }]
                        }

                        # Run async rewrite with special draft mode
                        result = asyncio.run(
                            rewriter.rewrite_analyzed_post(
                                analyzed_content=analyzed_content,
                                persona=draft_persona,
                                platform=draft_platform
                            )
                        )

                        if result and result.get("rewritten_content"):
                            drafted = result["rewritten_content"]

                            # Check if it's an error
                            from src.utils.error_handler import is_rate_limit_error_in_content
                            if is_rate_limit_error_in_content(drafted):
                                st.error("❌ Drafting failed - API rate limit hit. Try again in a moment.")
                            else:
                                st.success("✅ **Draft ready!**")

                                st.markdown("### 📝 Your Drafted Post:")
                                st.info(drafted)

                                # Editable version for tweaks
                                st.markdown("#### ✏️ Make Tweaks:")
                                st.caption("Edit the draft above if you want to adjust anything")
                                final_content = st.text_area(
                                    "Final content",
                                    value=drafted,
                                    height=200,
                                    key="drafted_output",
                                    label_visibility="collapsed"
                                )

                                # Action buttons
                                col_post_draft, col_save_draft, col_regenerate = st.columns(3)

                                with col_post_draft:
                                    if st.button("🚀 **Post Now**", type="primary", use_container_width=True, key="post_draft"):
                                        try:
                                            from src.services.posting_service import PostingService
                                            posting_service = PostingService()

                                            with st.spinner(f"📤 Posting to {draft_platform}..."):
                                                if draft_platform == "twitter":
                                                    post_result = posting_service.post_to_twitter(final_content)
                                                elif draft_platform == "threads":
                                                    post_result = posting_service.post_to_threads(final_content)
                                                elif draft_platform == "telegram":
                                                    post_result = posting_service.post_to_telegram(final_content)

                                                if post_result.get("success"):
                                                    st.success(f"🎉 Posted! [View]({post_result.get('url', '#')})")
                                                else:
                                                    st.error(f"❌ Posting failed: {post_result.get('error')}")

                                        except Exception as e:
                                            st.error(f"❌ Posting error: {str(e)}")

                                with col_save_draft:
                                    if st.button("💾 **Save to Curation**", use_container_width=True, key="save_draft"):
                                        try:
                                            from pathlib import Path
                                            import json

                                            curation_dir = Path("data/curated_posts")
                                            curation_dir.mkdir(parents=True, exist_ok=True)

                                            curation_entry = {
                                                "created_at": datetime.now().isoformat(),
                                                "persona": draft_persona,
                                                "persona_name": persona_info.get(draft_persona, {}).get("name", draft_persona),
                                                "platform": draft_platform,
                                                "original_post_id": f"draft_{datetime.now().timestamp()}",
                                                "original_platform": "draft_assistant",
                                                "content": final_content,
                                                "rewritten_content": final_content,
                                                "content_type": "user_draft",
                                                "quality_score": result.get("quality_score", 100),
                                                "quality_rating": result.get("quality_rating", "excellent"),
                                                "length": len(final_content),
                                                "original_ideas": raw_ideas,
                                                "style": draft_style,
                                                "source": "draft_assistant"
                                            }

                                            curation_file = curation_dir / f"{draft_persona}_curated.jsonl"
                                            with open(curation_file, 'a', encoding='utf-8') as f:
                                                f.write(json.dumps(curation_entry, ensure_ascii=False) + '\n')

                                            st.success(f"✅ Saved to curated posts!")

                                        except Exception as e:
                                            st.error(f"❌ Save failed: {str(e)}")

                                with col_regenerate:
                                    if st.button("🔄 **Regenerate**", use_container_width=True, key="regen_draft"):
                                        st.info("💡 Click 'Write Draft' again to regenerate with different wording")

                                with st.expander("📊 Draft Details"):
                                    st.json({
                                        "persona": draft_persona,
                                        "platform": draft_platform,
                                        "style": draft_style,
                                        "original_length": len(raw_ideas),
                                        "drafted_length": len(drafted),
                                        "quality_score": result.get("quality_score", "N/A"),
                                        "content_type": result.get("content_type", "draft")
                                    })
                        else:
                            st.error("❌ Draft failed - no content returned")

                except Exception as e:
                    st.error(f"❌ **Draft Error:** {str(e)}")
                    import traceback
                    with st.expander("🔍 Debug Info"):
                        st.code(traceback.format_exc())

    # === REWRITE MODE: Raw Content + Opinion → Persona Post ===
    with st.expander("✨ Rewrite Mode: Content + Opinion → Persona Post"):
        st.markdown("**Give me raw content and your opinion, I'll turn it into a persona post**")

        col_raw, col_opinion = st.columns(2)

        with col_raw:
            st.markdown("**📄 Raw Content**")
            st.caption("Paste the original post/article/content here")
            raw_content = st.text_area(
                "Raw content",
                placeholder="e.g., 'MIT study shows AI coding assistants increase speed by 55% but bugs by 15%'",
                height=150,
                key="raw_content",
                label_visibility="collapsed"
            )

        with col_opinion:
            st.markdown("**💭 Your Opinion/Angle**")
            st.caption("What's your take? What do you want to say about it?")
            opinion = st.text_area(
                "Your opinion",
                placeholder="e.g., 'This is concerning. Speed doesn't matter if quality drops. Who fixes the bugs?'",
                height=150,
                key="opinion",
                label_visibility="collapsed"
            )

        st.markdown("---")

        col_rewrite_persona, col_rewrite_platform = st.columns(2)

        with col_rewrite_persona:
            rewrite_persona_options = [f"{persona_info.get(key, {}).get('name', key)} ({key})" for key in persona_keys]
            selected_rewrite_persona = st.selectbox("Persona", rewrite_persona_options, key="rewrite_persona")
            rewrite_persona = selected_rewrite_persona.split(" (")[-1].rstrip(")")

        with col_rewrite_platform:
            rewrite_platform = st.selectbox("Platform", list(configured_platforms.keys()), key="rewrite_platform")

        if st.button("✨ **Rewrite into Persona Post**", type="primary", use_container_width=True, key="rewrite_btn"):
            if not raw_content or not opinion:
                st.warning("⚠️ Please provide both raw content and your opinion")
            else:
                try:
                    with st.spinner("🔄 Rewriting..."):
                        from src.publishing.rewriter import ContentRewriter
                        import asyncio

                        rewriter = ContentRewriter()

                        # Combine raw content + opinion
                        combined_content = f"{raw_content}\n\n[YOUR TAKE]: {opinion}"

                        # Create analyzed_content structure
                        analyzed_content = {
                            "original_content": combined_content,
                            "category": "opinion",
                            "topics": ["user_opinion"],
                            "angle": opinion[:100] if len(opinion) > 100 else opinion
                        }

                        # Run async rewrite
                        result = asyncio.run(
                            rewriter.rewrite_analyzed_post(
                                analyzed_content=analyzed_content,
                                persona=rewrite_persona,
                                platform=rewrite_platform,
                                post_id=f"opinion_{datetime.now().timestamp()}"
                            )
                        )

                        if result and result.get("rewritten_content"):
                            rewritten = result["rewritten_content"]

                            st.success("✅ **Rewrite complete!**")

                            st.markdown("### 📝 Your Persona Post:")
                            st.code(rewritten, language=None)

                            # Copy to clipboard button (text will be in a text area for easy copying)
                            st.text_area(
                                "Copy this",
                                value=rewritten,
                                height=200,
                                key="rewritten_output",
                                label_visibility="collapsed"
                            )

                            # Save to curation button
                            col_save, col_schedule = st.columns(2)

                            with col_save:
                                if st.button("💾 **Save to Curation**", type="secondary", use_container_width=True, key="save_curation"):
                                    try:
                                        from pathlib import Path
                                        import json

                                        # Create curation directory if it doesn't exist
                                        curation_dir = Path("data/curated_posts")
                                        curation_dir.mkdir(parents=True, exist_ok=True)

                                        # Create curation entry
                                        curation_entry = {
                                            "id": f"{rewrite_persona}_{datetime.now().timestamp()}",
                                            "persona": rewrite_persona,
                                            "platform": rewrite_platform,
                                            "original_content": raw_content,
                                            "user_opinion": opinion,
                                            "rewritten_content": rewritten,
                                            "content_type": result.get("content_type", "unknown"),
                                            "created_at": datetime.now().isoformat(),
                                            "status": "curated",
                                            "source": "rewrite_mode"
                                        }

                                        # Save to persona-specific file
                                        curation_file = curation_dir / f"{rewrite_persona}_curated.jsonl"
                                        with open(curation_file, 'a', encoding='utf-8') as f:
                                            f.write(json.dumps(curation_entry, ensure_ascii=False) + '\n')

                                        st.success(f"✅ Saved to curation queue: {curation_file.name}")

                                    except Exception as e:
                                        st.error(f"❌ Save failed: {str(e)}")

                            with col_schedule:
                                if st.button("⏱️ **Schedule Post**", type="secondary", use_container_width=True, key="schedule_rewrite"):
                                    st.info("💡 Use the 'Post Now' section above to schedule this content")

                            with st.expander("📊 Rewrite Details"):
                                st.json({
                                    "persona": rewrite_persona,
                                    "platform": rewrite_platform,
                                    "original_length": len(combined_content),
                                    "rewritten_length": len(rewritten),
                                    "content_type": result.get("content_type", "unknown"),
                                    "examples_used": result.get("examples_used", [])
                                })
                        else:
                            st.error("❌ Rewrite failed - no content returned")

                except Exception as e:
                    st.error(f"❌ **Rewrite Error:** {str(e)}")
                    import traceback
                    with st.expander("🔍 Debug Info"):
                        st.code(traceback.format_exc())

    # === ADVANCED OPTIONS ===
    with st.expander("🔧 Advanced: Generate from Posts"):
        gen_platform = st.selectbox("Platform", list(configured_platforms.keys()), key="gen_platform")
        limit = st.slider("Max source posts", 1, 50, 5, key="gen_limit")
        use_recent_only = st.checkbox("Use most recent posts only", value=True, key="gen_recent")

        if st.button("🔮 Generate Post", key="gen_button"):
            dbm = get_database_manager()
            try:
                posts = dbm.get_posts(limit=limit)
                if not posts:
                    st.info("No source posts available.")
                else:
                    gen = PersonaGenerator()
                    created = gen.generate_and_schedule(
                        persona, gen_platform, posts, schedule_in_minutes=0
                    )
                    st.success(f"Generated {len(created)} post(s). Check your account!")
            except Exception as e:
                st.error(f"Generation failed: {e}")
