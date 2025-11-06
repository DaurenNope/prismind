#!/usr/bin/env python3
"""
Collection Tab for Streamlit UI
Provides unified collection interface with real-time progress
"""

import asyncio
import os
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional

from src.services.unified_collection_service import (
    UnifiedCollectionService,
    CollectionProgress,
    CollectionResult,
    CollectionStatus,
)
from src.services.new_database_manager import NewDatabaseManager


def render_collection_tab():
    """Render the collection tab in Streamlit"""
    st.header("📥 Collection Manager")

    # Initialize service
    if "collection_service" not in st.session_state:
        st.session_state.collection_service = UnifiedCollectionService()

    service: UnifiedCollectionService = st.session_state.collection_service

    # Show current status
    st.subheader("📊 Current Status")

    # Get database stats
    db = NewDatabaseManager()

    col1, col2, col3 = st.columns(3)

    with col1:
        threads_count = len(db.get_posts_by_platform("threads"))
        st.metric("Threads Posts", threads_count)

    with col2:
        twitter_count = len(db.get_posts_by_platform("twitter"))
        st.metric("Twitter Posts", twitter_count)

    with col3:
        reddit_count = len(db.get_posts_by_platform("reddit"))
        st.metric("Reddit Posts", reddit_count)

    st.divider()

    # Collection controls
    st.subheader("🎯 Collect Posts")

    # Platform selection
    col1, col2 = st.columns([2, 1])

    with col1:
        # Deterministic unique key for selectbox
        unique_key = "collection_tab_select_platform"
        platform = st.selectbox(
            "Select Platform",
            options=["threads", "twitter", "reddit"],
            format_func=lambda x: {
                "threads": "🧵 Threads",
                "twitter": "🐦 Twitter",
                "reddit": "📱 Reddit",
            }.get(x, x),
            key=unique_key,
        )

    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        # Unique key for checkbox to avoid DuplicateWidgetID
        # Deterministic unique key for checkbox
        collect_all = st.checkbox("Collect All", value=False, key="collection_tab_collect_all")

    # Collection button
    if service.is_collecting():
        st.warning("⏳ Collection in progress...")

        # Show current progress
        progress = service.get_current_progress()
        if progress:
            st.info(f"**{progress.platform}**: {progress.current_message}")

            if progress.posts_collected > 0:
                st.progress(min(progress.posts_collected / 100, 1.0))
                st.caption(f"Collected: {progress.posts_collected} posts")
    else:
        if collect_all:
            button_label = "🚀 Collect from All Platforms"
            button_key = "collect_all_button"
        else:
            button_label = f"📥 Collect from {platform.title()}"
            button_key = f"collect_{platform}_button"

        if st.button(button_label, key=button_key, type="primary"):
            run_collection(service, platform if not collect_all else None, collect_all)

    st.divider()

    # Collection logs section
    if "collection_logs" in st.session_state and st.session_state.collection_logs:
        st.subheader("📝 Collection Logs")
        recent_logs = st.session_state.collection_logs[-15:]  # Show last 15 entries
        st.text_area(
            "",
            value="\n".join(recent_logs),
            height=250,
            disabled=True,
            key="collection_logs_display",
        )

    st.divider()

    # Collection history
    st.subheader("📜 Collection History")

    if "collection_history" not in st.session_state:
        st.session_state.collection_history = []

    if st.session_state.collection_history:
        # Show recent collections
        for i, result in enumerate(reversed(st.session_state.collection_history[-10:])):
            with st.expander(
                f"{'✅' if result.success else '❌'} {result.platform.title()} - "
                f"{result.posts_collected} posts - "
                f"{datetime.fromisoformat(result.metadata.get('timestamp', datetime.now().isoformat())).strftime('%Y-%m-%d %H:%M')}"
            ):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Posts Collected", result.posts_collected)

                with col2:
                    st.metric("Duration", f"{result.duration_seconds:.1f}s")

                with col3:
                    status_emoji = "✅" if result.success else "❌"
                    st.metric(
                        "Status",
                        f"{status_emoji} {'Success' if result.success else 'Failed'}",
                    )

                if result.error:
                    st.error(f"Error: {result.error}")
    else:
        st.info("No collection history yet. Start a collection to see results here.")

    # Advanced settings
    with st.expander("⚙️ Advanced Settings"):
        st.number_input(
            "Max Retries",
            min_value=1,
            max_value=5,
            value=3,
            key="collection_max_retries",
            help="Maximum number of retry attempts on failure",
        )

        st.number_input(
            "Retry Delay (seconds)",
            min_value=1,
            max_value=30,
            value=5,
            key="collection_retry_delay",
            help="Delay between retry attempts",
        )

        st.checkbox(
            "Enable Supabase Sync",
            value=True,
            key="collection_supabase_sync",
            help="Sync collected posts to Supabase",
        )


def run_collection(
    service: UnifiedCollectionService, platform: Optional[str], collect_all: bool
):
    """Run collection with progress updates"""

    # Progress containers
    progress_container = st.empty()
    status_container = st.empty()
    logs_container = st.empty()

    # Initialize logs
    if "collection_logs" not in st.session_state:
        st.session_state.collection_logs = []

    # Progress callback with detailed logging
    def update_progress(progress: CollectionProgress):
        """Update UI with progress"""
        # Update status
        status_emoji = {
            CollectionStatus.STARTING: "🚀",
            CollectionStatus.AUTHENTICATING: "🔐",
            CollectionStatus.COLLECTING: "📥",
            CollectionStatus.ANALYZING: "🤖",
            CollectionStatus.COMPLETED: "✅",
            CollectionStatus.FAILED: "❌",
        }.get(progress.status, "⏳")

        status_container.info(f"{status_emoji} {progress.current_message}")

        # Update progress bar
        if progress.posts_collected > 0:
            progress_container.progress(min(progress.posts_collected / 100, 1.0))

        # Add to logs
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {status_emoji} {progress.current_message}"
        if progress.posts_collected > 0:
            log_entry += f" (Posts: {progress.posts_collected})"
        if progress.error:
            log_entry += f" ❌ Error: {progress.error}"

        st.session_state.collection_logs.append(log_entry)

        # Display last 10 log entries
        recent_logs = st.session_state.collection_logs[-10:]
        with logs_container.container():
            st.text_area(
                "📝 Collection Logs",
                value="\n".join(recent_logs),
                height=200,
                disabled=True,
            )

    # Run collection
    async def do_collection():
        if collect_all:
            results = await service.collect_all(progress_callback=update_progress)

            # Add to history
            for platform_name, result in results.items():
                result.metadata["timestamp"] = datetime.now().isoformat()
                st.session_state.collection_history.append(result)

            # Show summary
            total_collected = sum(r.posts_collected for r in results.values())
            success_count = sum(1 for r in results.values() if r.success)

            if success_count == len(results):
                st.success(f"✅ Collected {total_collected} posts from all platforms!")
            else:
                st.warning(
                    f"⚠️ Collected {total_collected} posts, {success_count}/{len(results)} platforms succeeded"
                )
        else:
            result = await service.collect(platform, progress_callback=update_progress)

            # Add to history
            result.metadata["timestamp"] = datetime.now().isoformat()
            st.session_state.collection_history.append(result)

            # Show result
            if result.success:
                st.success(
                    f"✅ Collected {result.posts_collected} posts from {platform.title()}!"
                )
            else:
                st.error(f"❌ Collection failed: {result.error}")

        # Clear progress
        progress_container.empty()
        status_container.empty()

        # Rerun to update UI
        st.rerun()

    # Run async task
    try:
        asyncio.run(do_collection())
    except Exception as e:
        st.error(f"❌ Error: {e}")


def render_collection_schedule():
    """Render collection scheduling options"""
    st.subheader("⏰ Scheduled Collection")

    st.info("Coming soon: Schedule automatic collections at specific times")

    # Placeholder for future scheduling
    col1, col2 = st.columns(2)

    with col1:
        st.selectbox(
            "Collection Frequency",
            options=["Manual", "Daily", "Every 6 hours", "Every 12 hours"],
            disabled=True,
        )

    with col2:
        st.time_input("Collection Time", disabled=True)

    st.button("Enable Scheduling", disabled=True)
