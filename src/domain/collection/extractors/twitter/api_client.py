import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)
"""Twitter API client - direct GraphQL API calls (bypasses browser automation detection)"""

try:
    from dateutil import parser as date_parser
except Exception:
    date_parser = None

from ..social_extractor_base import SocialPost


class TwitterAPIClient:
    """Direct API client for Twitter - uses GraphQL API"""

    def __init__(self, cookies: Dict[str, str], auth_token: str, ct0: str):
        self.cookies = cookies
        self.auth_token = auth_token
        self.ct0 = ct0
        self.base_url = "https://x.com/i/api/graphql"

    async def get_bookmarks(
        self, limit: int = 50, cursor: Optional[str] = None
    ) -> Tuple[List[SocialPost], Optional[str]]:
        """Get bookmarks via GraphQL API"""
        import aiohttp

        # GraphQL query for bookmarks
        query_id = "Hf9iRaMf0HtJB6bdLmrJAg"
        variables = {"count": limit, "includePromotedContent": True}
        if cursor:
            variables["cursor"] = cursor
        features = {
            "rweb_video_screen_enabled": False,
            "payments_enabled": False,
            "profile_label_improvements_pcf_label_in_post_enabled": True,
            "responsive_web_profile_redirect_enabled": False,
            "rweb_tipjar_consumption_enabled": True,
            "verified_phone_label_enabled": False,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "premium_content_api_read_enabled": False,
            "communities_web_enable_tweet_community_results_fetch": True,
            "c9s_tweet_anatomy_moderator_badge_enabled": True,
            "responsive_web_grok_analyze_button_fetch_trends_enabled": False,
            "responsive_web_grok_analyze_post_followups_enabled": True,
            "responsive_web_jetfuel_frame": True,
            "responsive_web_grok_share_attachment_enabled": True,
            "articles_preview_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": True,
            "tweet_awards_web_tipping_enabled": False,
            "responsive_web_grok_show_grok_translated_post": False,
            "responsive_web_grok_analysis_button_from_backend": True,
            "creator_subscriptions_quote_tweet_preview_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_grok_image_annotation_enabled": True,
            "responsive_web_grok_imagine_annotation_enabled": True,
            "responsive_web_grok_community_note_auto_translation_is_enabled": False,
            "responsive_web_enhance_cards_enabled": False,
        }

        url = f"{self.base_url}/{query_id}/Bookmarks"
        params = {"variables": json.dumps(variables), "features": json.dumps(features)}

        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "authorization": f"Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "content-type": "application/json",
            "referer": "https://x.com/i/bookmarks",
            "sec-ch-ua": '"Not_A Brand";v="99", "Chromium";v="142"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Mobile Safari/537.36",
            "x-csrf-token": self.ct0,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "en",
        }

        # Build cookie string
        cookie_parts = []
        for name, value in self.cookies.items():
            cookie_parts.append(f"{name}={value}")
        cookie_string = "; ".join(cookie_parts)
        headers["cookie"] = cookie_string

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status != 200:
                    text = await response.text()
                    raise Exception(
                        f"API request failed: {response.status} - {text[:200]}"
                    )

                data = await response.json()
                return self._parse_bookmarks_response(data)

    def _parse_bookmarks_response(
        self, data: Dict[str, Any]
    ) -> Tuple[List[SocialPost], Optional[str]]:
        """Parse GraphQL response into SocialPost objects"""
        posts = []
        next_cursor = None

        try:
            # Navigate through GraphQL response structure
            bookmark_data = data.get("data", {})
            timeline = (
                bookmark_data.get("bookmark_timeline_v2", {}).get("timeline", {})
                or bookmark_data.get("bookmark_timeline", {}).get("timeline", {})
            )
            instructions = timeline.get("instructions", [])

            if not instructions:
                logger.warning("⚠️ No instructions in API response")
                # Save response for debugging
                import json

                with open("logs/twitter_api_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                logger.info("   Saved full response to logs/twitter_api_response.json")
                return [], None

            for instruction in instructions:
                if instruction.get("type") == "TimelineAddEntries":
                    entries = instruction.get("entries", [])
                    for entry in entries:
                        content = entry.get("content", {})
                        entry_type = content.get("entryType")

                        if entry_type == "TimelineTimelineItem":
                            item_content = content.get("itemContent", {})
                            tweet_results = item_content.get("tweet_results", {})
                            result = tweet_results.get("result", {})

                            if not result:
                                continue

                            if result.get("__typename") == "TweetWithVisibilityResults":
                                result = result.get("tweet", {})

                            legacy = result.get("legacy", {})
                            core = result.get("core", {})
                            user_results = core.get("user_results", {}) if core else {}
                            user_result = user_results.get("result", {})
                            user_legacy = (
                                user_result.get("legacy", {}) if user_result else {}
                            )

                            tweet_id = result.get("rest_id") or legacy.get("id_str")
                            if not tweet_id:
                                continue

                            user_core = user_result.get("core", {}) if user_result else {}
                            author = (
                                user_legacy.get("name")
                                or user_core.get("name")
                                or "Unknown"
                            )
                            author_handle = (
                                user_legacy.get("screen_name")
                                or user_core.get("screen_name")
                                or ""
                            )
                            
                            # Check for note tweet (long-form content) first
                            content_text = ""
                            note_tweet = result.get("note_tweet", {})
                            if note_tweet:
                                note_results = note_tweet.get("note_tweet_results", {})
                                note_result = note_results.get("result", {})
                                if note_result:
                                    # Full text is in note_tweet for long posts
                                    content_text = note_result.get("text", "")
                            
                            # Fallback to legacy full_text if note_tweet not available
                            if not content_text:
                                content_text = legacy.get("full_text", "")

                            def _sanitize_tweet_text(text: str) -> str:
                                """Remove trailing t.co placeholders and collapse whitespace."""
                                if not text:
                                    return text
                                import re

                                # Remove any trailing t.co URLs (often media placeholders)
                                text = re.sub(r"(https://t\.co/\w+)+\s*$", "", text).rstrip()
                                # Remove standalone t.co links inside text (optional)
                                text = re.sub(r"\s+https://t\.co/\w+\b", "", text)
                                # Collapse extra whitespace
                                text = re.sub(r"\s{2,}", " ", text)
                                return text.strip()

                            content_text = _sanitize_tweet_text(content_text)
                            
                            created_at_str = legacy.get("created_at", "")

                            created_at = datetime.now()
                            if created_at_str:
                                if date_parser:
                                    try:
                                        created_at = date_parser.parse(created_at_str)
                                    except Exception:
                                        pass
                                else:
                                    try:
                                        created_at = datetime.strptime(
                                            created_at_str, "%a %b %d %H:%M:%S %z %Y"
                                        )
                                    except Exception:
                                        pass

                            url = (
                                f"https://x.com/{author_handle}/status/{tweet_id}"
                                if author_handle
                                else f"https://x.com/i/web/status/{tweet_id}"
                            )

                            post = SocialPost(
                                platform="twitter",
                                author=author,
                                author_handle=author_handle,
                                content=content_text,
                                created_at=created_at,
                                url=url,
                                post_type="tweet",
                                is_saved=True,
                                post_id=f"twitter_{tweet_id}",
                            )

                            posts.append(post)
                        elif entry_type == "TimelineTimelineCursor":
                            cursor_type = (
                                content.get("cursorType")
                                or content.get("value")
                                or content.get("cursor")
                            )
                            if (
                                cursor_type
                                and "Bottom" in cursor_type
                                and not next_cursor
                            ):
                                next_cursor = (
                                    content.get("value")
                                    or content.get("cursorValue")
                                    or content.get("text")
                                )

        except Exception as e:
            logger.error(f"⚠️ Error parsing API response: {e}")
            import traceback

            traceback.print_exc()
            # Save response for debugging
            try:
                import json

                Path("logs").mkdir(exist_ok=True)
                with open("logs/twitter_api_response_error.json", "w") as f:
                    json.dump(data, f, indent=2)
                logger.error(
                    "   Saved error response to logs/twitter_api_response_error.json"
                )
            except Exception as e:
                logger.error(f"Error: {e}")
                pass

        return posts, next_cursor
