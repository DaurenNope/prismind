import logging

logger = logging.getLogger(__name__)
"""
Threads Posting Service using Meta Graph API
Direct implementation without external dependencies
"""

import json
import time
from datetime import datetime
from typing import Dict, Optional

import requests

from src.utils.secrets_manager import get_secrets_manager

secrets = get_secrets_manager()


class ThreadsPoster:
    """Post to Threads using Meta's official Graph API."""

    def __init__(self):
        """Initialize with Threads API credentials."""
        # Support multiple env var names using secrets manager
        self.access_token = (
            secrets.get("THREADS_ACCESS_TOKEN")
            or secrets.get("THREADS_TOKEN_ACCESS")
            or secrets.get("THREADS_API_TOKEN")
        )
        self.user_id = secrets.get("THREADS_USER_ID") or secrets.get("THREADS_API_USER_ID")

        if not self.access_token:
            raise ValueError(
                "Threads access token missing. Add to .env:\n"
                "THREADS_ACCESS_TOKEN=your_access_token\n"
                "(or THREADS_TOKEN_ACCESS)\n"
            )

        self.api_base = "https://graph.threads.net/v1.0"

        # If user_id not provided, try to fetch it from API
        if not self.user_id:
            self._fetch_user_id()

    def _fetch_user_id(self):
        """Fetch user ID from API using access token."""
        try:
            response = requests.get(
                f"{self.api_base}/me",
                params={"fields": "id,username", "access_token": self.access_token},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()
            self.user_id = data.get("id")
            self.username = data.get("username")
        except Exception as e:
            logger.error(f"Error: {e}")
            raise ValueError(
                f"Failed to fetch Threads user ID: {e}\n"
                "Add THREADS_USER_ID to .env manually"
            )

    def post_thread(self, content: str, image_url: Optional[str] = None) -> Dict:
        """
        Post to Threads.

        Args:
            content: Post content (500 char max)
            image_url: Optional image URL (must be publicly accessible)

        Returns:
            Dict with success, post_id, url, error keys
        """
        try:
            # Validate length
            if len(content) > 500:
                return {
                    "success": False,
                    "error": f"Content too long: {len(content)} chars (max 500)",
                }

            if not self.user_id:
                return {
                    "success": False,
                    "error": "User ID not available. Add THREADS_USER_ID to .env",
                }

            # Step 1: Create media container
            container_params = {
                "media_type": "TEXT",
                "text": content,
                "access_token": self.access_token,
            }

            if image_url:
                container_params["image_url"] = image_url
                container_params["media_type"] = "IMAGE"

            container_response = requests.post(
                f"{self.api_base}/{self.user_id}/threads",
                data=container_params,
                timeout=30,
            )
            container_response.raise_for_status()
            container_data = container_response.json()

            if "id" not in container_data:
                return {
                    "success": False,
                    "error": f"Container creation failed: {container_data.get('error', {}).get('message', 'Unknown error')}",
                }

            container_id = container_data["id"]

            # Step 2: Publish container (with small delay)
            time.sleep(1)  # Brief delay recommended by Meta

            publish_params = {
                "creation_id": container_id,
                "access_token": self.access_token,
            }

            publish_response = requests.post(
                f"{self.api_base}/{self.user_id}/threads_publish",
                data=publish_params,
                timeout=30,
            )
            publish_response.raise_for_status()
            publish_data = publish_response.json()

            if "id" not in publish_data:
                return {
                    "success": False,
                    "error": f"Publishing failed: {publish_data.get('error', {}).get('message', 'Unknown error')}",
                    "container_id": container_id,
                }

            post_id = publish_data["id"]

            # Build Threads URL (requires username)
            post_url = None
            if hasattr(self, "username"):
                post_url = f"https://www.threads.net/@{self.username}/post/{post_id}"

            return {
                "success": True,
                "post_id": post_id,
                "url": post_url,
                "container_id": container_id,
                "posted_at": datetime.utcnow().isoformat(),
            }

        except requests.exceptions.HTTPError as e:
            logger.error(f"Error: {e}")
            error_msg = str(e)
            try:
                error_data = e.response.json()
                error_msg = error_data.get("error", {}).get("message", str(e))
            except (json.JSONDecodeError, AttributeError, KeyError) as parse_error:
                pass

            return {"success": False, "error": f"HTTP error: {error_msg}"}

        except Exception as e:
            logger.error(f"Error: {e}")
            return {"success": False, "error": str(e)}

    def get_thread_insights(self, thread_id: str) -> Optional[Dict]:
        """
        Get insights/metrics for a thread.

        Args:
            thread_id: Thread post ID

        Returns:
            Dict with metrics or None if failed
        """
        try:
            response = requests.get(
                f"{self.api_base}/{thread_id}/insights",
                params={
                    "metric": "views,likes,replies,reposts,quotes",
                    "access_token": self.access_token,
                },
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            if "data" not in data:
                return None

            # Parse metrics
            metrics = {}
            for item in data["data"]:
                metric_name = item.get("name")
                metric_value = item.get("values", [{}])[0].get("value", 0)
                metrics[metric_name] = metric_value

            return {
                "thread_id": thread_id,
                "views": metrics.get("views", 0),
                "likes": metrics.get("likes", 0),
                "replies": metrics.get("replies", 0),
                "reposts": metrics.get("reposts", 0),
                "quotes": metrics.get("quotes", 0),
                "fetched_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Error fetching insights: {e}")
            return None


def post_to_threads_direct(content: str, image_url: Optional[str] = None) -> Dict:
    """
    Post to Threads using direct API.

    Returns:
        Dict with 'success', 'post_id', 'url', 'error' keys
    """
    try:
        poster = ThreadsPoster()
        result = poster.post_thread(content, image_url=image_url)

        # Normalize response format
        if result.get("success"):
            return {
                "success": True,
                "post_id": result.get("post_id"),
                "url": result.get("url"),
                "error": None,
            }
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}

    except Exception as e:
        logger.error(f"Error: {e}")
        return {
            "success": False,
            "error": f"ThreadsPoster initialization failed: {str(e)}",
        }


if __name__ == "__main__":
    logger.info("THREADS POSTER (Meta Graph API)")
    logger.info("=" * 60)

    try:
        poster = ThreadsPoster()

        logger.info(f"\n✅ Threads API credentials loaded")
        if hasattr(poster, "username"):
            logger.info(f"   Username: @{poster.username}")
        logger.info(f"   User ID: {poster.user_id}")
        logger.info(f"   Token: [REDACTED]")

        logger.info("\n📝 Ready to post to Threads")
        logger.info("   (Uncomment test code to actually post)")

        # Uncomment to test:
        # test_content = "Testing Threads API from beyondlines! 🧵"
        # result = poster.post_thread(test_content)
        #
        # if result['success']:
        #     logger.info(f"\n✅ SUCCESS! Posted to Threads")
        #     logger.info(f"   URL: {result.get('url', 'N/A')}")
        #     logger.info(f"   Post ID: {result['post_id']}")
        # else:
        #     logger.error(f"\n❌ Failed: {result['error']}")

    except ValueError as e:
        logger.error(f"\n❌ {e}")
