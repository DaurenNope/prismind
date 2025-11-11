#!/usr/bin/env python3
import streamlit as st
from datetime import datetime

from src.database.database_agent import DatabaseAgent


def render_publishing_analytics_tab():
    st.header("📈 Publishing Analytics")

    try:
        agent = DatabaseAgent()
        col_a, col_b, col_c = st.columns(3)
        window = col_a.selectbox("Window", ["24h", "7d", "30d"], index=1)
        platform = col_b.selectbox("Platform", ["All", "twitter", "reddit", "threads"], index=0)
        persona = col_c.text_input("Persona filter", "")

        minutes = {"24h": 24*60, "7d": 7*24*60, "30d": 30*24*60}[window]
        plat_arg = None if platform == "All" else platform
        person_arg = persona.strip() or None

        top = agent.get_top_posts(since_minutes=minutes, limit=50, platform=plat_arg, persona=person_arg)
        cohorts = agent.get_performance_cohorts(window_minutes=minutes)

        st.subheader("Top Posts")
        if top:
            cols = [
                {"platform": t.get("platform"),
                 "persona": t.get("persona"),
                 "posted_at": t.get("posted_at"),
                 "engagement": round(float(t.get("engagement_score") or 0), 4),
                 "likes": t.get("total_likes"),
                 "comments": t.get("total_comments"),
                 "shares": t.get("total_shares"),
                 "bookmarks": t.get("total_bookmarks"),
                 "url": t.get("url")}
                for t in top
            ]
            st.dataframe(cols, use_container_width=True)
        else:
            st.info("No posted content found in the selected window.")

        st.subheader("Cohorts (avg engagement)")
        c1, c2, c3 = st.columns(3)
        c1.json(cohorts.get("platform", {}))
        c2.json(cohorts.get("persona", {}))
        c3.json(cohorts.get("has_media", {}))

    except Exception as e:
        st.error(f"Analytics unavailable: {e}")

    st.markdown("---")
    st.subheader("🧠 Recent Analyses (Supabase)")
    try:
        from src.database.manager import SupabaseManager
        sm = SupabaseManager()
        # Fetch latest analyzed posts
        rows = (
            sm.client
            .table("posts")
            .select("platform,post_id,url,author,author_handle,analyzed_at,value_score,quality_score,ai_summary,tags,analysis_model,time_sensitive,urgency_score,relevance_window")
            .not_.is_("analyzed_at", "null")
            .order("urgency_score", desc=True)
            .order("analyzed_at", desc=True)
            .limit(25)
            .execute()
            .data or []
        )
        if not rows:
            st.info("No analyzed posts yet.")
        else:
            # Render compact table
            table = []
            for r in rows:
                urgent_badge = "" if not r.get("time_sensitive") else f"🔥 {round(float(r.get('urgency_score') or 0)*100)}% ({r.get('relevance_window')})"
                table.append({
                    "platform": r.get("platform"),
                    "post_id": r.get("post_id"),
                    "analyzed_at": r.get("analyzed_at"),
                    "urgent": urgent_badge,
                    "value": r.get("value_score"),
                    "quality": r.get("quality_score"),
                    "model": r.get("analysis_model"),
                    "author": r.get("author_handle") or r.get("author"),
                    "summary": (r.get("ai_summary") or "")[:120] + ("..." if (r.get("ai_summary") and len(r.get("ai_summary"))>120) else ""),
                    "tags": ", ".join(r.get("tags") or []) if isinstance(r.get("tags"), list) else (r.get("tags") or ""),
                    "url": r.get("url"),
                })
            st.dataframe(table, use_container_width=True)
    except Exception as e:
        st.info(f"Recent analyses unavailable: {e}")

import streamlit as st
from datetime import datetime, timedelta, timezone

from src.database.publishing.bridge import MimesisDB


def render():
    st.header("Publishing Analytics")
    db = MimesisDB()

    # Time filters
    colf1, colf2 = st.columns(2)
    with colf1:
        days = st.selectbox("Window", [1, 3, 7, 14, 30], index=2)
    with colf2:
        persona_filter = st.text_input("Persona filter (optional)")
    since_iso = (datetime.now(timezone.utc) - timedelta(days=int(days))).isoformat()

    try:
        ready = db.list_ready_transformations(
            None if not persona_filter else persona_filter
        )
    except Exception:
        ready = []
    try:
        due = db.list_due_posts()
    except Exception:
        due = []

    st.subheader("Snapshot")
    col1, col2 = st.columns(2)
    col1.metric("Ready to post", len(ready))
    col2.metric("Due now", len(due))

    st.subheader("Recent Posted Content")
    try:
        q = (
            db.sb.client.table("posted_content")
            .select("*")
            .order("posted_at", desc=True)
        )
        if persona_filter:
            q = q.eq("persona_key", persona_filter)
        rows = q.limit(50).execute().data

        if not rows:
            st.info("No posts published yet.")
        else:
            for row in rows:
                platform = row.get("platform", "unknown")
                persona = row.get("personality_key") or row.get(
                    "persona_key", "unknown"
                )
                posted_at = row.get("posted_at", "")
                post_url = row.get("platform_post_id")  # Might be URL or ID
                post_id = row.get("platform_post_id")

                col1, col2 = st.columns([3, 1])
                with col1:
                    platform_emoji = {
                        "twitter": "🐦",
                        "threads": "🧵",
                        "telegram": "📱",
                    }.get(platform, "📝")
                    st.write(
                        f"{platform_emoji} **{platform.upper()}** | {persona} | {posted_at[:19] if posted_at else 'unknown time'}"
                    )
                with col2:
                    if post_url or post_id:
                        if post_url and (
                            post_url.startswith("http") or post_url.startswith("www")
                        ):
                            st.markdown(f"[View Post]({post_url})")
                        elif post_id:
                            st.caption(f"ID: {post_id[:20]}...")
                    else:
                        st.caption("Posted (no URL/ID)")

                if row.get("content"):
                    with st.expander(f"Content preview"):
                        st.write(
                            row["content"][:200]
                            + ("..." if len(row.get("content", "")) > 200 else "")
                        )

                st.divider()

    except Exception as e:
        st.warning(f"Could not load posted_content: {e}")

    st.subheader("Rollups")
    try:
        # Persona rollup
        data = db.sb.client.rpc(
            "execute",  # fallback if no RPC; emulate via filters below
        )  # will raise; fallback below
    except Exception:
        try:
            q = (
                db.sb.client.table("posted_content")
                .select("persona_key, platform, posted_at")
                .gte("posted_at", since_iso)
            )
            rows = q.execute().data
            # simple in-Python rollup
            counts = {}
            for r in rows or []:
                pk = r.get("persona_key") or "(none)"
                counts[pk] = counts.get(pk, 0) + 1
            st.write({k: counts[k] for k in sorted(counts)})

            plat = {}
            for r in rows or []:
                p = r.get("platform") or "(none)"
                plat[p] = plat.get(p, 0) + 1
            st.write({k: plat[k] for k in sorted(plat)})
        except Exception as e:
            st.warning(f"Could not compute rollups: {e}")
