"""
Analysis Tab - AI Analysis with Quality Filtering
"""

import streamlit as st
from src.services.new_database_manager import NewDatabaseManager
from src.services.analysis_runner import analyze_recent_posts
from src.utils.post_validator import PostValidator


def render_analysis_tab():
    """Render the analysis tab with quality filtering"""

    st.subheader("🤖 AI Analysis & Quality Control")
    st.markdown("Analyze unanalyzed posts and filter out low quality content")

    db = NewDatabaseManager()

    # Get stats
    unanalyzed = db.get_unanalyzed_posts(limit=1000)

    # Group by platform
    by_platform = {}
    for p in unanalyzed:
        platform = p.get("platform", "unknown")
        by_platform[platform] = by_platform.get(platform, 0) + 1

    # Display stats
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Unanalyzed", len(unanalyzed))

    with col2:
        twitter_count = by_platform.get("twitter", 0)
        st.metric("Twitter", twitter_count)

    with col3:
        threads_count = by_platform.get("threads", 0)
        st.metric("Threads", threads_count)

    with col4:
        reddit_count = by_platform.get("reddit", 0)
        st.metric("Reddit", reddit_count)

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

                        # Run analysis on single post using orchestrator
                        from src.pipeline.orchestrator import get_orchestrator
                        import asyncio
                        
                        orch = get_orchestrator()
                        # Analyze this specific post (orchestrator will get unanalyzed posts)
                        analyzed_count = asyncio.run(orch.analyze_batch(limit=1))
                        
                        # Check if analysis succeeded
                        if analyzed_count > 0:
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

        if st.button("🔍 Validate Quality"):
            with st.spinner("Validating post quality..."):
                validator = PostValidator(strict=True)

                valid_count = 0
                low_quality_count = 0
                invalid_count = 0

                for post in unanalyzed[:100]:  # Check first 100
                    validation = validator.validate_post(post)

                    if not validation.is_valid:
                        invalid_count += 1
                    elif validation.warnings:
                        low_quality_count += 1
                    else:
                        valid_count += 1

                st.metric("✅ Valid", valid_count)
                st.metric("⚠️ Low Quality", low_quality_count)
                st.metric("❌ Invalid", invalid_count)

                if invalid_count > 0:
                    st.warning(f"Found {invalid_count} invalid posts")
                    if st.button("🗑️ Delete Invalid"):
                        # Delete logic here
                        st.info("Delete functionality can be added")

    st.markdown("---")

    # Show recent analysis results
    st.subheader("Recently Analyzed Posts")

    all_posts = db.get_posts(limit=100)
    analyzed = [p for p in all_posts if p.get("analyzed_at")]

    if analyzed:
        st.write(f"Showing {min(10, len(analyzed))} of {len(analyzed)} analyzed posts")

        for i, post in enumerate(analyzed[:10]):
            with st.expander(
                f"{i + 1}. {post.get('author', 'Unknown')} - {post.get('platform', 'unknown')}"
            ):
                st.markdown(f"**Content:** {post.get('content', '')[:200]}...")

                if post.get("ai_summary"):
                    st.markdown(f"**AI Summary:** {post.get('ai_summary')}")

                col1, col2, col3 = st.columns(3)
                with col1:
                    score = post.get("content_quality_score", 0)
                    st.metric("Quality Score", f"{score}/10")
                with col2:
                    sentiment = post.get("sentiment", "unknown")
                    st.metric("Sentiment", sentiment)
                with col3:
                    created = post.get("created_at", "")[:10]
                    st.metric("Date", created)

                if post.get("key_concepts"):
                    st.markdown(f"**Key Concepts:** {post.get('key_concepts')}")
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
