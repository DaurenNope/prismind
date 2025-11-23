import json
import logging
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import dns.resolver
import praw
import prawcore
import requests
import urllib3
from playwright.async_api import async_playwright
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .social_extractor_base import SocialExtractorBase, SocialPost

logger = logging.getLogger(__name__)
try:
    # Optional universal fallback
    from src.domain.collection import UniversalCollector  # type: ignore

    universal_collector = UniversalCollector  # type: ignore
except Exception:
    universal_collector = None  # type: ignore

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RedditExtractor(SocialExtractorBase):
    """Extract saved posts and comments from Reddit with universal fallback"""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str,
        username: str = None,
        password: str = None,
        access_token: str = None,
        refresh_token: str = None,
        enable_screenshots: bool = False,
    ):
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.username = username
        self.password = password
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.reddit = None
        self.read_only_mode = not (username and password) and not access_token
        self.enable_screenshots = enable_screenshots

        # Initialize universal collector for fallback (optional)
        self.universal_collector = (
            universal_collector() if universal_collector else None
        )

        # Screenshot configuration
        self.screenshot_dir = Path("screenshots/reddit")
        if self.enable_screenshots:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        # Configure session with retries
        self.session = self._create_retry_session()

        # Safety config
        self._load_collection_safety_config()

    def _load_collection_safety_config(self):
        """Load optional jitter/rate safety settings from config/collection.json."""
        try:
            cfg_path = Path("config/collection.json")
            self.reddit_cfg = {}
            if cfg_path.exists():
                with open(cfg_path, "r") as f:
                    data = json.load(f)
                    self.reddit_cfg = data.get("reddit", {}) or {}
            jitter = self.reddit_cfg.get("jitter_ms") or [300, 1200]
            if isinstance(jitter, list) and len(jitter) == 2:
                self._jitter_low, self._jitter_high = int(jitter[0]), int(jitter[1])
            else:
                self._jitter_low, self._jitter_high = 300, 1200
            self._requests_per_hour_cap = int(
                self.reddit_cfg.get("requests_per_hour_cap", 60)
            )
            self._processed_counter = 0
        except Exception:
            self._jitter_low, self._jitter_high = 300, 1200
            self._requests_per_hour_cap = 60
            self._processed_counter = 0

    def _jitter_sleep(self, extra_ms: int = 0):
        try:
            delay_ms = random.randint(self._jitter_low, self._jitter_high)
            time.sleep((delay_ms + max(0, extra_ms)) / 1000)
        except Exception:
            time.sleep(0.3)

    def _create_retry_session(self, retries=5, backoff_factor=1.0) -> requests.Session:
        """Create a requests session with retry logic and improved timeouts."""
        session = requests.Session()

        # More aggressive retry configuration
        retry = Retry(
            total=retries,
            backoff_factor=backoff_factor,
            status_forcelist=[500, 502, 503, 504, 403, 429, 408, 407],
            allowed_methods=frozenset(["GET", "POST", "PUT", "DELETE"]),
            respect_retry_after_header=True,
        )

        # Configure connection pooling
        adapter = HTTPAdapter(
            max_retries=retry, pool_connections=10, pool_maxsize=10, pool_block=False
        )

        # Mount the adapter with retry logic
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default timeout and disable SSL verification
        session.verify = False
        session.timeout = (20, 45)  # Increased timeouts: 20s connect, 45s read

        # Add default headers
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Host": "oauth.reddit.com",  # Always use oauth.reddit.com as host header
            }
        )

        return session

    def _resolve_reddit_domains(self) -> Dict[str, str]:
        """Resolve Reddit domains using Google's public DNS."""
        domains = {
            "www": "www.reddit.com",
            "oauth": "oauth.reddit.com",
            "api": "api.reddit.com",
        }

        resolved = {}
        for name, domain in domains.items():
            try:
                # Use Google's public DNS
                resolver = dns.resolver.Resolver()
                resolver.nameservers = ["8.8.8.8", "8.8.4.4"]  # Google's public DNS

                # Get A records
                answers = resolver.resolve(domain, "A")
                ips = [str(ip) for ip in answers]
                resolved[domain] = ips[0]  # Use first IP
                logger.info(f"✅ Resolved {domain} to {ips[0]}")

            except Exception as e:
                logger.error(f"❌ Failed to resolve {domain}: {e}")

        return resolved

    def _test_reddit_connection(self) -> Tuple[bool, str]:
        """Test connection to Reddit's API endpoints."""
        # First try to resolve domains
        resolved_ips = self._resolve_reddit_domains()

        # Prepare endpoints to test
        endpoints = []

        # Add direct IPs if we resolved them
        if "www.reddit.com" in resolved_ips:
            endpoints.append(f"https://{resolved_ips['www.reddit.com']}")
        if "oauth.reddit.com" in resolved_ips:
            endpoints.append(f"https://{resolved_ips['oauth.reddit.com']}")

        # Always try the standard domains as fallback
        endpoints.extend(
            [
                "https://www.reddit.com",
                "https://oauth.reddit.com",
                "https://api.reddit.com",
                "https://151.101.1.140",  # Known Reddit IPs as last resort
                "https://151.101.129.140",
            ]
        )

        # Remove duplicates while preserving order
        seen = set()
        endpoints = [url for url in endpoints if not (url in seen or seen.add(url))]

        logger.debug("🔍 Testing Reddit endpoints:", ", ".join(endpoints))

        for url in endpoints:
            try:
                # Skip IP addresses in the Host header to avoid SSL errors
                host_header = None
                if url.startswith("https://") and not url[8:].startswith(
                    tuple("0123456789")
                ):
                    host_header = url[8:].split("/")[0]

                response = self.session.get(
                    url,
                    timeout=10,
                    headers={"Host": host_header} if host_header else {},
                )
                if response.status_code == 200:
                    return True, f"Successfully connected to {url}"
            except requests.exceptions.SSLError as e:
                logger.error(f"⚠️ SSL Error with {url}: {e}")
                continue
            except requests.exceptions.RequestException as e:
                logger.error(f"⚠️ Connection error with {url}: {e}")
                continue

        return False, "Failed to connect to any Reddit endpoint"

    def authenticate(self) -> bool:
        """Authenticate with Reddit API with enhanced error handling and retries."""
        max_retries = 5  # Increased max retries
        retry_delay = 3  # Increased initial delay to 3 seconds

        for attempt in range(max_retries):
            try:
                # Try OAuth2 first if we have a refresh token
                if self.refresh_token:
                    try:
                        print(
                            f"🔑 Attempt {attempt + 1}/{max_retries}: OAuth2 authentication..."
                        )
                        self.reddit = praw.Reddit(
                            client_id=self.client_id,
                            client_secret=self.client_secret,
                            refresh_token=self.refresh_token,
                            user_agent=self.user_agent,
                            requestor_kwargs={"session": self.session, "timeout": 30},
                            api_url="https://151.101.1.140/api/v1",
                            oauth_url="https://151.101.1.140/api/v1/access_token",
                            reddit_url="https://151.101.1.140",
                            check_for_async=False,
                        )
                        # Test the connection with a simple API call
                        self.reddit.user.me()
                        logger.info("✅ OAuth2 authentication successful")
                        return True
                    except Exception as e:
                        logger.error(f"⚠️ OAuth2 attempt {attempt + 1} failed: {e}")
                        if "invalid_grant" in str(e).lower():
                            logger.warning("⚠️ Refresh token may be invalid or expired")
                            break  # No point in retrying with invalid token

                # Fall back to password auth if username/password are provided
                if self.username and self.password:
                    try:
                        print(
                            f"🔑 Attempt {attempt + 1}/{max_retries}: Password authentication..."
                        )
                        self.reddit = praw.Reddit(
                            client_id=self.client_id,
                            client_secret=self.client_secret,
                            username=self.username,
                            password=self.password,
                            user_agent=self.user_agent,
                            requestor_kwargs={"session": self.session, "timeout": 30},
                            check_for_async=False,
                        )
                        # Test the connection with a simple API call
                        self.reddit.user.me()
                        self.read_only_mode = (
                            False  # Set read_only_mode to False after successful auth
                        )
                        logger.info("✅ Password authentication successful")
                        return True
                    except Exception as e:
                        print(
                            f"⚠️ Password authentication attempt {attempt + 1} failed: {e}"
                        )

                # If we get here, all auth methods have been tried and failed
                if attempt < max_retries - 1:
                    logger.warning(f"🔄 Waiting {retry_delay} seconds before retry...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff

            except Exception as e:
                print(
                    f"⚠️ Unexpected error during authentication attempt {attempt + 1}: {e}"
                )
                if attempt == max_retries - 1:
                    logger.error("❌ All authentication attempts failed")

        # If all else fails, try read-only mode
        logger.warning("⚠️ Falling back to read-only mode...")
        return self._fallback_to_readonly()

    def _fallback_to_readonly(self) -> bool:
        """Fallback to read-only mode when OAuth fails"""
        try:
            logger.info("🔄 Falling back to read-only mode...")
            try:
                # First try with standard endpoint
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    requestor_kwargs={
                        "session": self.session,
                        "api_url": "https://151.101.1.140/api/v1",
                        "oauth_url": "https://151.101.1.140/api/v1/access_token",
                        "reddit_url": "https://151.101.1.140",
                        "ratelimit_seconds": 5,
                        "min_delay": 1.0,
                    },
                    check_for_async=False,
                )
                # Test with a simple API call
                subreddit = self.reddit.subreddit("test")
                subreddit.display_name  # This will fail if auth is bad
                logger.info(
                    "✅ Reddit read-only authentication successful with direct IP"
                )
                return True
            except Exception as direct_ip_error:
                print(
                    f"⚠️ Direct IP connection failed, trying standard endpoint: {direct_ip_error}"
                )
                # Fall back to standard endpoint
                self.reddit = praw.Reddit(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    user_agent=self.user_agent,
                    check_for_async=False,
                )
                subreddit = self.reddit.subreddit("test")
                subreddit.display_name
                print(
                    "✅ Reddit read-only authentication successful with standard endpoint"
                )
                return True
        except Exception as e:
            logger.error(f"❌ Reddit read-only auth failed: {e}")
            return False

    def get_saved_posts(
        self,
        limit: int = 100,
        max_retries: int = 3,
        after: str = None,
        existing_ids: set = None,
    ) -> List[SocialPost]:
        """Get saved posts and comments from Reddit with retries and pagination.

        Args:
            limit: Maximum number of posts to return
            max_retries: Maximum number of retry attempts
            after: Fullname of the next data block to return (for pagination)
            existing_ids: Set of post IDs that already exist in the database

        Returns:
            Tuple of (List[SocialPost], str): List of new posts and the 'after' token for pagination
        """
        logger.info(f"🔍 Starting get_saved_posts with limit={limit}, after={after}")

        if not self.reddit:
            logger.warning(
                "⚠️ Reddit client not initialized, attempting to authenticate..."
            )
            if not self.authenticate():
                logger.error(
                    "❌ Authentication failed and no read-only access available"
                )
                return [], None

        try:
            # Test authentication by getting current user info
            me = self.reddit.user.me()
            logger.info(f"✅ Authenticated as: {me.name}")
            logger.info(f"🔒 Read-only mode: {self.read_only_mode}")
        except Exception as e:
            logger.error(f"❌ Error getting current user: {e}")
            return [], None

        posts = []
        params = {
            "limit": min(limit, 100)
        }  # Ensure we don't exceed Reddit's limit of 100
        if after and isinstance(after, str):
            logger.info(f"🔗 Resuming from after: {after}")
            params["after"] = after

        for attempt in range(max_retries):
            try:
                # Safety: minimal jitter before API call
                self._jitter_sleep()
                saved_items = []
                next_after = None

                if self.read_only_mode:
                    print(
                        "⚠️ In read-only mode, fetching popular posts instead of saved ones"
                    )
                    saved = self.reddit.subreddit("all").hot(limit=limit, params=params)
                    saved_items = list(saved)
                    logger.info(f"ℹ️ Fetched {len(saved_items)} popular posts")
                else:
                    logger.info("🔍 Fetching saved posts...")
                    try:
                        saved = self.reddit.user.me().saved(limit=limit, params=params)
                        saved_items = list(saved)
                        logger.info(f"✅ Fetched {len(saved_items)} saved items")
                        if hasattr(saved, "after"):
                            next_after = saved.after
                            logger.info(f"➡️ Next page token: {next_after}")
                    except Exception as e:
                        logger.error(f"❌ Error fetching saved posts: {e}")
                        saved_items = []

                # Log details about the first few items
                for i, item in enumerate(saved_items[:3]):  # Log first 3 items
                    try:
                        item_id = getattr(item, "id", "N/A")
                        item_name = getattr(item, "name", "N/A")
                        item_title = getattr(item, "title", "N/A")
                        if item_title != "N/A":
                            item_title = (
                                item_title[:50] + "..."
                                if len(str(item_title)) > 50
                                else item_title
                            )
                        print(
                            f"📝 Item {i + 1}: ID={item_id}, Name={item_name}, Title={item_title}"
                        )
                    except Exception as e:
                        logger.error(f"⚠️ Error logging item {i}: {e}")

                # Convert items to SocialPost objects with early-stop on seen IDs
                print(f"🔄 Converting {len(saved_items)} items to SocialPost objects...")
                for idx, item in enumerate(saved_items, 1):
                    try:
                        item_id = getattr(item, "id", "unknown")
                        # Only log every 10th item to speed up
                        if idx % 10 == 0 or idx == 1:
                            print(
                                f"🔄 Converting item {idx}/{len(saved_items)} (ID: {item_id})..."
                            )

                        # Early-stop if we hit known existing ID to avoid extra work
                        if existing_ids:
                            # support raw and fullname (t3_*) variants
                            raw_id = str(item_id or "").strip()
                            full_id = (
                                raw_id if raw_id.startswith("t3_") else f"t3_{raw_id}"
                            )
                            if raw_id in existing_ids or full_id in existing_ids:
                                logger.info(f"🛑 Early stop at known ID: {full_id}")
                                break

                        post = self._convert_reddit_item(
                            item, is_saved=not self.read_only_mode
                        )
                        if post:
                            posts.append(post)
                            self._processed_counter += 1
                            # Safety: light jitter every few items to avoid burst patterns
                            if self._processed_counter % 10 == 0:
                                self._jitter_sleep()
                        elif idx % 10 == 0:
                            print(
                                f"⚠️ Conversion returned None for item {idx} (ID: {item_id})"
                            )

                    except Exception as e:
                        logger.error(
                            f"⚠️ Error converting item {idx} (ID: {item_id}): {e}"
                        )
                        import traceback

                        traceback.print_exc()
                        continue

                print(
                    f"✅ Retrieved {len(posts)} items from Reddit"
                    + (" (read-only mode)" if self.read_only_mode else "")
                )
                return posts, next_after  # Return both posts and next_after token

            except Exception as e:
                print(
                    f"❌ Error during Reddit API call (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)  # Exponential backoff
                    logger.warning(f"🔄 Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)

        logger.error("❌ All retry attempts failed")

        # Try universal fallback if Reddit API completely fails
        logger.warning("🔄 Attempting universal fallback for Reddit content...")
        try:
            if not self.universal_collector:
                logger.warning("⚠️ UniversalCollector not available; skipping fallback")
                return [], None
            fallback_posts = []
            # Try to scrape some popular Reddit URLs as fallback
            reddit_urls = [
                "https://www.reddit.com/r/popular/",
                "https://www.reddit.com/r/all/",
                "https://www.reddit.com/r/programming/",
                "https://www.reddit.com/r/technology/",
            ]

            for url in reddit_urls[:2]:  # Limit to 2 URLs to avoid overwhelming
                try:
                    logger.info(f"🌐 Trying universal scraping for: {url}")
                    result = self.universal_collector.collect_content(
                        url, validate_content=True
                    )

                    if result and result.get("success") and result.get("content"):
                        # Convert universal collector result to SocialPost format
                        content = result["content"]
                        post = SocialPost(
                            id=f"reddit_fallback_{hash(url)}",
                            platform="reddit",
                            content=content.get("text", ""),
                            author="reddit_fallback",
                            created_at=datetime.now(),
                            url=url,
                            title=content.get("title", "Reddit Fallback Content"),
                            engagement_metrics={"likes": 0, "shares": 0, "comments": 0},
                            metadata={
                                "collection_method": "universal_fallback",
                                "original_platform": "reddit",
                                "fallback_reason": "reddit_api_failed",
                            },
                        )
                        fallback_posts.append(post)
                        logger.info(
                            f"✅ Successfully scraped fallback content from {url}"
                        )

                        if len(fallback_posts) >= min(
                            limit, 10
                        ):  # Limit fallback posts
                            break

                except Exception as fallback_error:
                    logger.error(
                        f"⚠️ Universal fallback failed for {url}: {fallback_error}"
                    )
                    continue

            if fallback_posts:
                logger.info(
                    f"✅ Universal fallback retrieved {len(fallback_posts)} posts"
                )
                return fallback_posts, None
            else:
                logger.error("❌ Universal fallback also failed")

        except Exception as e:
            logger.error(f"❌ Error during universal fallback: {e}")

        return [], None  # Return empty list and None for next_after on failure

    def get_liked_posts(
        self, limit: int = 100, max_retries: int = 3
    ) -> List[SocialPost]:
        """Get upvoted posts from Reddit with retries."""
        if not self.reddit:
            if not self.authenticate():
                raise Exception("Authentication with Reddit failed")

        if self.read_only_mode:
            print(
                "⚠️ Cannot access liked posts in read-only mode. Returning empty list."
            )
            return []

        posts = []
        for attempt in range(max_retries):
            try:
                upvoted_items = self.reddit.user.me().upvoted(limit=limit)
                for item in upvoted_items:
                    post = self._convert_reddit_item(item, is_saved=False)
                    if post:
                        posts.append(post)
                logger.info(f"✅ Retrieved {len(posts)} upvoted items from Reddit")
                return posts  # Success
            except prawcore.exceptions.PrawcoreException as e:
                logger.error(f"❌ Reddit API error on attempt {attempt + 1}: {e}")
                if attempt >= max_retries - 1:
                    logger.error("❌ All retries failed for getting upvoted posts.")
                    break
                time.sleep(2 * (attempt + 1))
            except Exception as e:
                logger.error(f"❌ An unexpected error occurred: {e}")
                break  # Don't retry on unexpected errors
        return posts

    def get_top_comments(self, submission_id: str, limit: int = 10) -> List[Dict]:
        """Get top valuable comments for a Reddit submission with enhanced filtering"""
        try:
            submission = self.reddit.submission(id=submission_id)
            submission.comments.replace_more(limit=0)

            # Get top-level comments sorted by score
            top_comments = []
            all_comments = submission.comments.list()[
                :100
            ]  # Increased from 50 to 100 for better selection

            # Sort by score and filter valuable ones with enhanced criteria
            for comment in sorted(
                all_comments, key=lambda x: getattr(x, "score", 0), reverse=True
            ):
                if (
                    hasattr(comment, "body")
                    and comment.body not in ["[deleted]", "[removed]"]
                    and len(comment.body.strip())
                    > 20  # Reduced from 30 to 20 for more inclusivity
                    and getattr(comment, "score", 0) > 1
                ):  # Reduced from 2 to 1 for more inclusivity
                    # Enhanced value scoring
                    comment_score = getattr(comment, "score", 0)
                    is_op = getattr(comment, "is_submitter", False)
                    has_awards = (
                        hasattr(comment, "all_awardings")
                        and len(comment.all_awardings) > 0
                    )
                    is_long_form = len(comment.body) > 200  # Detailed responses
                    has_links = "http" in comment.body.lower()  # Contains references

                    # Prioritize valuable comments
                    value_multiplier = 1
                    if is_op:
                        value_multiplier += 2  # OP responses are valuable
                    if has_awards:
                        value_multiplier += 1  # Awarded comments
                    if is_long_form:
                        value_multiplier += 0.5  # Detailed responses
                    if has_links:
                        value_multiplier += 0.5  # Comments with references

                    effective_score = comment_score * value_multiplier

                    top_comments.append(
                        {
                            "author": str(comment.author)
                            if comment.author
                            else "Unknown",
                            "content": comment.body,
                            "score": comment_score,
                            "effective_score": effective_score,
                            "created_at": datetime.fromtimestamp(
                                comment.created_utc
                            ).isoformat(),
                            "is_op": is_op,
                            "has_awards": has_awards,
                            "depth": getattr(comment, "depth", 0),
                            "url": f"https://reddit.com{comment.permalink}",
                            "comment_length": len(comment.body),
                            "has_links": has_links,
                        }
                    )

            # Sort by effective score and return top comments
            top_comments.sort(key=lambda x: x["effective_score"], reverse=True)
            return top_comments[:limit]

        except Exception as e:
            logger.error(f"❌ Error extracting comments for {submission_id}: {e}")
            return []

    def _convert_reddit_item(self, item, is_saved: bool = True) -> SocialPost:
        """Convert Reddit submission or comment to SocialPost"""
        try:
            # Handle both submissions (posts) and comments
            if isinstance(item, praw.models.Submission):  # It's a submission
                # Optional: fetch top comments (disabled by default for speed)
                import os

                fetch_comments = os.getenv(
                    "REDDIT_FETCH_TOP_COMMENTS", "false"
                ).lower() in ("1", "true", "yes", "on")
                top_comments = []
                if fetch_comments:
                    top_comments = self.get_top_comments(item.id, limit=10)

                # Build enhanced content with valuable comments
                enhanced_content = (
                    f"{item.title}\n\n{item.selftext}" if item.selftext else item.title
                )

                if top_comments:
                    enhanced_content += "\n\n=== TOP VALUABLE COMMENTS ===\n"
                    for i, comment in enumerate(top_comments, 1):
                        enhanced_content += f"\n💬 Comment {i} (Score: {comment['score']}) by {comment['author']}:\n"
                        enhanced_content += f"{comment['content']}\n"

                        # Add comment metadata for analysis
                        if comment.get("is_op"):
                            enhanced_content += "   [OP Response]\n"
                        if comment["score"] > 50:
                            enhanced_content += "   [High Engagement]\n"

                # Ensure we have a valid URL
                url = (
                    f"https://reddit.com{item.permalink}"
                    if hasattr(item, "permalink") and item.permalink
                    else "https://reddit.com"
                )

                return SocialPost(
                    platform="reddit",
                    post_id=item.id if hasattr(item, "id") else "unknown_id",
                    author=str(item.author)
                    if hasattr(item, "author") and item.author
                    else "[deleted]",
                    author_handle=f"u/{item.author}"
                    if hasattr(item, "author") and item.author
                    else "[deleted]",
                    content=enhanced_content,
                    created_at=datetime.fromtimestamp(item.created_utc)
                    if hasattr(item, "created_utc")
                    else datetime.utcnow(),
                    url=f"https://reddit.com{item.permalink}",
                    post_type="post_with_comments" if top_comments else "post",
                    media_urls=self._extract_media_urls(item),
                    hashtags=[],  # Reddit doesn't have hashtags
                    mentions=[],  # Could parse mentions from text
                    engagement={
                        "score": item.score,
                        "upvote_ratio": getattr(item, "upvote_ratio", 0),
                        "num_comments": item.num_comments,
                        "valuable_comments_count": len(top_comments),
                    },
                    is_saved=is_saved,
                    folder_category=f"r/{item.subreddit.display_name}"
                    if hasattr(item, "subreddit") and item.subreddit
                    else "Unknown",
                )
            elif isinstance(item, praw.models.Comment):  # It's a comment
                # Ensure we have a valid URL
                comment_url = (
                    f"https://reddit.com{item.permalink}"
                    if hasattr(item, "permalink") and item.permalink
                    else "https://reddit.com"
                )

                return SocialPost(
                    platform="reddit_comment",
                    post_id=f"{item.id}"
                    if hasattr(item, "id")
                    else "unknown_comment_id",
                    author=str(item.author)
                    if hasattr(item, "author") and item.author
                    else "[deleted]",
                    author_handle=f"u/{item.author}"
                    if hasattr(item, "author") and item.author
                    else "[deleted]",
                    content=getattr(item, "body", "[No content]"),
                    created_at=datetime.fromtimestamp(item.created_utc)
                    if hasattr(item, "created_utc")
                    else datetime.utcnow(),
                    url=comment_url,
                    post_type="comment",
                    media_urls=self._extract_media_from_comment(item),
                    hashtags=[],
                    mentions=[],
                    engagement={
                        "score": item.score,
                        "replies": len(item.replies)
                        if hasattr(item.replies, "__len__")
                        else 0,
                    },
                    is_saved=is_saved,
                    folder_category=f"r/{item.subreddit.display_name}",
                )

        except Exception as e:
            logger.error(f"❌ Error converting Reddit item: {e}")
            return None

    def _extract_media_urls(self, submission: praw.models.Submission) -> List[str]:
        """Extract media URLs from a Reddit submission - FAST VERSION (no gallery fetches)"""
        if not submission or not hasattr(submission, "id"):
            return []

        media_urls = set()

        try:
            # 1. Direct URL for image/gif (fast)
            if (
                hasattr(submission, "url")
                and submission.url
                and isinstance(submission.url, str)
            ):
                if any(
                    submission.url.lower().endswith(ext)
                    for ext in [".jpg", ".jpeg", ".png", ".gif"]
                ):
                    media_urls.add(submission.url)

            # 2. Thumbnail (always available, fast)
            if hasattr(submission, "thumbnail") and submission.thumbnail:
                thumb = submission.thumbnail
                if thumb and thumb != "self" and thumb != "default":
                    media_urls.add(thumb)

            # 3. Preview images (fast, no fetch needed)
            if (
                hasattr(submission, "preview")
                and submission.preview
                and "images" in submission.preview
            ):
                for image in submission.preview["images"][
                    :2
                ]:  # Limit to first 2 images
                    if not isinstance(image, dict):
                        continue
                    source = image.get("source", {})
                    if not isinstance(source, dict):
                        continue
                    source_url = source.get("url")
                    if isinstance(source_url, str):
                        media_urls.add(source_url.replace("&amp;", "&"))

            # Skip gallery and video checks that trigger fetches

        except Exception as e:
            logger.error(f"⚠️ Error extracting media URLs: {e}")

        return list(media_urls)

    def _extract_media_from_comment(self, comment: praw.models.Comment) -> List[str]:
        """Extract media URLs from a Reddit comment (usually GIFs or images)."""
        if not comment or not hasattr(comment, "id"):
            return []

        media_urls = set()

        try:
            if hasattr(comment, "media_metadata") and comment.media_metadata:
                for item in comment.media_metadata.values():
                    if "s" in item and "u" in item["s"]:
                        media_urls.add(item["s"]["u"].replace("&amp;", "&"))
        except Exception as e:
            logger.error(f"⚠️ Error extracting comment media: {e}")

        return list(media_urls)

    async def _capture_reddit_screenshot(
        self, post_url: str, post_id: str
    ) -> Optional[str]:
        """Capture a screenshot of a Reddit post using Playwright."""
        if not self.enable_screenshots:
            return None

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    viewport={"width": 1200, "height": 800},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                page = await context.new_page()

                # Navigate to the Reddit post
                await page.goto(post_url, wait_until="networkidle")

                # Wait for the main post content to load
                await page.wait_for_selector(
                    '[data-testid="post-content"]', timeout=10000
                )

                # Try to find and click "Show more" or expand buttons if they exist
                try:
                    show_more_buttons = await page.query_selector_all(
                        'button:has-text("Show more")'
                    )
                    for button in show_more_buttons:
                        if await button.is_visible():
                            await button.click()
                            await page.wait_for_timeout(1000)
                except Exception:
                    pass

                # Focus on the main post content area
                post_element = await page.query_selector('[data-testid="post-content"]')
                if not post_element:
                    # Fallback selector
                    post_element = await page.query_selector('[data-click-id="body"]')

                if post_element:
                    # Take screenshot of just the post content
                    screenshot_path = self.screenshot_dir / f"{post_id}.png"
                    await post_element.screenshot(path=str(screenshot_path))
                    logger.info(f"📸 Screenshot saved: {screenshot_path}")
                    return str(screenshot_path)
                else:
                    # Take full page screenshot as fallback
                    screenshot_path = self.screenshot_dir / f"{post_id}_full.png"
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"📸 Full page screenshot saved: {screenshot_path}")
                    return str(screenshot_path)

        except Exception as e:
            logger.error(f"⚠️ Error capturing screenshot for {post_id}: {e}")
            return None
