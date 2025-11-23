#!/usr/bin/env python3
"""
Platform-specific collectors for Twitter, Reddit, and Threads
"""

import asyncio
import importlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set


def load_dotenv() -> bool:
    """Load environment variables from .env if python-dotenv is available."""
    try:
        module = importlib.import_module("dotenv")
        return bool(getattr(module, "load_dotenv")())
    except (ImportError, AttributeError):  # pragma: no cover
        return False


from src.core.extraction.reddit_extractor import RedditExtractor

# Core imports
from src.core.extraction.social_extractor_base import SocialPost
from src.core.extraction.threads_extractor import ThreadsExtractor
from src.core.extraction.twitter_extractor_playwright import (
    TwitterExtractorPlaywright,
)
from src.infrastructure.database.scrape_state_manager import ScrapeStateManager

# Analysis import
from src.services.analysis.post_analyzer import analyze_and_store_post, log

# Logger import
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


async def collect_twitter_bookmarks(
    db_manager, existing_ids: set, existing_urls=None, supabase_manager=None
):
    """
    Collect Twitter bookmarks

    Args:
        db_manager: Database manager instance
        existing_ids: Set of existing post IDs to avoid duplicates
        existing_urls: Set of existing URLs to avoid duplicates
        supabase_manager: Optional SupabaseManager instance for cloud sync

    Returns:
        int: Number of new posts collected
    """
    extractor = None
    try:
        # Load collection state and auto-sync if needed
        state_manager = ScrapeStateManager()
        state_manager.sync_state_from_main_db(force=False)  # Auto-recover state

        dry_run_mode = os.getenv("COLLECTION_DRY_RUN", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if dry_run_mode:
            log(
                "🧪 COLLECTION_DRY_RUN enabled - will NOT write to SQLite/Supabase",
                "warning",
            )

        force_full_collection = os.getenv("TWITTER_FORCE_FULL", "").lower() in (
            "1",
            "true",
            "yes",
        )

        # Get last collected ID from Supabase (source of truth) instead of scrape state
        last_collected_id = None
        if supabase_manager:
            try:
                # Get the most recent Twitter post from Supabase
                result = (
                    supabase_manager.client.table("posts")
                    .select("post_id")
                    .eq("platform", "twitter")
                    .order("collected_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if result.data and len(result.data) > 0:
                    last_collected_id = result.data[0].get("post_id")
                    log(
                        f"🔄 Incremental: stopping at {last_collected_id} (from Supabase)"
                    )
                else:
                    log("🆕 Full collection mode (no posts in Supabase)")
            except Exception as e:
                logger.error(f"Error: {e}")
                log(
                    f"⚠️ Could not get last post ID from Supabase: {e}, falling back to scrape state"
                )
                last_collected_id = state_manager.get_last_collected_post_id("twitter")
                if last_collected_id:
                    log(
                        f"🔄 Incremental: stopping at {last_collected_id} (from scrape state)"
                    )
                else:
                    log("🆕 Full collection mode")
        else:
            # Fallback to scrape state if Supabase not available
            last_collected_id = state_manager.get_last_collected_post_id("twitter")
            if last_collected_id:
                log(
                    f"🔄 Incremental: stopping at {last_collected_id} (from scrape state)"
                )
            else:
                log("🆕 Full collection mode")

        # Set collection limit based on mode
        # Force full mode: limit to recent posts only (avoid processing old deprecated bookmarks)
        # Normal mode: standard incremental limit
        if force_full_collection:
            collection_limit = int(os.getenv("TWITTER_FORCE_FULL_LIMIT", "150"))
            log(
                f"⚠️ Force full Twitter collection enabled - checking last {collection_limit} bookmarks only (to avoid deprecated posts)",
                "warning",
            )
            existing_ids.clear()
            last_collected_id = None
        else:
            collection_limit = 80  # Standard incremental collection limit

        twitter_username = os.getenv("TWITTER_USERNAME")
        twitter_password = os.getenv("TWITTER_PASSWORD")
        # Support multiple env names; prefer TWITTER_COOKIE_FILE
        # Fallbacks: TWITTER_COOKIES_FILE, TWITTER_COOKIES_PATH
        cookie_path_env = (
            os.getenv("TWITTER_COOKIE_FILE")
            or os.getenv("TWITTER_COOKIES_FILE")
            or os.getenv("TWITTER_COOKIES_PATH")
        )

        if not twitter_username:
            log("Twitter username not found in environment variables", "warning")
            state_manager.update_scrape_state(
                platform="twitter", posts_scraped=0, success=False
            )
            return 0

        default_cookie_path = (
            Path("config") / f"twitter_cookies_{twitter_username}.json"
        )
        cookie_path = (
            Path(cookie_path_env).expanduser()
            if cookie_path_env
            else default_cookie_path
        )

        if not twitter_password and not cookie_path.exists():
            log(
                "Twitter password or cookie file not provided; please set TWITTER_PASSWORD or supply a cookie file",
                "warning",
            )
            state_manager.update_scrape_state(
                platform="twitter", posts_scraped=0, success=False
            )
            return 0

        # Check for headless mode configuration (default: False for development, True for production)
        # Default headless true for server/VPS deployments; override locally by setting HEADLESS_MODE=false
        headless_mode = os.getenv("HEADLESS_MODE", "true").lower() in (
            "true",
            "1",
            "yes",
        )

        extractor = TwitterExtractorPlaywright(
            username=twitter_username,
            password=twitter_password,
            headless=headless_mode,
            cookie_file=str(cookie_path) if cookie_path else None,
        )

        log(f"🚀 Starting Twitter collection (headless: {headless_mode})")

        if twitter_password:
            log("Twitter credentials detected; attempting password authentication")
        else:
            log(f"Using Twitter cookie file at {cookie_path}")

        auth_success = await extractor.authenticate()
        if not auth_success:
            log("Twitter authentication failed; unable to access bookmarks", "error")
            state_manager.update_scrape_state(
                platform="twitter", posts_scraped=0, success=False
            )
            return 0

        prefer_api_first = os.getenv("TWITTER_API_FIRST", "true").lower() in (
            "1",
            "true",
            "yes",
        )

        bookmarks = []
        dom_fallback_enabled = os.getenv("TWITTER_DOM_FALLBACK", "false").lower() in (
            "1",
            "true",
            "yes",
        )
        if prefer_api_first:
            log(
                "⚙️ Attempting Twitter GraphQL bookmark fetch (API-first collector)",
                "info",
            )
            try:
                bookmarks = await extractor.get_saved_posts_api_first(
                    limit=collection_limit, stop_at_post_id=last_collected_id
                )
            except Exception as api_error:
                logger.error(f"Error: {api_error}")
                log(
                    f"⚠️ API-first Twitter collector failed: {api_error}; falling back to legacy scraper",
                    "warning",
                )

        if not bookmarks and dom_fallback_enabled:
            log(
                "⚠️ API-first returned no tweets; using DEPRECATED DOM fallback (TWITTER_DOM_FALLBACK=true)",
                "warning",
            )
            # DOM fallback uses smaller limit since it's slower
            dom_limit = min(collection_limit, 50)
            bookmarks = await extractor.get_saved_posts(
                limit=dom_limit, skip_cached_ids=existing_ids, stop_at_post_id=last_collected_id
            )
        elif not bookmarks:
            log(
                "⚠️ API-first returned no tweets and DOM fallback is disabled "
                "(set TWITTER_DOM_FALLBACK=true if you need the legacy scraper)",
                "warning",
            )

        if not bookmarks:
            # This is normal if all tweets are already saved (early-stop worked)
            log(
                "✅ Twitter collection complete - no new bookmarks to collect (all already saved)",
                "info",
            )
            state_manager.update_scrape_state(
                platform="twitter", posts_scraped=0, success=True
            )
            return 0

        log(f"Found {len(bookmarks)} Twitter bookmarks from extractor")

        # Extract full thread content in second pass (after collection, before processing)
        # This avoids DOM conflicts during bookmark scrolling
        try:
            if extractor and hasattr(extractor, "extract_threads_second_pass"):
                log("🧵 Starting second pass thread extraction...")
                bookmarks = await extractor.extract_threads_second_pass(bookmarks, max_retries=2)
                log(f"✅ Thread extraction complete: {len(bookmarks)} posts processed")
        except Exception as e:
            logger.warning(f"⚠️ Thread extraction failed, continuing with original posts: {e}")
            # Continue with original bookmarks if thread extraction fails

        # Helper function to check if existing post has full content
        # Cache results to avoid repeated DB queries for the same post
        _full_content_cache = {}
        
        def has_full_content(post_id: str, url: str) -> bool:
            """Check if an existing post has full (non-truncated) content."""
            # Check cache first
            cache_key = post_id or url
            if cache_key in _full_content_cache:
                return _full_content_cache[cache_key]
            
            try:
                # Try to get existing post from database
                existing_post = None
                if db_manager:
                    try:
                        # Try to get by post_id first (most efficient)
                        existing_post = db_manager.get_post_by_id(post_id)
                    except Exception as e:
                        logger.debug(f"Could not get post by ID {post_id}: {e}")
                    
                    # If not found by ID and we have URL, try querying by URL
                    if not existing_post and url:
                        try:
                            # Try to get posts by platform and filter by URL
                            twitter_posts = db_manager.get_posts_by_platform("twitter", limit=1000)
                            for p in twitter_posts:
                                if p.get("url") == url:
                                    existing_post = p
                                    break
                        except Exception as e:
                            logger.debug(f"Could not get post by URL {url}: {e}")
                
                if not existing_post:
                    _full_content_cache[cache_key] = False
                    return False
                
                content = (existing_post.get("content") or "").strip()
                if not content:
                    _full_content_cache[cache_key] = False
                    return False
                
                content_length = len(content)
                content_lower = content.lower()
                content_rstrip = content.rstrip()
                
                # Smart truncation detection - only flag if we're confident it's actually truncated
                # Don't assume posts ending with "..." or "…" are truncated - they might be natural
                
                is_truncated = False
                
                # STRONG indicators of truncation (high confidence - these are definitely truncated)
                # Check for explicit truncation markers (case-insensitive, with or without ellipsis)
                truncation_phrases = [
                    "read more", "show more", "continue reading", 
                    "read more...", "show more...", "continue reading...",
                    "read more…", "show more…", "continue reading…",
                ]
                
                ends_with_truncation_phrase = any(
                    content_lower.endswith(phrase) or content_lower.rstrip().endswith(phrase)
                    for phrase in truncation_phrases
                )
                
                if (
                    # Explicit truncation text (definitely truncated)
                    ends_with_truncation_phrase or
                    # Bracket truncation markers
                    content_rstrip.endswith("[...]") or
                    content_rstrip.endswith("...]") or
                    # Very short content with ellipsis (almost certainly truncated)
                    (content_length < 100 and (content_rstrip.endswith("...") or content_rstrip.endswith("…")))
                ):
                    is_truncated = True
                
                # MEDIUM indicators - only flag if content is suspiciously short
                # If content is long (> 300 chars), ending with "..." is likely natural
                elif content_length < 300:
                    ends_with_ellipsis = content_rstrip.endswith("...") or content_rstrip.endswith("…")
                    
                    if ends_with_ellipsis:
                        # Check if ellipsis appears after proper punctuation (natural usage)
                        # Natural ellipsis often follows sentence-ending punctuation
                        text_before_ellipsis = content_rstrip[:-3] if content_rstrip.endswith("...") else content_rstrip[:-1]
                        
                        # If there's no sentence-ending punctuation before ellipsis, might be truncated
                        # But only if content is also suspiciously short
                        has_sentence_end = any(text_before_ellipsis.rstrip().endswith(p) 
                                             for p in ['.', '!', '?', ')', ']', '}', '"', "'"])
                        
                        # Flag as truncated only if:
                        # - Content is short (< 300 chars)
                        # - Ends with ellipsis
                        # - No sentence-ending punctuation before ellipsis
                        # - Content doesn't look complete
                        if not has_sentence_end and content_length < 250:
                            # Additional check: if last "word" before ellipsis is very short, likely truncated
                            last_word = text_before_ellipsis.split()[-1] if text_before_ellipsis.split() else ""
                            if len(last_word) < 3:  # Very short last word suggests truncation
                                is_truncated = True
                
                # Consider it full if:
                # 1. Length > 500 chars (definitely full)
                # 2. OR length > 200 chars AND not flagged as truncated
                # 3. OR length > 300 chars (even with ellipsis, likely complete)
                is_full = (content_length > 500) or (content_length > 300) or (content_length > 200 and not is_truncated)
                
                # Cache the result
                _full_content_cache[cache_key] = is_full
                return is_full
            except Exception as e:
                logger.debug(f"Error checking full content for {post_id}: {e}")
                # On error, assume not full (allow re-collection to be safe)
                _full_content_cache[cache_key] = False
                return False

        # Filter out existing posts (double-check)
        new_posts = []
        full_content_skipped = 0
        truncated_to_update = 0
        reached_last_collected = False

        for bookmark in bookmarks:
            post_id = str(bookmark.post_id or "")
            url = bookmark.url or ""

            # Normalize post ID for comparison (remove twitter_ prefix if present)
            normalized_post_id = (
                post_id.replace("twitter_", "").replace("Twitter_", "").strip()
            )
            normalized_last_id = (
                str(last_collected_id)
                .replace("twitter_", "")
                .replace("Twitter_", "")
                .strip()
                if last_collected_id
                else None
            )

            # Stop if we reached the last collected post (incremental collection)
            # Check both raw and normalized IDs
            if last_collected_id and (
                post_id == last_collected_id or normalized_post_id == normalized_last_id
            ):
                log(
                    f"✓ Reached last collected post: {last_collected_id} (matched: {post_id})"
                )
                reached_last_collected = True
                break

            # Double-check: Check if post already exists
            if post_id in existing_ids or (existing_urls and url in existing_urls):
                # CRITICAL: Check if this duplicate is the stop post
                # If so, we should stop collection (even though it's a duplicate)
                if last_collected_id and (
                    post_id == last_collected_id
                    or normalized_post_id == normalized_last_id
                ):
                    log(
                        f"✓ Reached last collected post (duplicate): {last_collected_id} (matched: {post_id})"
                    )
                    reached_last_collected = True
                    break

                # Check if post has full content - if truncated, re-collect to update it
                if has_full_content(post_id, url):
                    full_content_skipped += 1
                    log(f"⏭️ Skipping post with full content: {post_id}")
                    continue
                else:
                    # Post exists but is truncated - allow re-collection to update it
                    truncated_to_update += 1
                    log(f"🔄 Re-collecting truncated post: {post_id} (will update with full content)")
                    # Don't skip - allow it to be processed

            new_posts.append(bookmark)

        if full_content_skipped > 0 or truncated_to_update > 0:
            skip_msg = f"📊 Filtered {full_content_skipped} posts with full content (already analyzed)"
            if truncated_to_update > 0:
                skip_msg += f", {truncated_to_update} truncated posts to update (may already have analysis)"
            skip_msg += f", {len(new_posts)} truly new posts to process"
            log(skip_msg)
        log(f"Processing {len(new_posts)} Twitter posts ({len(new_posts) - truncated_to_update} new, {truncated_to_update} updates)")

        successful_count = 0
        dry_run_count = 0
        last_post_id = None
        last_post_url = None

        # Process posts without AI analysis first (collection phase)
        collected_posts = []
        for post_data in new_posts:
            try:
                post_id = str(post_data.post_id or "")

                # Normalize post ID for comparison
                normalized_id = state_manager.normalize_post_id(post_id, "twitter")

                # Double-check: stop if we encounter the last collected ID
                if last_collected_id and normalized_id == last_collected_id:
                    log(
                        f"🛑 Stopped at previously collected post: {post_id} (normalized: {normalized_id})"
                    )
                    break

                # Convert to dictionary format
                # Build safe content with fallbacks to avoid empty payloads
                raw_content = (post_data.content or "").strip()
                title = (getattr(post_data, "title", "") or "").strip()
                url = post_data.url or ""
                # Minimal, readable fallback if text was not captured but we have metadata
                if not raw_content:
                    parts = []
                    if title:
                        parts.append(title)
                    if getattr(post_data, "author", None):
                        parts.append(
                            f"by @{str(getattr(post_data, 'author_handle', '') or '').lstrip('@') or post_data.author}"
                        )
                    if url:
                        parts.append(url)
                    # Include up to 6 hashtags as text if present
                    ht = (
                        list(post_data.hashtags or [])
                        if getattr(post_data, "hashtags", None) is not None
                        else []
                    )
                    if ht:
                        parts.append(
                            "#" + " #".join([str(h).strip("#") for h in ht[:6]])
                        )
                    fallback_text = " \n".join([p for p in parts if p])
                    raw_content = fallback_text.strip()
                # If still no content, skip to avoid DB validation errors
                if not raw_content:
                    log(
                        f"🚫 Skipping Twitter post with no text content (id={post_id or 'unknown'})",
                        "warning",
                    )
                    continue

                MAX_CONTENT_LENGTH = 10000
                post_dict = {
                    "post_id": post_data.post_id,
                    "title": title,  # Some posts might not have title
                    "content": raw_content
                    if len(raw_content) <= MAX_CONTENT_LENGTH
                    else raw_content[:MAX_CONTENT_LENGTH],
                    "url": url,
                    "platform": "twitter",
                    "author": post_data.author,
                    "username": post_data.author_handle,
                    "created_at": post_data.created_at.isoformat()
                    if isinstance(post_data.created_at, datetime)
                    else (post_data.created_at or datetime.now().isoformat()),
                    "collected_at": datetime.now().isoformat(),
                    "hashtags": list(post_data.hashtags or []),
                    "engagement": dict(post_data.engagement or {}),
                    "media_urls": list(post_data.media_urls or []),
                    "post_type": post_data.post_type or "post",
                }

                if dry_run_mode:
                    dry_run_count += 1
                    log(
                        f"[DRY RUN] Would store Twitter post {post_id} ({post_dict.get('url','')})",
                        "info",
                    )
                    continue

                # Store without AI analysis first
                local_stored = db_manager.add_post(post_dict)
                if local_stored:
                    collected_posts.append(post_dict)
                    successful_count += 1

                    # Update last post tracking
                    if post_dict.get("post_id"):
                        last_post_id = normalized_id
                    last_post_url = post_dict.get("url")

                    # Mark post as scraped in state database
                    state_manager.mark_post_scraped(
                        post_id=normalized_id,
                        platform="twitter",
                        url=post_dict.get("url"),
                        title=post_dict.get("title"),
                        author=post_dict.get("author"),
                    )

                    # Add to existing IDs sets
                    if post_dict.get("post_id"):
                        existing_ids.add(str(post_dict["post_id"]))
                    if existing_urls is not None and post_dict.get("url"):
                        existing_urls.add(str(post_dict["url"]))

                    log(f"✅ Collected and tracked post: {post_id}")
                else:
                    log(f"❌ Failed to collect post: {post_id}")

            except Exception as e:
                logger.error(f"Error: {e}")
                log(f"Error collecting Twitter post: {e}", "error")
                continue

        # Update scrape state
        if dry_run_mode:
            log(
                f"🧪 DRY RUN complete - {dry_run_count} Twitter posts would have been stored",
                "info",
            )
            return dry_run_count

        if successful_count:
            state_manager.update_scrape_state(
                platform="twitter",
                last_post_id=last_post_id,
                last_post_url=last_post_url,
                posts_scraped=successful_count,
                success=True,
            )
        else:
            state_manager.update_scrape_state(
                platform="twitter", posts_scraped=0, success=True
            )

        # Calculate breakdown for better logging
        truly_new = successful_count - truncated_to_update
        update_msg = f"Twitter collection completed: {successful_count} posts processed"
        if truncated_to_update > 0:
            update_msg += f" ({truly_new} new, {truncated_to_update} updated)"
        if full_content_skipped > 0:
            update_msg += f" | {full_content_skipped} skipped (already have full content + analysis)"
        log(update_msg, "success")

        return successful_count

    except Exception as e:
        import traceback

        log(f"Twitter collection failed: {e}", "error")
        import logging

        logging.getLogger(__name__).error(
            f"Twitter collection error traceback:\n{traceback.format_exc()}"
        )
        state_manager.update_scrape_state(
            platform="twitter", posts_scraped=0, success=False
        )
        return 0
    finally:
        if extractor is not None:
            try:
                await extractor.close()
            except Exception as e:
                logger.error(f"Error: {e}")
                pass


async def analyze_twitter_posts(db_manager, supabase_manager=None):
    """
    Run AI analysis on collected Twitter posts

    Args:
        db_manager: Database manager instance
        supabase_manager: Optional SupabaseManager instance for cloud sync

    Returns:
        int: Number of posts successfully analyzed
    """
    try:
        # Skip AI analysis if flag is set
        if os.environ.get("SKIP_AI_ANALYSIS", "").lower() in ("true", "1", "yes"):
            log("AI analysis skipped as SKIP_AI_ANALYSIS is set", "info")
            return 0

        # Get unanalyzed posts
        unanalyzed_posts = db_manager.get_unanalyzed_posts("twitter")
        if not unanalyzed_posts:
            log("No unanalyzed Twitter posts found", "info")
            return 0

        log(f"Starting AI analysis on {len(unanalyzed_posts)} Twitter posts...")
        analyzed_count = 0

        # Process each unanalyzed post
        for post_dict in unanalyzed_posts:
            try:
                if await analyze_and_store_post(
                    db_manager, post_dict, supabase_manager
                ):
                    analyzed_count += 1
                    log(f"✅ Analyzed post: {post_dict.get('post_id')}")
                else:
                    log(f"❌ Failed to analyze post: {post_dict.get('post_id')}")
            except Exception as e:
                post_id = post_dict.get("post_id", "unknown")
                log(f"Error analyzing Twitter post {post_id}: {e}", "error")
                import logging
                import traceback

                logging.getLogger(__name__).debug(
                    f"Twitter analysis error for {post_id}:\n{traceback.format_exc()}"
                )
                continue

        log(
            f"AI analysis completed: {analyzed_count}/{len(unanalyzed_posts)} posts analyzed",
            "success",
        )
        return analyzed_count

    except Exception as e:
        log(f"Twitter analysis failed: {e}", "error")
        import logging
        import traceback

        logging.getLogger(__name__).error(
            f"Twitter analysis error traceback:\n{traceback.format_exc()}"
        )
        return 0


async def collect_reddit_bookmarks(
    db_manager, existing_ids: set, existing_urls=None, supabase_manager=None
):
    """
    Collect Reddit saved posts

    Args:
        db_manager: Database manager instance
        existing_ids: Set of existing post IDs to avoid duplicates
        existing_urls: Set of existing URLs to avoid duplicates
        supabase_manager: Optional SupabaseManager instance for cloud sync

    Returns:
        int: Number of new posts collected
    """
    try:
        log("🔍 Starting Reddit bookmark collection...")
        log("USING SUPABASE-FIRST REDDIT COLLECTOR v2")
        try:
            import os

            log(f"collector_path: {__file__}")
        except Exception as e:
            logger.error(f"Error: {e}")
            pass

        # Load collection state and auto-sync if needed
        state_manager = ScrapeStateManager()
        state_manager.sync_state_from_main_db(force=False)  # Auto-recover state

        # Prefer Supabase for last_collected_id
        last_collected_id = None
        last_collected_from_supabase = False
        if supabase_manager:
            try:
                r = (
                    supabase_manager.client.table("posts")
                    .select("post_id")
                    .eq("platform", "reddit")
                    .order("created_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if r.data:
                    last_collected_id = (r.data[0].get("post_id") or "").strip()
                    if last_collected_id and not last_collected_id.startswith("t3_"):
                        last_collected_id = f"t3_{last_collected_id}"
                    last_collected_from_supabase = True
            except Exception as e:
                logger.error(f"Error: {e}")
                log(f"Supabase last_collected lookup failed: {e}", "warning")
        if not last_collected_id:
            last_collected_id = state_manager.get_last_collected_post_id("reddit")

        if last_collected_id:
            log(
                f"🔄 Incremental: stopping at {last_collected_id} (source={'Supabase' if last_collected_from_supabase else 'local'})"
            )
        else:
            log("🆕 Full collection mode")

        # Ensure env is loaded
        load_dotenv()

        # Get Reddit credentials from environment
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "BEYONDLINES:1.0.0")
        reddit_username = os.getenv("REDDIT_USERNAME")
        reddit_password = os.getenv("REDDIT_PASSWORD")
        reddit_access_token = os.getenv("REDDIT_ACCESS_TOKEN")

        if not reddit_client_id or not reddit_client_secret:
            log("Reddit credentials not found in environment variables", "warning")
            state_manager.update_scrape_state(
                platform="reddit", posts_scraped=0, success=False
            )
            return 0

        # Initialize Reddit extractor
        extractor = RedditExtractor(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent,
            username=reddit_username,
            password=reddit_password,
            access_token=reddit_access_token,
        )

        # Collect saved posts with existing IDs to stop early
        log(
            f"Fetching Reddit saved posts (will stop at: {last_collected_id or 'none'})..."
        )
        saved_posts_result = extractor.get_saved_posts(
            existing_ids=existing_ids, limit=100
        )
        if isinstance(saved_posts_result, tuple):
            saved_posts, _ = saved_posts_result
        else:
            saved_posts = saved_posts_result

        if not saved_posts:
            log("No Reddit saved posts found", "info")
            return 0

        log(f"Found {len(saved_posts)} Reddit saved posts")

        # Normalize objects to dicts
        def to_post_dict(post):
            if isinstance(post, dict):
                return post
            return {
                "post_id": getattr(post, "post_id", None),
                "title": getattr(post, "title", ""),
                "content": getattr(post, "content", ""),
                "url": getattr(post, "url", None),
                "platform": getattr(post, "platform", "reddit"),
                "author": getattr(post, "author", None),
                "subreddit": getattr(
                    getattr(post, "metadata", {}), "get", lambda k, d=None: None
                )("subreddit"),
                # Normalize post_type to align with collector expectations
                # Treat SocialPost types "post" and "post_with_comments" as "submission"
                "post_type": (
                    "submission"
                    if getattr(post, "post_type", None)
                    in ("post", "post_with_comments")
                    else getattr(post, "post_type", "submission")
                ),
                "created_at": getattr(post, "created_at", None),
            }

        saved_posts = [to_post_dict(p) for p in saved_posts]

        # Store submissions only by default; optionally include top comments if enabled
        include_comments = os.getenv("REDDIT_INCLUDE_COMMENTS", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        # After normalization above, submissions have post_type == "submission"
        submission_posts = [
            p
            for p in saved_posts
            if (p.get("post_type") or "submission") == "submission"
        ]

        if include_comments:
            # Only fetch comments for posts we are about to save and limit to last 20
            comments_limit = int(os.getenv("REDDIT_COMMENTS_LIMIT", "3"))
            max_comment_targets = int(os.getenv("REDDIT_MAX_COMMENT_TARGETS", "20"))
            comment_posts: List[Dict] = []
            # We'll fetch comments after we compute new_posts below; hold targets here
            pending_comment_targets = []
            # Temporarily stash submission_posts; we'll revisit after new_posts computed
            pass
        else:
            saved_posts = submission_posts

        # Supabase-first existing ids
        supabase_existing_ids = set()
        if supabase_manager:
            try:
                r_all = (
                    supabase_manager.client.table("posts")
                    .select("post_id")
                    .eq("platform", "reddit")
                    .limit(10000)
                    .execute()
                )
                for row in r_all.data or []:
                    pid = (row.get("post_id") or "").strip()
                    if not pid:
                        continue
                    supabase_existing_ids.add(pid)
                    if pid.startswith("t3_"):
                        supabase_existing_ids.add(pid.replace("t3_", ""))
                    else:
                        supabase_existing_ids.add(f"t3_{pid}")
            except Exception as e:
                logger.error(f"Error: {e}")
                log(f"Supabase existing_ids lookup failed: {e}", "warning")
        log(
            f"supabase_existing_ids={len(supabase_existing_ids)} local_existing_ids={len(existing_ids)}"
        )

        def normalize_reddit_id(pid: str):
            pid = (pid or "").strip()
            if not pid:
                return "", ""
            raw = pid.replace("t3_", "")
            full = pid if pid.startswith("t3_") else f"t3_{raw}"
            return raw, full

        # Filter out existing posts and check for stop condition
        new_posts = []
        reached_last_collected = False
        skipped = 0
        for idx, post in enumerate(saved_posts):
            post_id = str(post.get("post_id") or post.get("name") or "")
            url = post.get("url") or ""
            raw_id, full_id = normalize_reddit_id(post_id)
            if idx < 5:
                log(f"scan[{idx}] raw={raw_id} full={full_id} url={(url or '')[:60]}")

            # Stop if we reached the last collected post (incremental collection)
            if last_collected_id and full_id == last_collected_id:
                log(f"🛑 Reached last collected post: {full_id}")
                reached_last_collected = True
                break

            # Supabase-first duplicate check
            if (
                full_id in supabase_existing_ids
                or raw_id in supabase_existing_ids
                or raw_id in existing_ids
                or full_id in existing_ids
                or (existing_urls and url in existing_urls)
            ):
                skipped += 1
                continue

            new_posts.append(post)

        log(f"📋 Processing {len(new_posts)} new Reddit posts (skipped: {skipped})")

        # If comments are enabled, fetch for at most the last 20 new posts
        if include_comments and new_posts:
            try:
                comments_limit = int(os.getenv("REDDIT_COMMENTS_LIMIT", "3"))
                max_comment_targets = int(os.getenv("REDDIT_MAX_COMMENT_TARGETS", "20"))
                comment_targets = new_posts[:max_comment_targets]
                comment_posts: List[Dict] = []
                for p in comment_targets:
                    try:
                        comments = await extractor.get_post_comments(
                            p.get("url") or "", limit=comments_limit
                        )
                        for c in comments:
                            comment_posts.append(
                                {
                                    "post_id": getattr(c, "post_id", None),
                                    "title": getattr(c, "title", ""),
                                    "content": getattr(c, "content", ""),
                                    "url": getattr(c, "url", None),
                                    "platform": "reddit",
                                    "author": getattr(c, "author", None),
                                    "subreddit": getattr(
                                        getattr(c, "metadata", {}),
                                        "get",
                                        lambda k, d=None: None,
                                    )("subreddit"),
                                    "post_type": "comment",
                                    "created_at": getattr(c, "created_at", None),
                                }
                            )
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        log(
                            f"Error fetching comments for {p.get('url')}: {e}",
                            "warning",
                        )
                if comment_posts:
                    new_posts.extend(comment_posts)
                    log(
                        f"🗨️ Included {len(comment_posts)} comments from {min(len(comment_targets), max_comment_targets)} recent posts"
                    )
            except Exception as e:
                logger.error(f"Error: {e}")
                log(f"Comment enrichment failed: {e}", "warning")

        # Process and store new posts (collection-only; no AI analysis here)
        successful_count = 0
        last_post_id = None
        last_post_url = None
        saved_to_supabase = 0
        failed_sync = 0
        for post_data in new_posts:
            try:
                post_id = str(post_data.get("post_id") or post_data.get("name") or "")
                raw_id, full_id = normalize_reddit_id(post_id)

                # Convert to dictionary format
                post_dict = {
                    "post_id": post_data.get("post_id"),
                    "title": post_data.get("title", ""),
                    "content": post_data.get("content", ""),
                    "url": post_data.get("url"),
                    "platform": "reddit",
                    "author": post_data.get("author"),
                    "subreddit": post_data.get("subreddit"),
                    "created_at": post_data.get(
                        "created_at", datetime.now().isoformat()
                    ),
                    "collected_at": datetime.now().isoformat(),
                }

                # Supabase-primary write; local cache is optional and does not advance state on failure
                supabase_ok = False
                if supabase_manager:
                    try:
                        supabase_ok = bool(supabase_manager.insert_post(post_dict))
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        supabase_ok = False

                # Attempt local cache regardless of Supabase status, but do not count as success if Supabase failed
                try:
                    db_manager.add_post(post_dict)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

                if not supabase_ok:
                    failed_sync += 1
                    log(
                        "⚠️ Supabase insert failed; cached locally and will retry on next run"
                    )
                    continue

                # Success path: Supabase accepted the post
                saved_to_supabase += 1
                successful_count += 1

                # Update last post tracking
                if post_dict.get("post_id"):
                    last_post_id = full_id
                    existing_ids.add(raw_id)
                    existing_ids.add(full_id)

                    # Mark post as scraped in state database
                    state_manager.mark_post_scraped(
                        post_id=last_post_id,
                        platform="reddit",
                        url=post_dict.get("url"),
                        title=post_dict.get("title"),
                        author=post_dict.get("author"),
                    )

                    last_post_url = post_dict.get("url") or last_post_url
                    if existing_urls is not None and post_dict.get("url"):
                        existing_urls.add(str(post_dict["url"]))

                    log(f"✅ Saved to Supabase: {last_post_id}")

            except Exception as e:
                post_id = (
                    post_dict.get("post_id", "unknown")
                    if "post_dict" in locals()
                    else "unknown"
                )
                log(f"❌ Error processing Reddit post {post_id}: {e}", "error")
                import logging
                import traceback

                logging.getLogger(__name__).debug(
                    f"Reddit post processing error for {post_id}:\n{traceback.format_exc()}"
                )
                failed_sync += 1
                continue

        if successful_count:
            state_manager.update_scrape_state(
                platform="reddit",
                last_post_id=last_post_id,
                last_post_url=last_post_url,
                posts_scraped=successful_count,
                success=True,
            )
        else:
            state_manager.update_scrape_state(
                platform="reddit", posts_scraped=0, success=True
            )

        log(
            f"Reddit collection completed: {successful_count} new posts (saved_to_supabase={saved_to_supabase}, failed_sync={failed_sync}, skipped={skipped})",
            "success",
        )
        return successful_count

    except Exception as e:
        import traceback

        log(f"Reddit collection failed: {e}", "error")
        import logging

        logging.getLogger(__name__).error(
            f"Reddit collection error traceback:\n{traceback.format_exc()}"
        )
        state_manager.update_scrape_state(
            platform="reddit", posts_scraped=0, success=False
        )
        return 0


async def collect_threads_bookmarks(
    db_manager, existing_ids: set, existing_urls=None, supabase_manager=None
):
    """
    Collect Threads bookmarks

    Args:
        db_manager: Database manager instance
        existing_ids: Set of existing post IDs to avoid duplicates
        existing_urls: Set of existing URLs to avoid duplicates
        supabase_manager: Optional SupabaseManager instance for cloud sync

    Returns:
        int: Number of new posts collected
    """
    extractor = None
    try:
        # Load collection state and auto-sync if needed
        state_manager = ScrapeStateManager()
        state_manager.sync_state_from_main_db(force=False)  # Auto-recover state

        dry_run_mode = os.getenv("COLLECTION_DRY_RUN", "").lower() in (
            "1",
            "true",
            "yes",
        )
        if dry_run_mode:
            log(
                "🧪 COLLECTION_DRY_RUN enabled - Threads posts will NOT be written",
                "warning",
            )

        threads_force_full = os.getenv("THREADS_FORCE_FULL", "").lower() in (
            "1",
            "true",
            "yes",
        )

        last_collected_id = state_manager.get_last_collected_post_id("threads")
        if last_collected_id:
            log(f"🔄 Incremental: stopping at {last_collected_id}")
        else:
            log("🆕 Full collection mode")

        if threads_force_full:
            log(
                "⚠️ Force full Threads collection enabled - ignoring existing IDs and stop_at_post_id",
                "warning",
            )
            existing_ids.clear()
            last_collected_id = None

        # Get Threads credentials from environment
        threads_username = os.getenv("THREADS_USERNAME")
        threads_password = os.getenv("THREADS_PASSWORD")
        threads_cookies_file = os.getenv("THREADS_COOKIES_FILE")

        if not threads_username:
            log("Threads username not found in environment variables", "warning")
            state_manager.update_scrape_state(
                platform="threads", posts_scraped=0, success=False
            )
            return 0

        # Initialize Threads extractor
        extractor = ThreadsExtractor()

        # Authenticate if credentials provided
        if threads_username and threads_password:
            # Use environment variable for cookie file path
            # Default to cookies/threads_cookies.json (where the file actually exists)
            cookies_file = threads_cookies_file or os.getenv("THREADS_COOKIES_PATH", "cookies/threads_cookies.json")

            # Check if file exists
            if not Path(cookies_file).exists():
                logger.warning(f"Threads cookies file not found at: {cookies_file}")
                cookies_file = None

            auth_success = await extractor.authenticate(
                username=threads_username,
                password=threads_password,
                cookies_path=cookies_file,
            )
            if not auth_success:
                log("Threads authentication failed", "warning")
                state_manager.update_scrape_state(
                    platform="threads", posts_scraped=0, success=False
                )
                return 0

        normalized_threads_handle = (
            str(threads_username or "").strip().lstrip("@").lower()
        )

        # Collect saved posts
        log("Fetching Threads saved posts...")
        # Use default limit (no artificial test limits)
        scrape_limit = 50
        saved_posts = await extractor.get_saved_posts(
            username=threads_username,
            password=threads_password,
            limit=scrape_limit,
            stop_at_post_id=last_collected_id,
            existing_ids=existing_ids,
        )

        if not saved_posts:
            log("No Threads saved posts found", "info")
            # Diagnostic: check if it's an authentication issue
            if not threads_username:
                log("⚠️ THREADS_USERNAME not set - authentication may have failed", "warning")
            # Suggest enabling DOM fallback if API method failed
            if os.getenv("THREADS_DOM_FALLBACK", "false").lower() not in ("1", "true", "yes"):
                log("💡 Tip: If you have saved posts but none were found, try setting THREADS_DOM_FALLBACK=true", "info")
            return 0

        log(f"Found {len(saved_posts)} Threads saved posts")

        # Filter out existing posts and check for stop condition
        new_posts = []
        reached_last_collected = False
        consecutive_seen = 0

        for post in saved_posts:
            post_id = str(post.post_id or "")
            url = post.url or ""

            # Skip attachments or malformed entries that use placeholder IDs
            if not post_id or post_id.lower() == "media" or url.endswith("/media"):
                log(
                    f"🚫 Skipping placeholder attachment post (id={post_id or 'none'}, url={url})"
                )
                continue

            # Normalize post ID for comparison
            normalized_id = state_manager.normalize_post_id(post_id, "threads")

            # Check if post already exists BEFORE processing
            if (
                post_id in existing_ids
                or normalized_id in existing_ids
                or (existing_urls and url in existing_urls)
            ):
                consecutive_seen += 1
                log(f"⏭️ Skipping duplicate (seen in DB): id={post_id} url={url}")
                # If we see duplicates back-to-back, assume we've reached the previously scraped range
                if consecutive_seen >= 2 and len(new_posts) > 0:
                    log(
                        "🛑 Encountered consecutive duplicates after new items → stopping scroll (incremental)"
                    )
                    break
                continue

            # Stop if we reached the last collected post (incremental collection)
            if last_collected_id and normalized_id == last_collected_id:
                log(
                    f"🛑 Reached last collected post: {post_id} (normalized: {normalized_id})"
                )
                reached_last_collected = True
                break

            # New post found → reset duplicate streak
            consecutive_seen = 0
            new_posts.append(post)

        log(f"📋 Processing {len(new_posts)} new Threads posts (after filtering {len(saved_posts) - len(new_posts)} duplicates/existing)")
        
        # Diagnostic: if we had posts but all were filtered, log why
        if saved_posts and not new_posts:
            log(
                f"⚠️ All {len(saved_posts)} saved posts were filtered out. "
                f"This could mean:\n"
                f"  - All posts already exist in database\n"
                f"  - All posts were self-authored (your own posts)\n"
                f"  - Reached last_collected_id (incremental mode)\n"
                f"  - Duplicate detection is too aggressive",
                "warning"
            )

        # Process and store new posts
        successful_count = 0
        dry_run_count = 0
        last_post_id = None
        last_post_url = None

        # Helper function to detect language
        def detect_language(text: str) -> str:
            """Detect if content is primarily Russian or English"""
            if not text:
                return "en"

            # Count Cyrillic characters (Russian)
            russian_chars = sum(1 for c in text if "\u0400" <= c <= "\u04FF")
            # Count Latin characters (English)
            latin_chars = sum(1 for c in text if c.isalpha() and ord(c) < 128)

            total_letters = russian_chars + latin_chars

            if total_letters == 0:
                return "en"  # Default to English if no letters

            russian_ratio = russian_chars / total_letters

            # If more than 30% of letters are Cyrillic, it's Russian
            if russian_ratio > 0.3:
                return "ru"
            else:
                return "en"

        for post_data in new_posts:
            try:
                post_id = str(post_data.post_id or "")
                content = post_data.content or ""
                author_handle = (
                    str(getattr(post_data, "author_handle", "") or "")
                    .strip()
                    .lstrip("@")
                    .lower()
                )

                if (
                    normalized_threads_handle
                    and author_handle
                    and author_handle == normalized_threads_handle
                ):
                    log(
                        f"⏭️ Skipping self-authored Threads post {post_id} (@{author_handle})",
                        "info",
                    )
                    continue

                # Normalize post ID
                normalized_id = state_manager.normalize_post_id(post_id, "threads")

                # Convert to dictionary format
                post_dict = {
                    "post_id": post_data.post_id,
                    "title": getattr(post_data, "title", ""),
                    "content": content,
                    "url": post_data.url,
                    "platform": "threads",
                    "author": post_data.author,
                    "author_handle": getattr(post_data, "author_handle", None),
                    "language": detect_language(content),
                    "created_at": post_data.created_at.isoformat()
                    if post_data.created_at
                    else datetime.now().isoformat(),
                    # Optional enrichments when available (ensure JSON-serializable)
                    "hashtags": list(getattr(post_data, "hashtags", []) or []),
                    "media_urls": list(getattr(post_data, "media_urls", []) or []),
                    "post_type": getattr(post_data, "post_type", "post"),
                    "is_saved": True,
                }

                if dry_run_mode:
                    dry_run_count += 1
                    log(
                        f"[DRY RUN] Would store Threads post {post_id} ({post_dict.get('url','')})",
                        "info",
                    )
                    continue

                # Remove any keys with None or empty dict values to keep payload clean
                post_dict = {
                    k: v for k, v in post_dict.items() if v is not None and v != {}
                }

                # REMOVED: DOM refresh logic to prevent double-scraping
                # The extractor already does full content extraction, no need for additional refresh

                # Store without AI analysis
                supabase_ok = True
                if supabase_manager:
                    try:
                        supabase_result = supabase_manager.insert_post(post_dict)
                        if supabase_result:
                            supabase_ok = True
                        elif post_dict.get(
                            "url"
                        ) and supabase_manager.check_duplicate_by_url(post_dict["url"]):
                            supabase_ok = True
                            log(
                                "ℹ️ Duplicate already exists in Supabase; skipping insert"
                            )
                        else:
                            supabase_ok = False
                    except Exception as supabase_error:
                        logger.error(f"Error: {supabase_error}")
                        log(f"⚠️ Supabase insert exception: {supabase_error}")
                        if post_dict.get(
                            "url"
                        ) and supabase_manager.check_duplicate_by_url(post_dict["url"]):
                            supabase_ok = True
                            log("ℹ️ Duplicate already in Supabase; marking as handled")
                        else:
                            supabase_ok = False

                try:
                    db_manager.add_post(post_dict)
                except Exception as e:
                    logger.error(f"Error: {e}")
                    pass

                if not supabase_ok:
                    log(
                        "⚠️ Supabase insert failed; cached locally and will retry on next run"
                    )
                    continue

                successful_count += 1

                # Update last post tracking
                if post_dict.get("post_id"):
                    last_post_id = normalized_id
                    existing_ids.add(str(post_dict["post_id"]))
                    existing_ids.add(normalized_id)  # Also add normalized version
                    # Mark post as scraped in state database
                    state_manager.mark_post_scraped(
                        post_id=normalized_id,
                        platform="threads",
                        url=post_dict.get("url"),
                        title=post_dict.get("title"),
                        author=post_dict.get("author"),
                    )

                last_post_url = post_dict.get("url") or last_post_url
                if existing_urls is not None and post_dict.get("url"):
                    existing_urls.add(str(post_dict["url"]))

                log(f"✅ Collected and tracked Threads post: {post_id}")

            except Exception as e:
                post_id = (
                    post_dict.get("post_id", "unknown")
                    if "post_dict" in locals()
                    else "unknown"
                )
                log(f"❌ Error processing Threads post {post_id}: {e}", "error")
                import logging
                import traceback

                logging.getLogger(__name__).debug(
                    f"Threads post processing error for {post_id}:\n{traceback.format_exc()}"
                )
                continue

        if dry_run_mode:
            log(
                f"🧪 DRY RUN complete - {dry_run_count} Threads posts would have been stored",
                "info",
            )
            return dry_run_count

        if successful_count:
            state_manager.update_scrape_state(
                platform="threads",
                last_post_id=last_post_id,
                last_post_url=last_post_url,
                posts_scraped=successful_count,
                success=True,
            )
        else:
            state_manager.update_scrape_state(
                platform="threads", posts_scraped=0, success=True
            )

        log(f"Threads collection completed: {successful_count} new posts", "success")
        return successful_count

    except Exception as e:
        import traceback

        log(f"Threads collection failed: {e}", "error")
        import logging

        logging.getLogger(__name__).error(
            f"Threads collection error traceback:\n{traceback.format_exc()}"
        )
        state_manager.update_scrape_state(
            platform="threads", posts_scraped=0, success=False
        )
        return 0
    finally:
        if extractor is not None:
            try:
                await extractor.close()
            except Exception as e:
                logger.error(f"Error: {e}")
                pass


async def analyze_threads_posts(db_manager, supabase_manager=None):
    """
    Run AI analysis on collected Threads posts
    """
    try:
        # Global skip via env
        if os.environ.get("SKIP_AI_ANALYSIS", "").lower() in ("true", "1", "yes"):
            log("AI analysis skipped as SKIP_AI_ANALYSIS is set", "info")
            return 0

        # Get unanalyzed posts (support multiple manager interfaces)
        unanalyzed_posts = []
        try:
            # Preferred signature: limit, platforms
            if hasattr(db_manager, "get_unanalyzed_posts"):
                try:
                    unanalyzed_posts = db_manager.get_unanalyzed_posts(
                        limit=1000, platforms=["threads"]
                    )
                except TypeError as type_error:
                    logger.error(f"Error: {type_error}")
                    # Fallback older signature
                    unanalyzed_posts = db_manager.get_unanalyzed_posts("threads")
        except Exception as e:
            import logging

            logging.getLogger(__name__).debug(
                f"Failed to get unanalyzed Threads posts from db_manager: {e}"
            )
            pass
        if not unanalyzed_posts:
            try:
                from src.services.new_database_manager import NewDatabaseManager

                unanalyzed_posts = NewDatabaseManager().get_unanalyzed_posts(
                    limit=1000, platforms=["threads"]
                )
            except Exception as e:
                import logging

                logging.getLogger(__name__).debug(
                    f"Failed to get unanalyzed Threads posts from NewDatabaseManager: {e}"
                )
                unanalyzed_posts = []
        if not unanalyzed_posts:
            log("No unanalyzed Threads posts found", "info")
            return 0

        log(f"Starting AI analysis on {len(unanalyzed_posts)} Threads posts...")
        analyzed_count = 0

        for post_dict in unanalyzed_posts:
            try:
                if await analyze_and_store_post(
                    db_manager, post_dict, supabase_manager
                ):
                    analyzed_count += 1
                    log(f"✅ Analyzed post: {post_dict.get('post_id')}")
                else:
                    log(f"❌ Failed to analyze post: {post_dict.get('post_id')}")
            except Exception as e:
                post_id = post_dict.get("post_id", "unknown")
                log(f"Error analyzing Threads post {post_id}: {e}", "error")
                import logging
                import traceback

                logging.getLogger(__name__).debug(
                    f"Threads analysis error for {post_id}:\n{traceback.format_exc()}"
                )
                continue

        log(
            f"AI analysis completed: {analyzed_count}/{len(unanalyzed_posts)} posts analyzed",
            "success",
        )
        return analyzed_count
    except Exception as e:
        log(f"Threads analysis failed: {e}", "error")
        import logging
        import traceback

        logging.getLogger(__name__).error(
            f"Threads analysis error traceback:\n{traceback.format_exc()}"
        )
        return 0
