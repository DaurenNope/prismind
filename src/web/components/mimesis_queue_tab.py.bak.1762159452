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
    twitter_cookies_file = os.getenv("TWITTER_COOKIES_FILE", "")
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
