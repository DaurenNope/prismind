import os
import logging
import threading
import time
import requests
from typing import Optional

from src.database.publishing.bridge import MimesisDB

logger = logging.getLogger(__name__)


def post_to_twitter_direct(content: str) -> dict:
    """
    Post to Twitter using Playwright (browser automation - like mimesis).
    Falls back to API if Playwright fails.

    Returns:
        dict with 'success', 'tweet_id', 'url', 'error' keys
    """
    # Try Playwright first (primary method like mimesis)
    try:
        from src.publishing.platforms.twitter_playwright import (
            post_to_twitter_direct as twitter_post_playwright,
        )
        
        result = twitter_post_playwright(content)
        if result.get("success"):
            return result
        # If Playwright failed, try API fallback
        logger.warning(f"Playwright failed: {result.get('error')}, trying API...")
    except ImportError as e:
        logger.warning(f"Playwright not available: {e}, trying API...")
    except Exception as e:
        logger.warning(f"Playwright error: {e}, trying API...")
    
    # Fallback to API
    try:
        from src.publishing.platforms.twitter import (
            post_to_twitter_direct as twitter_post_api,
        )
        return twitter_post_api(content)
    except ImportError as e:
        return {"success": False, "error": f"Twitter poster not available: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Twitter posting failed: {str(e)}"}


def post_to_threads_direct(content: str, image_url: Optional[str] = None) -> dict:
    """
    Post to Threads using Playwright ONLY (browser automation - like mimesis).
    No API fallback - Threads API doesn't work.

    Returns:
        dict with 'success', 'post_id', 'url', 'error' keys
    """
    # Use Playwright ONLY (like mimesis - no API fallback)
    try:
        from src.publishing.platforms.threads_playwright import (
            post_to_threads_direct as threads_post_playwright,
        )
        
        result = threads_post_playwright(content, image_url=image_url)
        return result  # Return Playwright result directly (no API fallback)
    except ImportError as e:
        return {"success": False, "error": f"Playwright not available: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Playwright error: {str(e)}"}


def post_to_telegram_direct(content: str, chat_id: Optional[str] = None) -> dict:
    """
    Post directly to Telegram using Bot API.

    Returns:
        dict with 'success', 'message_id', 'url', 'error' keys
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not chat_id:
        chat_id = os.getenv("TELEGRAM_CHAT_ID") or os.getenv("TELEGRAM_CHANNEL_ID")

    if not bot_token or not chat_id:
        return {
            "success": False,
            "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured",
            "permanent_failure": True  # Configuration error is permanent
        }

    api_base = f"https://api.telegram.org/bot{bot_token}"

    # Validate message length (Telegram limit: 4096 chars)
    if len(content) > 4096:
        return {
            "success": False,
            "error": f"Message too long: {len(content)} chars (max 4096)",
            "permanent_failure": True  # Message too long is permanent
        }

    try:
        payload = {
            "chat_id": chat_id,
            "text": content,
            "parse_mode": "Markdown",
            "disable_web_page_preview": False,
        }

        response = requests.post(f"{api_base}/sendMessage", json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("ok"):
            message = result.get("result", {})
            message_id = str(message.get("message_id"))

            # Build message URL (for public channels)
            message_url = None
            if isinstance(chat_id, str) and chat_id.startswith("@"):
                channel_name = chat_id[1:]  # Remove @
                message_url = f"https://t.me/{channel_name}/{message_id}"

            return {
                "success": True,
                "message_id": message_id,
                "url": message_url,
                "error": None,
            }
        else:
            # Check if it's a permanent error from Telegram API
            error_desc = result.get("description", "Unknown Telegram API error")
            permanent = any(keyword in error_desc.lower() for keyword in [
                "forbidden", "unauthorized", "bad request", "chat not found",
                "bot blocked", "bot was blocked", "user is deactivated"
            ])
            
            return {
                "success": False,
                "error": error_desc,
                "permanent_failure": permanent
            }

    except requests.exceptions.Timeout:
        return {
            "success": False,
            "error": "Telegram API timeout (30s)",
            "permanent_failure": False  # Timeout is transient
        }
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None
        error_msg = f"HTTP error: {status_code}"
        
        # Add more context for common errors
        if status_code == 403:
            error_msg += " (Forbidden - check bot token permissions or chat access)"
        elif status_code == 401:
            error_msg += " (Unauthorized - invalid bot token)"
        elif status_code == 400:
            error_msg += " (Bad Request - check message format or chat_id)"
        
        return {
            "success": False,
            "error": error_msg,
            "status_code": status_code,
            "permanent_failure": status_code in [400, 401, 403]  # Permanent failures
        }
    except Exception as e:
        return {"success": False, "error": f"Exception: {str(e)}", "permanent_failure": False}


class PublisherWorker:
    """Background worker that posts due scheduled items periodically."""

    def __init__(self, interval_seconds: int = None) -> None:
        # Default to 15s for faster posting, or use env var, or 60s fallback
        self.interval_seconds = interval_seconds or int(os.getenv("PUBLISHER_WORKER_INTERVAL", "15"))
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._started = False

    def start(self) -> None:
        if self._started:
            logger.debug("Publisher worker already started")
            return
        self._started = True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="publisher-worker", daemon=True
        )
        self._thread.start()
        logger.debug(
            f"🚀 Publisher worker started (checking every {self.interval_seconds}s)"
        )

    def stop(self) -> None:
        self._stop.set()

    def _run_loop(self) -> None:
        db = MimesisDB()

        logger.debug("Publisher worker loop started")

        while not self._stop.is_set():
            try:
                try:
                    due = db.list_due_posts()
                except Exception as e:
                    # Network/DNS errors are handled gracefully in list_due_posts
                    # Only log as debug to avoid spam
                    logger.debug(f"Failed to list due posts (Supabase may be unavailable): {e}")
                    due = []
                if due:
                    logger.info(f"Found {len(due)} due post(s) to publish")
                for item in due:
                    platform = item.get("platform")
                    content = item.get("content", "")
                    item_id = item.get("id")

                    # Global platform gating via config
                    try:
                        from src.utils.config import get_config
                        cfg = get_config()
                        telegram_enabled = bool(cfg.flags.get("enable_telegram_channels", True))
                    except Exception:
                        telegram_enabled = True

                    # Route based on platform
                    if platform == "telegram":
                        # If Telegram is disabled, mark as failed immediately to prevent infinite retries
                        if not telegram_enabled:
                            try:
                                db.sb.client.table("scheduled_posts").update(
                                    {
                                        "status": "failed",
                                        "error_message": "Telegram disabled by config (enable_telegram_channels=false)",
                                    }
                                ).eq("id", item_id).execute()
                            except Exception:
                                pass
                            continue

                        # Use direct Telegram Bot API (no webhook needed)
                        try:
                            result = post_to_telegram_direct(content)

                            if result.get("success"):
                                platform_post_id = result.get("message_id")
                                post_url = result.get("url")

                                db.mark_posted(
                                    item_id, platform_post_id=platform_post_id
                                )

                                log_msg = f"✅ Posted to Telegram"
                                if post_url:
                                    log_msg += f": {post_url}"
                                elif platform_post_id:
                                    log_msg += f" (ID: {platform_post_id})"
                                logger.info(log_msg)
                            else:
                                error = result.get("error", "Unknown error")
                                status_code = result.get("status_code")
                                permanent_failure = result.get("permanent_failure", False)
                                
                                # Determine if this is a permanent failure
                                if permanent_failure:
                                    logger.error(
                                        f"❌ Permanent failure posting to Telegram (HTTP {status_code}): {error}. "
                                        f"Marking as failed - check bot token, permissions, or chat_id."
                                    )
                                    try:
                                        db.sb.client.table("scheduled_posts").update(
                                            {"status": "failed", "error_message": error}
                                        ).eq("id", item_id).execute()
                                    except Exception as update_error:
                                        logger.error(
                                            f"❌ Failed to update failure status for item {item_id}: {update_error}",
                                            exc_info=True
                                        )
                                else:
                                    # Transient failure - check retry count
                                    try:
                                        # Get current retry count
                                        current_item = db.sb.client.table("scheduled_posts").select(
                                            "retry_count"
                                        ).eq("id", item_id).single().execute()
                                        
                                        retry_count = current_item.data.get("retry_count", 0) if current_item.data else 0
                                        max_retries = 5  # Maximum retry attempts
                                        
                                        if retry_count >= max_retries:
                                            logger.error(
                                                f"❌ Max retries ({max_retries}) reached for Telegram post {item_id}. "
                                                f"Marking as failed: {error}"
                                            )
                                            db.sb.client.table("scheduled_posts").update(
                                                {
                                                    "status": "failed",
                                                    "error_message": f"Max retries exceeded: {error}",
                                                    "retry_count": retry_count + 1
                                                }
                                            ).eq("id", item_id).execute()
                                        else:
                                            logger.warning(
                                                f"⚠️ Transient failure posting to Telegram (attempt {retry_count + 1}/{max_retries}): {error}. "
                                                f"Will retry later."
                                            )
                                            db.sb.client.table("scheduled_posts").update(
                                                {
                                                    "status": "retry",
                                                    "retry_count": retry_count + 1,
                                                    "error_message": error
                                                }
                                            ).eq("id", item_id).execute()
                                    except Exception as retry_error:
                                        logger.error(
                                            f"❌ Failed to update retry status for item {item_id}: {retry_error}",
                                            exc_info=True
                                        )
                        except Exception as e:
                            logger.error(
                                f"❌ Exception posting item {item_id} to Telegram: {e}",
                                exc_info=True
                            )
                            # For exceptions, check retry count before marking as retry
                            try:
                                current_item = db.sb.client.table("scheduled_posts").select(
                                    "retry_count"
                                ).eq("id", item_id).single().execute()
                                
                                retry_count = current_item.data.get("retry_count", 0) if current_item.data else 0
                                max_retries = 5
                                
                                if retry_count >= max_retries:
                                    logger.error(
                                        f"❌ Max retries ({max_retries}) reached for Telegram post {item_id}. "
                                        f"Marking as failed after exception: {e}"
                                    )
                                    db.sb.client.table("scheduled_posts").update(
                                        {
                                            "status": "failed",
                                            "error_message": f"Max retries exceeded after exception: {str(e)}",
                                            "retry_count": retry_count + 1
                                        }
                                    ).eq("id", item_id).execute()
                                else:
                                    db.sb.client.table("scheduled_posts").update(
                                        {
                                            "status": "retry",
                                            "retry_count": retry_count + 1,
                                            "error_message": f"Exception: {str(e)}"
                                        }
                                    ).eq("id", item_id).execute()
                            except Exception as retry_error:
                                logger.error(
                                    f"❌ Failed to update retry status for item {item_id}: {retry_error}",
                                    exc_info=True
                                )
                        continue  # Skip webhook logic for telegram

                    elif platform == "twitter":
                        # Use Playwright (primary, like mimesis) with API fallback
                        try:
                            result = post_to_twitter_direct(content)

                            if result.get("success"):
                                platform_post_id = result.get("tweet_id")
                                post_url = result.get("url")

                                db.mark_posted(
                                    item_id,
                                    platform_post_id=platform_post_id,
                                    post_url=post_url,
                                )

                                # Method detection - check if we got a real tweet URL or synthetic ID
                                method = "API" if result.get("url") and "twitter.com" in result.get("url", "") and "/status/" in result.get("url", "") and not "playwright_" in result.get("tweet_id", "") else "Playwright"
                                log_msg = f"✅ Posted to Twitter ({method})"
                                if post_url:
                                    log_msg += f": {post_url}"
                                elif platform_post_id:
                                    log_msg += f" (ID: {platform_post_id})"
                                logger.info(log_msg)
                            else:
                                error = result.get("error", "Unknown error")
                                logger.error(f"❌ Failed to post to Twitter: {error}")
                                try:
                                    db.sb.client.table("scheduled_posts").update(
                                        {"status": "retry"}
                                    ).eq("id", item_id).execute()
                                except Exception as retry_error:
                                    logger.error(
                                        f"❌ Failed to update retry status for item {item_id}: {retry_error}",
                                        exc_info=True
                                    )
                        except Exception as e:
                            logger.error(
                                f"❌ Error posting item {item_id} to Twitter: {e}",
                                exc_info=True
                            )
                            try:
                                db.sb.client.table("scheduled_posts").update(
                                    {"status": "retry"}
                                ).eq("id", item_id).execute()
                            except Exception as retry_error:
                                logger.error(
                                    f"❌ Failed to update retry status for item {item_id}: {retry_error}",
                                    exc_info=True
                                )
                        continue  # Skip webhook logic for twitter

                    elif platform == "threads":
                        # Use Playwright (primary, like mimesis) with API fallback
                        try:
                            result = post_to_threads_direct(content)

                            if result.get("success"):
                                platform_post_id = result.get("post_id")
                                post_url = result.get("url")

                                db.mark_posted(
                                    item_id,
                                    platform_post_id=platform_post_id,
                                    post_url=post_url,
                                )

                                # Method detection - check if we got a real threads URL or synthetic ID
                                method = "API" if result.get("url") and "threads.net" in result.get("url", "") and "/post/" in result.get("url", "") and not "playwright_" in result.get("post_id", "") else "Playwright"
                                log_msg = f"✅ Posted to Threads ({method})"
                                if post_url:
                                    log_msg += f": {post_url}"
                                elif platform_post_id:
                                    log_msg += f" (ID: {platform_post_id})"
                                logger.info(log_msg)
                            else:
                                error = result.get("error", "Unknown error")
                                logger.error(f"❌ Failed to post to Threads: {error}")
                                try:
                                    db.sb.client.table("scheduled_posts").update(
                                        {"status": "retry"}
                                    ).eq("id", item_id).execute()
                                except Exception as retry_error:
                                    logger.error(
                                        f"❌ Failed to update retry status for item {item_id}: {retry_error}",
                                        exc_info=True
                                    )
                        except Exception as e:
                            logger.error(
                                f"❌ Error posting item {item_id} to Threads: {e}",
                                exc_info=True
                            )
                            try:
                                db.sb.client.table("scheduled_posts").update(
                                    {"status": "retry"}
                                ).eq("id", item_id).execute()
                            except Exception as retry_error:
                                logger.error(
                                    f"❌ Failed to update retry status for item {item_id}: {retry_error}",
                                    exc_info=True
                                )
                        continue  # Threads handled
            except Exception as e:
                logger.error(f"❌ Error in publisher worker: {e}", exc_info=True)
            finally:
                self._stop.wait(self.interval_seconds)


_publisher_singleton: Optional[PublisherWorker] = None


def get_publisher_worker() -> PublisherWorker:
    global _publisher_singleton
    if _publisher_singleton is None:
        _publisher_singleton = PublisherWorker()
    return _publisher_singleton
