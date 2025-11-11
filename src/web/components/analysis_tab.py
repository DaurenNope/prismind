"""
Analysis Tab - AI Analysis with Quality Filtering
"""

import asyncio
import streamlit as st
from src.services.new_database_manager import NewDatabaseManager
from src.services.analysis_runner import analyze_recent_posts
from src.utils.post_validator import PostValidator
from src.services.analysis.post_analyzer import analyze_and_store_post
from src.storage.db import get_storage
from src.services.analysis_lock import analysis_lock_guard


def render_analysis_tab():
    """Render the analysis tab with quality filtering"""

    st.subheader("🤖 AI Analysis & Quality Control")
    st.markdown("Analyze unanalyzed posts and filter out low quality content")

    # Styling for analyzed post previews
    st.markdown(
        """
        <style>
        .analysis-preview {
            background-color: #0f172a;
            border: 1px solid #1f2937;
            border-radius: 8px;
            padding: 14px 16px;
            margin: 10px 0 18px 0;
        }
        .analysis-preview .meta {
            color: #cbd5e1;
            font-size: 0.9rem;
            margin-bottom: 8px;
        }
        .analysis-preview .section-title {
            color: #94a3b8;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 6px;
            margin-bottom: 4px;
        }
        .analysis-preview .content {
            color: #e5e7eb;
            line-height: 1.5;
            white-space: pre-wrap;
        }
        .analysis-preview .tags {
            color: #a1a1aa;
            font-size: 0.8rem;
            margin-top: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    def _escape_html(text: str) -> str:
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )

    # Show recent builder updates influencing analysis
    try:
        from src.utils.diary_storage import DiaryStorage
        from src.core.discovery.profile_manager import ProfileManager
        ds = DiaryStorage()
        pm = None
        try:
            pm = ProfileManager()
            active_profile_id = (pm.get_active_profile() or {}).get("id")
        except Exception:
            active_profile_id = None
        entries = ds.load_entries(profile_key=active_profile_id, limit=2)
        if entries:
            with st.expander("📓 Recent builder updates (affecting analysis)", expanded=False):
                for e in entries:
                    ts = (e.get("timestamp") or "")[:19].replace("T", " ")
                    shipped = (e.get("shipped") or "").strip()
                    focus = (e.get("focus") or "").strip()
                    st.caption(f"{ts} • {active_profile_id or (e.get('profile_key') or 'all')}")
                    st.write(shipped)
                    if focus:
                        st.caption(f"focus: {focus}")
                    st.divider()
    except Exception:
        pass

    db = NewDatabaseManager()

    # Get stats
    unanalyzed = db.get_unanalyzed_posts(limit=1000)

    # Group by platform
    by_platform = {}
    for p in unanalyzed:
        platform = p.get("platform", "unknown")
        by_platform[platform] = by_platform.get(platform, 0) + 1

    # Display stats with modern gradient cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{len(unanalyzed)}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">Total Unanalyzed</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        twitter_count = by_platform.get("twitter", 0)
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 8px; text-align: center;">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{twitter_count}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">🐦 Twitter</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        threads_count = by_platform.get("threads", 0)
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 8px; text-align: center;">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{threads_count}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">🧵 Threads</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        reddit_count = by_platform.get("reddit", 0)
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 8px; text-align: center;">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{reddit_count}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">📱 Reddit</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Analysis controls
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Run Analysis")

        # Platform filter
        platform_options = ["All Platforms"] + sorted(list(by_platform.keys()))
        selected_platform = st.selectbox("Platform", platform_options)

        # Batch size
        batch_size = st.number_input(
            "Batch Size",
            min_value=1,
            max_value=500,
            value=50,
            step=10,
            help="Number of posts to analyze",
        )

        # Analyze button
        if st.button("🤖 Run AI Analysis", type="primary"):
            platform_filter = (
                None if selected_platform == "All Platforms" else selected_platform
            )

            # Create placeholder for progress
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            log_placeholder = st.empty()

            try:
                with analysis_lock_guard() as locked:
                    if not locked:
                        status_placeholder.warning("Analysis is already running elsewhere. Try again shortly.")
                        return

                    # Show initial status
                    progress_placeholder.progress(0)
                    status_placeholder.info(
                        f"🔄 Starting analysis of {batch_size} posts..."
                    )

                    # Create a log container
                    log_lines = []

                    def add_log(message):
                        log_lines.append(f"{message}")
                        log_placeholder.text_area(
                            "📋 Live Log",
                            "\n".join(log_lines[-20:]),  # Show last 20 lines
                            height=200,
                        )

                    add_log(f"Starting analysis...")
                    add_log(f"Platform filter: {platform_filter or 'All'}")
                    add_log(f"Batch size: {batch_size}")
                    add_log("")

                    # Get posts to analyze
                    posts_to_analyze = db.get_unanalyzed_posts(
                        limit=batch_size,
                        platforms=[platform_filter] if platform_filter else None,
                    )
                    add_log(f"Found {len(posts_to_analyze)} unanalyzed posts")
                    add_log("")

                    if not posts_to_analyze:
                        status_placeholder.warning("No posts to analyze")
                        return

                    # Analyze with progress
                    successful = 0
                    failed = 0
                    errors = []

                    storage = get_storage()
                    supabase_adapter = getattr(storage, "_supabase", None)

                    for i, post in enumerate(posts_to_analyze, 1):
                        try:
                            # Update progress
                            progress = i / len(posts_to_analyze)
                            progress_placeholder.progress(progress)
                            status_placeholder.info(
                                f"🤖 Analyzing post {i}/{len(posts_to_analyze)}: {post.get('author', 'Unknown')[:30]}..."
                            )

                            add_log(
                                f"[{i}/{len(posts_to_analyze)}] Analyzing: {post.get('platform')} - {post.get('author', 'Unknown')[:30]}"
                            )

                            # Run analysis on this specific post
                            analyzed_success = asyncio.run(
                                analyze_and_store_post(
                                    db,
                                    post,
                                    supabase_manager=supabase_adapter,
                                )
                            )

                            if analyzed_success:
                                successful += 1
                                add_log(f"    ✅ Success")
                            else:
                                failed += 1
                                add_log(f"    ❌ Failed (post may already be analyzed)")
                                errors.append(f"Post {post.get('post_id', 'unknown')} analysis failed")

                        except Exception as e:
                            failed += 1
                            add_log(f"    ❌ Error: {str(e)[:50]}")
                            errors.append(str(e))

                    # Final status
                    progress_placeholder.progress(1.0)

                    if successful > 0:
                        status_placeholder.success(
                            f"✅ Complete! Analyzed {successful}/{len(posts_to_analyze)} posts"
                        )
                        add_log("")
                        add_log("=" * 50)
                        add_log(f"COMPLETE: {successful} successful, {failed} failed")
                    else:
                        status_placeholder.warning(
                            f"⚠️ No posts analyzed successfully. {failed} failed."
                        )

                    if errors:
                        with st.expander("View Errors"):
                            for error in errors[:10]:
                                st.text(error)

                    # Wait a bit so user can see final status
                    import time

                    time.sleep(2)
                    st.rerun()

            except Exception as e:
                status_placeholder.error(f"Analysis failed: {e}")
                st.info("💡 Make sure Ollama is running for AI summarization")

    with col2:
        st.subheader("Quality Control")

        # Quality validation options
        validation_scope = st.radio(
            "Validation Scope",
            ["Unanalyzed Only (100)", "All Posts (Full Scan)"],
            help="Choose which posts to validate"
        )
        
        if st.button("🔍 Validate Quality", type="primary"):
            progress_placeholder = st.empty()
            status_placeholder = st.empty()
            results_placeholder = st.empty()
            
            try:
                validator = PostValidator(strict=True)
                
                # Get posts to validate
                if validation_scope == "All Posts (Full Scan)":
                    status_placeholder.info("🔄 Fetching all posts...")
                    all_posts = db.get_posts(limit=10000)  # Get all posts
                    posts_to_validate = all_posts
                else:
                    posts_to_validate = unanalyzed[:100]
                
                status_placeholder.info(f"🔄 Validating {len(posts_to_validate)} posts...")
                
                valid_count = 0
                low_quality_count = 0
                invalid_count = 0
                invalid_posts = []
                
                # Validate in batches with progress
                for i, post in enumerate(posts_to_validate, 1):
                    if i % 10 == 0:
                        progress = i / len(posts_to_validate)
                        progress_placeholder.progress(progress)
                        status_placeholder.info(f"🔄 Validating {i}/{len(posts_to_validate)}...")
                    
                    validation = validator.validate_post(post)
                    
                    if not validation.is_valid:
                        invalid_count += 1
                        invalid_posts.append({
                            'post_id': post.get('post_id', 'unknown'),
                            'platform': post.get('platform', 'unknown'),
                            'errors': validation.errors,
                            'warnings': validation.warnings
                        })
                    elif validation.warnings:
                        low_quality_count += 1
                    else:
                        valid_count += 1
                
                progress_placeholder.progress(1.0)
                
                # Show results
                with results_placeholder.container():
                    col1, col2, col3 = st.columns(3)
                    col1.metric("✅ Valid", valid_count)
                    col2.metric("⚠️ Low Quality", low_quality_count)
                    col3.metric("❌ Invalid", invalid_count)
                    
                    # Show invalid posts
                    if invalid_posts:
                        st.warning(f"Found {invalid_count} invalid posts")
                        with st.expander("View Invalid Posts", expanded=False):
                            for invalid in invalid_posts[:20]:  # Show first 20
                                st.write(f"**{invalid['post_id']}** ({invalid['platform']})")
                                st.caption(f"Errors: {', '.join(invalid['errors'][:2])}")
                                if invalid['warnings']:
                                    st.caption(f"Warnings: {', '.join(invalid['warnings'][:2])}")
                                st.divider()
                        
                        # Option to delete invalid posts
                        if st.button("🗑️ Delete Invalid Posts", type="secondary"):
                            st.warning("⚠️ Delete functionality not yet implemented. Invalid posts are logged above.")
                    else:
                        st.success("✅ All posts passed validation!")
                
                status_placeholder.success(f"✅ Validation complete: {valid_count} valid, {low_quality_count} low quality, {invalid_count} invalid")
                
            except Exception as e:
                status_placeholder.error(f"❌ Validation failed: {e}")
                st.exception(e)

    st.markdown("---")

    # Show recent analysis results
    st.subheader("Recently Analyzed Posts")

    all_posts = db.get_posts(limit=100)
    analyzed = [p for p in all_posts if p.get("analyzed_at")]

    if analyzed:
        st.write(f"Showing {min(10, len(analyzed))} of {len(analyzed)} analyzed posts")

        for i, post in enumerate(analyzed[:10]):
            author = post.get("author", "Unknown") or "Unknown"
            platform = post.get("platform", "unknown") or "unknown"
            created_at = (post.get("created_at") or "")[:19]
            post_id = post.get("post_id") or ""
            original = post.get("content") or ""
            summary_raw = post.get("ai_summary") or ""
            summary_clean = " ".join(summary_raw.split())
            tags = post.get("key_concepts") or []

            quality = post.get("content_quality_score", 0)
            sentiment = post.get("sentiment", "unknown")

            st.markdown(
                f"""
                <div class="analysis-preview">
                    <div class="meta"><b>{post_id}</b> &nbsp;|&nbsp; {author} &nbsp;|&nbsp; {platform.title()} &nbsp;|&nbsp; {created_at}</div>
                    <div class="section-title">Original Content</div>
                    <div class="content">{_escape_html(original)}</div>
                    <div class="section-title">AI Summary</div>
                    <div class="content">{_escape_html(summary_clean)}</div>
                    <div class="section-title">Metrics</div>
                    <div class="content">Quality Score: {quality}/10 &nbsp;&nbsp; Sentiment: {sentiment}</div>
                    {"<div class='section-title'>Key Concepts</div><div class='content'>" + ", ".join(tags) + "</div>" if tags else ""}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("No analyzed posts yet. Run analysis to see results here.")

    # Tips
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("""
    - **Start small**: Analyze 10-50 posts first to test
    - **Filter by platform**: Focus on one platform at a time
    - **Quality control**: Run validation before analysis to catch issues
    - **Regular analysis**: Run after each collection for best results
    """)
