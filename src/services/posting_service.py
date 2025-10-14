"""Posting service for publishing content to social media platforms."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import hmac
import hashlib
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PostingService:
    """
    Handles posting content to various social media platforms.
    Ported from mimesis project with adaptations for prismind.
    """

    def __init__(self) -> None:
        self.platform_config = self._load_platform_config()

    def _load_platform_config(self) -> Dict[str, Any]:
        """Load platform integration config from file."""
        config_path = Path(__file__).parent.parent.parent / "config" / "platform_integrations.json"
        if not config_path.exists():
            logger.warning("Platform integrations config not found: %s", config_path)
            return {}
        try:
            with config_path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except Exception as exc:
            logger.error("Failed to load platform config: %s", exc)
            return {}

    def _get_platform_config_value(self, platform: str, key: str) -> Optional[str]:
        """Get a config value for a platform."""
        return self.platform_config.get(platform, {}).get(key)

    def post_to_twitter(self, content: str, **kwargs) -> Dict[str, Any]:
        """
        Post content to Twitter.
        Supports both webhook and API approaches.
        """
        # Try webhook first (preferred)
        webhook_url = self._get_platform_config_value('twitter', 'webhook_url')
        webhook_secret = self._get_platform_config_value('twitter', 'webhook_secret')
        
        if webhook_url:
            return self._post_via_webhook('twitter', webhook_url, webhook_secret, content, **kwargs)
        
        # Fallback to Twitter API (requires tweepy)
        logger.warning("Twitter API posting not yet implemented in prismind")
        return {"success": False, "error": "Twitter API not configured"}

    def post_to_telegram(self, content: str, **kwargs) -> Dict[str, Any]:
        """
        Post content to Telegram using Bot API.
        """
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID") or kwargs.get("chat_id")
        
        if not bot_token or not chat_id:
            return {"success": False, "error": "TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not configured"}
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": content,
            "parse_mode": kwargs.get("parse_mode", "HTML"),
            "disable_web_page_preview": kwargs.get("disable_preview", False)
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get("ok"):
                return {
                    "success": True,
                    "platform": "telegram",
                    "message_id": data.get("result", {}).get("message_id"),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": data.get("description", "Unknown error")
                }
        except Exception as exc:
            logger.exception("Failed to post to Telegram: %s", exc)
            return {"success": False, "error": str(exc)}

    def post_to_threads(self, content: str, **kwargs) -> Dict[str, Any]:
        """
        Post content to Threads.
        Supports webhook approach.
        """
        webhook_url = self._get_platform_config_value('threads', 'webhook_url')
        webhook_secret = self._get_platform_config_value('threads', 'webhook_secret')
        
        if webhook_url:
            return self._post_via_webhook('threads', webhook_url, webhook_secret, content, **kwargs)
        
        logger.warning("Threads posting not configured")
        return {"success": False, "error": "Threads not configured"}

    def _post_via_webhook(
        self, 
        platform: str, 
        webhook_url: str, 
        webhook_secret: Optional[str],
        content: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generic webhook posting method.
        Sends content to a webhook endpoint with HMAC signature for security.
        """
        payload = {
            "platform": platform,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        }
        
        headers = {"Content-Type": "application/json"}
        
        # Add HMAC signature if secret is configured
        if webhook_secret:
            body = json.dumps(payload, ensure_ascii=False)
            signature = hmac.new(
                webhook_secret.encode('utf-8'),
                body.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "platform": platform,
                "webhook_response": response.json() if response.content else {},
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as exc:
            logger.exception("Webhook posting failed for %s: %s", platform, exc)
            return {
                "success": False,
                "platform": platform,
                "error": str(exc)
            }

    def publish(self, platform: str, content: str, **kwargs) -> Dict[str, Any]:
        """
        Universal publish method - routes to appropriate platform handler.
        
        Args:
            platform: Platform name (twitter, telegram, threads)
            content: Content to publish
            **kwargs: Additional platform-specific parameters
            
        Returns:
            Result dictionary with success status and details
        """
        platform = platform.lower()
        
        if platform == "twitter":
            return self.post_to_twitter(content, **kwargs)
        elif platform == "telegram":
            return self.post_to_telegram(content, **kwargs)
        elif platform == "threads":
            return self.post_to_threads(content, **kwargs)
        else:
            return {
                "success": False,
                "error": f"Unsupported platform: {platform}"
            }


# Singleton instance
_posting_service = None


def get_posting_service() -> PostingService:
    """Get the singleton posting service instance."""
    global _posting_service
    if _posting_service is None:
        _posting_service = PostingService()
    return _posting_service


# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python -m src.services.posting_service <platform> <content>")
        print("Example: python -m src.services.posting_service telegram 'Hello from PrisMind!'")
        sys.exit(1)
    
    platform = sys.argv[1]
    content = " ".join(sys.argv[2:])
    
    service = get_posting_service()
    result = service.publish(platform, content)
    
    print(json.dumps(result, indent=2))
