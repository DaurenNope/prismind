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
