from datetime import datetime, timedelta, timezone

import streamlit as st

from src.database.publishing.bridge import MimesisDB
from src.publishing.services.transformer import PersonaGenerator
from src.publishing.services.personalities import get_persona_keys
from src.web.components.tabs import get_database_manager  # reuse existing cache


def render():
    st.header("Queue → Schedule (Quick)")
    persona_keys = get_persona_keys()
    if persona_keys:
        persona = st.selectbox("Persona", persona_keys, index=0)
    else:
        persona = st.text_input("Persona key", "skeptical_builder")
    platform = st.selectbox("Platform", ["twitter", "threads", "telegram"])  # noqa: E501
    content = st.text_area("Content", "Hello world from Prismind + Mimesis")
    when = st.slider("Schedule in minutes", 0, 120, 1)

    if st.button("Schedule test post"):
        try:
            db = MimesisDB()
            dt = datetime.now(timezone.utc) + timedelta(minutes=when)
            # Use personality_key to match database schema
            # content_type: 'single_tweet' for twitter/threads, 'telegram_message' for telegram
            content_type_map = {
                "twitter": "single_tweet",
                "threads": "single_tweet",
                "telegram": "telegram_message",
            }
            payload = {
                "personality_key": persona,  # Support both schema variants
                "persona_key": persona,
                "platform": platform,
                "content": content,
                "content_type": content_type_map.get(
                    platform, "single_tweet"
                ),  # Required by DB
                "scheduled_time": dt.isoformat(),  # Mimesis uses scheduled_time, not scheduled_at
            }
            row = db.insert_scheduled(payload)
            scheduled_time_display = row.get("scheduled_time") or row.get(
                "scheduled_at", "unknown"
            )
            st.success(f"Scheduled {row['id']} at {scheduled_time_display}")
        except ConnectionError as e:
            st.error(f"⚠️ {str(e)}")
            st.info(
                "This usually means Supabase is temporarily down. Check https://status.supabase.com"
            )
        except Exception as e:
            st.error(f"Failed to schedule post: {str(e)}")

    st.divider()
    st.subheader("Generate from Posts → Transformations (Approve later)")
    gen_persona = st.text_input("Persona for generation", persona)
    gen_platform = st.selectbox(
        "Platform for generation",
        ["twitter", "threads", "telegram"],
        index=["twitter", "threads", "telegram"].index(platform),
    )
    limit = st.slider("Max source posts", 1, 50, 5)
    use_recent_only = st.checkbox("Use most recent posts only", value=True)

    if st.button("Generate transformations"):
        dbm = get_database_manager()
        posts = []
        try:
            posts = dbm.get_posts(limit=limit)
        except Exception as exc:
            st.error(f"Unable to load posts for generation: {exc}")
            return
        if not posts:
            st.info("No source posts available.")
            return
        if use_recent_only:
            # best effort: already limited by get_posts order; else sort here
            pass

        gen = PersonaGenerator()
        created = gen.generate_transformations(gen_persona or persona, posts)
        st.success(
            f"Generated {len(created)} transformation(s). Review in Editor tab (coming next)."
        )

    st.subheader("(Optional) Generate and schedule directly")
    gen_when = st.slider(
        "Schedule generated posts in minutes", 0, 240, max(when, 5), key="sched_slider"
    )
    if st.button("Generate and schedule now"):
        dbm = get_database_manager()
        posts = dbm.get_posts(limit=limit) or []
        gen = PersonaGenerator()
        created = gen.generate_and_schedule(
            gen_persona or persona, gen_platform, posts, schedule_in_minutes=gen_when
        )
        st.success(f"Generated and scheduled {len(created)} post(s).")
