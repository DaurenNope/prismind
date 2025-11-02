import os
import requests
from datetime import datetime, timezone, timedelta
import streamlit as st

from src.database.publishing.bridge import MimesisDB
from src.publishing.worker import (
    post_to_telegram_direct,
    post_to_twitter_direct,
    post_to_threads_direct,
)


def render():
    st.header("Scheduler")
    db = MimesisDB()
    due = []
    try:
        due = db.list_due_posts()
    except Exception as exc:
        st.warning(f"Could not load due items: {exc}")

    st.subheader("Due items")
    if not due:
        st.write("None")
    else:
        for item in due:
            persona = item.get("personality_key") or item.get("persona_key", "unknown")
            scheduled_time = item.get("scheduled_time") or item.get(
                "scheduled_at", "unknown"
            )
            st.write(
                f"{item['id']} · {persona} → {item['platform']} · {scheduled_time}"
            )

    st.subheader("Autoposter Service (optional)")
    autoposter_url = os.getenv("AUTOMATION_URL", "http://127.0.0.1:8000")
    if st.button("Check Autoposter Health"):
        try:
            r = requests.get(f"{autoposter_url}/health", timeout=5)
            st.success(f"Autoposter: {r.status_code} {r.text[:120]}")
        except Exception as e:
            st.warning(f"Autoposter unreachable: {e}")

    st.subheader("Run one cycle")
    st.write("**Platform Status:**")
    st.write("- Twitter: ✅ Direct API (Tweepy)")
    st.write("- Telegram: ✅ Direct API (Bot API)")
    st.write("- Threads: ✅ Direct API (Meta Graph API)")

    if st.button("Run one cycle"):
        if not due:
            st.warning("No due posts to publish")
        else:
            posted = 0
            failed = 0
            for item in due:
                platform = item.get("platform", "")

                # Route based on platform
                if platform == "telegram":
                    # Use direct Telegram Bot API (no webhook needed)
                    try:
                        result = post_to_telegram_direct(item["content"])

                        if result.get("success"):
                            platform_post_id = result.get("message_id")
                            post_url = result.get("url")

                            db.mark_posted(
                                item["id"], platform_post_id=platform_post_id
                            )
                            posted += 1

                            msg = f"✅ Posted to Telegram: {item['content'][:50]}..."
                            if post_url:
                                msg += f" ({post_url})"
                            st.success(msg)
                        else:
                            error = result.get("error", "Unknown error")
                            st.error(
                                f"❌ Failed to post {item['id']} to Telegram: {error}"
                            )
                            failed += 1
                            try:
                                db.sb.client.table("scheduled_posts").update(
                                    {"status": "retry"}
                                ).eq("id", item["id"]).execute()
                            except Exception:
                                pass
                    except Exception as e:
                        st.error(f"❌ Error posting {item['id']} to Telegram: {e}")
                        failed += 1
                    continue

                elif platform == "twitter":
                    # Use direct Twitter API (no webhook needed)
                    try:
                        result = post_to_twitter_direct(item["content"])

                        if result.get("success"):
                            platform_post_id = result.get("tweet_id")
                            post_url = result.get("url")

                            db.mark_posted(
                                item["id"], platform_post_id=platform_post_id
                            )
                            posted += 1

                            msg = f"✅ Posted to Twitter: {item['content'][:50]}..."
                            if post_url:
                                msg += f" ({post_url})"
                            st.success(msg)
                        else:
                            error = result.get("error", "Unknown error")
                            st.error(
                                f"❌ Failed to post {item['id']} to Twitter: {error}"
                            )
                            failed += 1
                            try:
                                db.sb.client.table("scheduled_posts").update(
                                    {"status": "retry"}
                                ).eq("id", item["id"]).execute()
                            except Exception:
                                pass
                    except Exception as e:
                        st.error(f"❌ Error posting {item['id']} to Twitter: {e}")
                        failed += 1
                    continue

                elif platform == "threads":
                    # Use direct Threads Meta Graph API (no webhook needed)
                    try:
                        result = post_to_threads_direct(item["content"])

                        if result.get("success"):
                            platform_post_id = result.get("post_id")
                            post_url = result.get("url")

                            db.mark_posted(
                                item["id"], platform_post_id=platform_post_id
                            )
                            posted += 1

                            msg = f"✅ Posted to Threads: {item['content'][:50]}..."
                            if post_url:
                                msg += f" ({post_url})"
                            st.success(msg)
                        else:
                            error = result.get("error", "Unknown error")
                            st.error(
                                f"❌ Failed to post {item['id']} to Threads: {error}"
                            )
                            failed += 1
                            try:
                                db.sb.client.table("scheduled_posts").update(
                                    {"status": "retry"}
                                ).eq("id", item["id"]).execute()
                            except Exception:
                                pass
                    except Exception as e:
                        st.error(f"❌ Error posting {item['id']} to Threads: {e}")
                        failed += 1
                    continue

                # For other platforms (unsupported), skip
                st.warning(
                    f"⚠️ Unsupported platform: {platform}. Skipping item {item['id']}"
                )
                failed += 1

            st.info(f"Posted: {posted}, Failed: {failed}")
