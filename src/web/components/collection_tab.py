#!/usr/bin/env python3
"""
Collection Tab for Streamlit UI
Provides unified collection interface with real-time progress
"""

import asyncio
import os
import uuid
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
from src.utils.collection_storage import CollectionStorage
from src.utils.logging_config import get_logger

logger = get_logger(__name__)
COLLECTION_STORAGE = CollectionStorage()


def _format_log_entry(entry) -> str:
    if isinstance(entry, str):
        return entry
    if not isinstance(entry, dict):
        return str(entry)

    timestamp = entry.get("timestamp", "")
    status = entry.get("status", "")
    message = entry.get("message", "")
    posts = entry.get("posts_collected")
    error = entry.get("error")

    parts = []
    if timestamp:
        parts.append(f"[{timestamp}]")
    if status:
        parts.append(status)
    if message:
        parts.append(message)

    line = " ".join(parts)
    if posts:
        line += f" (Posts: {posts})"
    if error:
        line += f" ❌ Error: {error}"
    return line


def _safe_count(db: NewDatabaseManager, method_name: str) -> int:
    """Safely call a database manager method and return the length of its result."""
    method = getattr(db, method_name, None)
    if not callable(method):
        logger.debug(f"Database manager missing method {method_name}")
        return 0

    try:
        result = method()
        if result is None:
            return 0
        return len(result)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"Failed to fetch {method_name}: {exc}")
        return 0


def render_collection_tab():
    """Render the collection tab in Streamlit"""
    st.header("📥 Collection Manager")

    # Local dark pane styling to avoid global white background
    st.markdown("""
    <style>
      .collect-pane {
        background-color: #0b1220;
        border: 1px solid #1f2a44;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
      }
      .collect-card {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 1.5rem;
        border-radius: 8px;
        text-align: center;
      }
      .collect-card .value {
        font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #e5e7eb;
      }
      .collect-card .label {
        font-size: 0.875rem; color: #9ca3af;
      }
      /* History preview styling */
      .post-preview {
        background-color: #0f172a;
        border: 1px solid #1f2937;
        border-radius: 8px;
        padding: 12px 14px;
        margin: 8px 0 14px 0;
      }
      .post-preview .meta {
        color: #cbd5e1;
        font-size: 0.9rem;
        margin-bottom: 6px;
      }
      .post-preview .content {
        color: #e5e7eb;
        white-space: pre-wrap; /* preserve newlines */
        line-height: 1.4;
        margin-bottom: 6px;
      }
      .post-preview .url {
        color: #94a3b8;
        font-size: 0.8rem;
      }
    </style>
    """, unsafe_allow_html=True)
    st.markdown('<div class="collect-pane">', unsafe_allow_html=True)

    # Unique key base per session to avoid DuplicateWidgetID when this tab is rendered
    if 'collection_tab_key_base' not in st.session_state:
        st.session_state.collection_tab_key_base = uuid.uuid4().hex
    key_base = st.session_state.collection_tab_key_base

    # Initialize service
    if "collection_service" not in st.session_state:
        st.session_state.collection_service = UnifiedCollectionService()

    service: UnifiedCollectionService = st.session_state.collection_service

    # Load persisted logs/history into session state once
    if "collection_logs" not in st.session_state:
        st.session_state.collection_logs = COLLECTION_STORAGE.load_logs()
    if "collection_history" not in st.session_state:
        st.session_state.collection_history = COLLECTION_STORAGE.load_history()

    # Show current status
    st.subheader("📊 Current Status")

    # Get database stats
    db = NewDatabaseManager()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        threads_count = len(db.get_posts_by_platform("threads"))
        st.markdown(f"""
        <div class="collect-card">
            <div class="value">{threads_count}</div>
            <div class="label">🧵 Threads</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        twitter_count = len(db.get_posts_by_platform("twitter"))
        st.markdown(f"""
        <div class="collect-card">
            <div class="value">{twitter_count}</div>
            <div class="label">🐦 Twitter</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        reddit_count = len(db.get_posts_by_platform("reddit"))
        st.markdown(f"""
        <div class="collect-card">
            <div class="value">{reddit_count}</div>
            <div class="label">📱 Reddit</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        github_count = _safe_count(db, "get_github_trending_repos")
        st.markdown(f"""
        <div class="collect-card">
            <div class="value">{github_count}</div>
            <div class="label">💻 GitHub</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col5:
        telegram_count = _safe_count(db, "get_telegram_messages")
        st.markdown(f"""
        <div class="collect-card">
            <div class="value">{telegram_count}</div>
            <div class="label">📢 Telegram</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Collection controls
    st.subheader("🎯 Collect Posts")

    # Platform selection
    col1, col2 = st.columns([2, 1])

    with col1:
        # Stable key so selection persists across renders
        platform = st.selectbox(
            "Select Platform",
            options=["threads", "twitter", "reddit", "github_trending", "telegram_channels", "discovery"],
            format_func=lambda x: {
                "threads": "🧵 Threads",
                "twitter": "🐦 Twitter",
                "reddit": "📱 Reddit",
                "github_trending": "💻 GitHub Trending",
                "telegram_channels": "📢 Telegram Channels",
                "discovery": "🔍 Autonomous Discovery",
                "twitter": "🐦 Twitter",
                "reddit": "📱 Reddit",
            }.get(x, x),
            key=f"{key_base}_collection_platform_select",
        )

    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        # Stable key for checkbox
        collect_all = st.checkbox("Collect All", value=False, key=f"{key_base}_collection_collect_all")

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
            button_key = f"{key_base}_collect_all_button"
        else:
            button_label = f"📥 Collect from {platform.title()}"
            button_key = f"{key_base}_collect_{platform}_button"

        if st.button(button_label, key=button_key, type="primary"):
            run_collection(service, platform if not collect_all else None, collect_all)

    st.divider()

    # Collection logs section
    if st.session_state.collection_logs:
        st.subheader("📝 Collection Logs")
        recent_logs = st.session_state.collection_logs[-15:]  # Show last 15 entries
        st.text_area(
            "",
            value="\n".join(_format_log_entry(entry) for entry in recent_logs),
            height=250,
            disabled=True,
            key="collection_logs_display",
        )

    st.divider()

    # Collection history
    st.subheader("📜 Collection History")

    if st.session_state.collection_history:
        # Show recent collections
        for i, result in enumerate(reversed(st.session_state.collection_history[-10:])):
            # Handle both dict and dataclass formats
            if isinstance(result, dict):
                platform = result.get('platform', 'unknown')
                posts_collected = result.get('posts_collected', 0)
                success = result.get('success', False)
                duration_seconds = result.get('duration_seconds', 0.0)
                metadata = result.get('metadata', {})
            else:
                platform = result.platform
                posts_collected = result.posts_collected
                success = result.success
                duration_seconds = result.duration_seconds
                metadata = getattr(result, 'metadata', {}) or {}
            
            with st.expander(
                f"{'✅' if success else '❌'} {platform.title()} - "
                f"{posts_collected} posts - "
                f"{datetime.fromisoformat(metadata.get('timestamp', datetime.now().isoformat())).strftime('%Y-%m-%d %H:%M')}"
            ):
                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    st.metric("Posts Collected", posts_collected)

                with col2:
                    st.metric("Duration", f"{duration_seconds:.1f}s")

                with col3:
                    status_emoji = "✅" if success else "❌"
                    st.metric(
                        "Status",
                        f"{status_emoji} {'Success' if success else 'Failed'}",
                    )

                error_msg = result.get('error') if isinstance(result, dict) else getattr(result, 'error', None)
                if error_msg:
                    st.error(f"Error: {error_msg}")

                automation_info = metadata.get("automation") if isinstance(metadata, dict) else {}
                if automation_info:
                    st.markdown("**Automation Summary**")
                    st.json(automation_info)

                # Recent posts preview to help locate items in DB/Supabase
                st.markdown("---")
                st.caption("Recent posts for quick access")
                try:
                    # Prefer getting a larger batch and filter/sort client-side for robustness
                    recent_all = db.get_posts(limit=200) or []
                    # Filter by platform
                    recent_platform = [
                        p for p in recent_all
                        if isinstance(p, dict) and (p.get("platform") or "").lower() == (platform or "").lower()
                    ]
                    # Sort by created_at desc (fallback to analyzed_at)
                    def _ts(p):
                        v = p.get("created_at") or p.get("analyzed_at") or ""
                        return v
                    recent_platform.sort(key=_ts, reverse=True)
                    preview = recent_platform[:5]
                    if preview:
                        post_ids_for_copy: list[str] = []
                        for p in preview:
                            post_id = p.get("post_id") or ""
                            author = p.get("author") or "unknown"
                            created_at = p.get("created_at") or ""
                            url = p.get("url") or ""
                            content = p.get("content") or ""
                            if post_id:
                                post_ids_for_copy.append(post_id)
                            # Render with preserved formatting and dark card
                            st.markdown(
                                f"""
                                <div class="post-preview">
                                  <div class="meta"><b>{post_id}</b> &nbsp;|&nbsp; {author} &nbsp;|&nbsp; {(created_at or '')[:19]}</div>
                                  <div class="content">{(content or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</div>
                                  <div class="url">{url}</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                        if post_ids_for_copy:
                            st.text_area(
                                "Post IDs (copy to Supabase filter)",
                                value=", ".join(post_ids_for_copy),
                                height=60
                            )
                    else:
                        st.info("No recent posts found for this platform yet.")
                except Exception as _e:
                    st.caption(f"Preview unavailable: {str(_e)[:80]}")
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

    # Close dark pane wrapper
    st.markdown('</div>', unsafe_allow_html=True)

def run_collection(
    service: UnifiedCollectionService, platform: Optional[str], collect_all: bool
):
    """Run collection with progress updates"""

    # Progress containers
    progress_container = st.empty()
    status_container = st.empty()
    logs_container = st.empty()

    # Initialize logs and history
    if "collection_logs" not in st.session_state:
        st.session_state.collection_logs = COLLECTION_STORAGE.load_logs()
    if "collection_history" not in st.session_state:
        st.session_state.collection_history = COLLECTION_STORAGE.load_history()

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
        log_entry = {
            "timestamp": timestamp,
            "status": status_emoji,
            "message": progress.current_message,
            "posts_collected": progress.posts_collected if progress.posts_collected > 0 else 0,
            "error": progress.error,
        }

        st.session_state.collection_logs.append(log_entry)
        COLLECTION_STORAGE.append_log(log_entry)

        # Display last 10 log entries
        recent_logs = st.session_state.collection_logs[-10:]
        with logs_container.container():
            st.text_area(
                "📝 Collection Logs",
                value="\n".join(_format_log_entry(entry) for entry in recent_logs),
                height=200,
                disabled=True,
            )

    # Run collection
    async def do_collection():
        try:
            if collect_all:
                results = await service.collect_all(progress_callback=update_progress)

                # Add to history - ensure history list exists
                if "collection_history" not in st.session_state:
                    st.session_state.collection_history = []
                
                # Add to history
                for platform_name, result in results.items():
                    if result:
                        if not hasattr(result, 'metadata') or result.metadata is None:
                            result.metadata = {}
                        result.metadata["timestamp"] = datetime.now().isoformat()
                        # Convert to dict for better session state persistence
                        history_entry = {
                            'platform': result.platform,
                            'posts_collected': result.posts_collected,
                            'success': result.success,
                            'duration_seconds': result.duration_seconds,
                            'error': result.error,
                            'metadata': result.metadata,
                            'posts_analyzed': getattr(result, 'posts_analyzed', 0),
                            'posts_failed': getattr(result, 'posts_failed', 0),
                        }
                        st.session_state.collection_history.append(history_entry)
                        COLLECTION_STORAGE.append_history(history_entry)

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

                # Add to history - ensure history list exists
                if "collection_history" not in st.session_state:
                    st.session_state.collection_history = []
                
                # Add to history
                if result:
                    if not hasattr(result, 'metadata') or result.metadata is None:
                        result.metadata = {}
                    result.metadata["timestamp"] = datetime.now().isoformat()
                    # Convert to dict for better session state persistence
                    history_entry = {
                        'platform': result.platform,
                        'posts_collected': result.posts_collected,
                        'success': result.success,
                        'duration_seconds': result.duration_seconds,
                        'error': result.error,
                        'metadata': result.metadata,
                        'posts_analyzed': getattr(result, 'posts_analyzed', 0),
                        'posts_failed': getattr(result, 'posts_failed', 0),
                    }
                    st.session_state.collection_history.append(history_entry)
                    COLLECTION_STORAGE.append_history(history_entry)

                    # Show result
                    if result.success:
                        st.success(
                            f"✅ Collected {result.posts_collected} posts from {platform.title()}!"
                        )
                    else:
                        st.error(f"❌ Collection failed: {result.error}")
        except Exception as e:
            st.error(f"❌ Collection error: {e}")
            logger.error(f"Collection error: {e}", exc_info=True)
        finally:
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
