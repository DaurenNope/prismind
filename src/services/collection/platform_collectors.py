#!/usr/bin/env python3
"""
Platform-specific collectors for Twitter, Reddit, and Threads
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from pathlib import Path

# Core imports
from src.core.extraction.social_extractor_base import SocialPost
from src.core.extraction.reddit_extractor import RedditExtractor
from src.core.extraction.twitter_extractor_playwright import TwitterExtractorPlaywright
from src.core.extraction.threads_extractor import ThreadsExtractor
from src.scrape_state_manager import ScrapeStateManager

# Analysis import
from src.services.analysis.post_analyzer import analyze_and_store_post, log
from dotenv import load_dotenv
import os

load_dotenv()


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
        
        last_collected_id = state_manager.get_last_collected_post_id("twitter")

        if last_collected_id:
            log(f"🔄 Incremental: stopping at {last_collected_id}")
        else:
            log("🆕 Full collection mode")

        twitter_username = os.getenv("TWITTER_USERNAME")
        twitter_password = os.getenv("TWITTER_PASSWORD")
        cookie_path_env = os.getenv("TWITTER_COOKIE_FILE")

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

        extractor = TwitterExtractorPlaywright(
            username=twitter_username,
            password=twitter_password,
            cookie_file=str(cookie_path) if cookie_path else None,
        )

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

        # Collect bookmarks - pass existing IDs to extractor to skip during collection
        log("Fetching Twitter bookmarks...")
        bookmarks = await extractor.get_saved_posts(
            limit=50, 
            skip_cached_ids=existing_ids,
            stop_at_post_id=last_collected_id
        )

        if not bookmarks:
            log("No Twitter bookmarks found after authentication", "warning")
            state_manager.update_scrape_state(
                platform="twitter", posts_scraped=0, success=True
            )
            return 0

        log(f"Found {len(bookmarks)} Twitter bookmarks")

        # Filter out existing posts (double-check)
        new_posts = []
        reached_last_collected = False

        for bookmark in bookmarks:
            post_id = str(bookmark.post_id or "")
            url = bookmark.url or ""

            # Stop if we reached the last collected post (incremental collection)
            if last_collected_id and post_id == last_collected_id:
                log(f"✓ Reached last collected post: {last_collected_id}")
                reached_last_collected = True
                break

            # Double-check: Check if post already exists
            if post_id in existing_ids:
                log(f"Skipping duplicate post ID: {post_id}")
                continue

            if existing_urls and url in existing_urls:
                log(f"Skipping duplicate post URL: {url}")
                continue

            new_posts.append(bookmark)

        log(f"Processing {len(new_posts)} new Twitter posts")

        successful_count = 0
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
                    log(f"🛑 Stopped at previously collected post: {post_id} (normalized: {normalized_id})")
                    break

                # Convert to dictionary format
                post_dict = {
                    "post_id": post_data.post_id,
                    "title": getattr(post_data, 'title', ''),  # Some posts might not have title
                    "content": post_data.content,
                    "url": post_data.url,
                    "platform": "twitter",
                    "author": post_data.author,
                    "username": post_data.author_handle,
                    "created_at": post_data.created_at.isoformat() if isinstance(post_data.created_at, datetime) else post_data.created_at,
                    "collected_at": datetime.now().isoformat(),
                    "hashtags": post_data.hashtags,
                    "engagement": post_data.engagement,
                    "media_urls": post_data.media_urls,
                    "post_type": post_data.post_type
                }

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
                        author=post_dict.get("author")
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
                log(f"Error collecting Twitter post: {e}", "error")
                continue

        # Update scrape state
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

        log(f"Twitter collection completed: {successful_count} new posts", "success")
        
        return successful_count

    except Exception as e:
        log(f"Twitter collection failed: {e}", "error")
        state_manager.update_scrape_state(
            platform="twitter", posts_scraped=0, success=False
        )
        return 0
    finally:
        if extractor is not None:
            try:
                await extractor.close()
            except Exception:
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
                log(f"Error analyzing Twitter post {post_dict.get('post_id')}: {e}", "error")
                continue
                
        log(f"AI analysis completed: {analyzed_count}/{len(unanalyzed_posts)} posts analyzed", "success")
        return analyzed_count
        
    except Exception as e:
        log(f"Twitter analysis failed: {e}", "error")
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
        
        # Load collection state and auto-sync if needed
        state_manager = ScrapeStateManager()
        state_manager.sync_state_from_main_db(force=False)  # Auto-recover state
        
        last_collected_id = state_manager.get_last_collected_post_id("reddit")

        if last_collected_id:
            log(f"🔄 Incremental: stopping at {last_collected_id}")
        else:
            log("🆕 Full collection mode")
        
        # Ensure env is loaded
        load_dotenv()

        # Get Reddit credentials from environment
        reddit_client_id = os.getenv("REDDIT_CLIENT_ID")
        reddit_client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        reddit_user_agent = os.getenv("REDDIT_USER_AGENT", "PrisMind:1.0.0")
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
        log(f"Fetching Reddit saved posts (will stop at: {last_collected_id or 'none'})...")
        saved_posts_result = extractor.get_saved_posts(
            existing_ids=existing_ids,
            limit=100
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
                "post_type": getattr(post, "post_type", "submission"),
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
        submission_posts = [
            p
            for p in saved_posts
            if (p.get("post_type") or "submission") == "submission"
        ]

        if include_comments:
            comments_limit = int(os.getenv("REDDIT_COMMENTS_LIMIT", "3"))
            comment_posts: List[Dict] = []
            for p in submission_posts:
                try:
                    comments = await extractor.get_post_comments(
                        p.get("url") or "", limit=comments_limit
                    )
                    # Normalize comment SocialPost objects to dicts
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
                    log(f"Error fetching comments for {p.get('url')}: {e}", "warning")
            saved_posts = submission_posts + comment_posts
        else:
            saved_posts = submission_posts

        # Filter out existing posts and check for stop condition
        new_posts = []
        reached_last_collected = False
        
        for post in saved_posts:
            post_id = str(post.get("post_id") or "")
            url = post.get("url") or ""
            
            # Normalize post ID for comparison
            normalized_id = state_manager.normalize_post_id(post_id, "reddit")

            # Stop if we reached the last collected post (incremental collection)
            if last_collected_id and normalized_id == last_collected_id:
                log(f"🛑 Reached last collected post: {post_id} (normalized: {normalized_id})")
                reached_last_collected = True
                break

            # Check if post already exists
            if post_id in existing_ids or normalized_id in existing_ids:
                log(f"⏭️ Skipping duplicate post ID: {post_id}")
                continue

            if existing_urls and url in existing_urls:
                log(f"⏭️ Skipping duplicate post URL: {url}")
                continue

            new_posts.append(post)

        log(f"📋 Processing {len(new_posts)} new Reddit posts")

        # Process and store new posts
        successful_count = 0
        last_post_id = None
        last_post_url = None
        for post_data in new_posts:
            try:
                post_id = str(post_data.get("post_id") or "")
                
                # Normalize post ID
                normalized_id = state_manager.normalize_post_id(post_id, "reddit")
                
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

                # Analyze and store
                if await analyze_and_store_post(
                    db_manager, post_dict, supabase_manager
                ):
                    successful_count += 1
                    
                    # Update last post tracking
                    if post_dict.get("post_id"):
                        last_post_id = normalized_id
                        existing_ids.add(str(post_dict["post_id"]))
                        existing_ids.add(normalized_id)  # Also add normalized version
                        
                        # Mark post as scraped in state database
                        state_manager.mark_post_scraped(
                            post_id=normalized_id,
                            platform="reddit",
                            url=post_dict.get("url"),
                            title=post_dict.get("title"),
                            author=post_dict.get("author"),
                        )
                        
                    last_post_url = post_dict.get("url") or last_post_url
                    if existing_urls is not None and post_dict.get("url"):
                        existing_urls.add(str(post_dict["url"]))
                    
                    log(f"✅ Collected and tracked Reddit post: {post_id}")

            except Exception as e:
                log(f"❌ Error processing Reddit post: {e}", "error")
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

        log(f"Reddit collection completed: {successful_count} new posts", "success")
        return successful_count

    except Exception as e:
        log(f"Reddit collection failed: {e}", "error")
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
        
        last_collected_id = state_manager.get_last_collected_post_id("threads")

        if last_collected_id:
            log(f"🔄 Incremental: stopping at {last_collected_id}")
        else:
            log("🆕 Full collection mode")

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
            cookies_file = threads_cookies_file or "config/threads_cookies.json"
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

        # Collect saved posts
        log("Fetching Threads saved posts...")
        saved_posts = await extractor.get_saved_posts()

        if not saved_posts:
            log("No Threads saved posts found", "info")
            return 0

        log(f"Found {len(saved_posts)} Threads saved posts")

        # Filter out existing posts and check for stop condition
        new_posts = []
        reached_last_collected = False
        
        for post in saved_posts:
            post_id = str(post.get("post_id", ""))
            url = post.get("url", "")
            
            # Normalize post ID for comparison
            normalized_id = state_manager.normalize_post_id(post_id, "threads")

            # Stop if we reached the last collected post (incremental collection)
            if last_collected_id and normalized_id == last_collected_id:
                log(f"🛑 Reached last collected post: {post_id} (normalized: {normalized_id})")
                reached_last_collected = True
                break

            # Check if post already exists
            if post_id in existing_ids or normalized_id in existing_ids:
                log(f"⏭️ Skipping duplicate post ID: {post_id}")
                continue

            if existing_urls and url in existing_urls:
                log(f"⏭️ Skipping duplicate post URL: {url}")
                continue

            new_posts.append(post)

        log(f"📋 Processing {len(new_posts)} new Threads posts")

        # Process and store new posts
        successful_count = 0
        last_post_id = None
        last_post_url = None
        for post_data in new_posts:
            try:
                post_id = str(post_data.get("post_id", ""))
                
                # Normalize post ID
                normalized_id = state_manager.normalize_post_id(post_id, "threads")
                
                # Convert to dictionary format
                post_dict = {
                    "post_id": post_data.get("post_id"),
                    "title": post_data.get("title", ""),
                    "content": post_data.get("content", ""),
                    "url": post_data.get("url"),
                    "platform": "threads",
                    "author": post_data.get("author"),
                    "username": post_data.get("username"),
                    "created_at": post_data.get(
                        "created_at", datetime.now().isoformat()
                    ),
                    "collected_at": datetime.now().isoformat(),
                }

                # Analyze and store
                if await analyze_and_store_post(
                    db_manager, post_dict, supabase_manager
                ):
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
                log(f"❌ Error processing Threads post: {e}", "error")
                continue

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
        log(f"Threads collection failed: {e}", "error")
        state_manager.update_scrape_state(
            platform="threads", posts_scraped=0, success=False
        )
        return 0
    finally:
        if extractor is not None:
            try:
                await extractor.close()
            except Exception:
                pass
