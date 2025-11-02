import streamlit as st
from datetime import datetime, timedelta, timezone

from src.database.publishing.bridge import MimesisDB
from src.publishing.services.personalities import get_persona_keys


def render():
    st.header("Editor: Review, Edit, Approve")
    db = MimesisDB()

    persona_keys = get_persona_keys()
    persona = st.selectbox("Persona", ["(all)"] + persona_keys, index=0)
    only_ready = st.checkbox("Show ready only", value=False)
    search = st.text_input("Search text")

    rows = db.list_transformations(
        None if persona == "(all)" else persona, ready_only=only_ready
    )
    if search:
        q = search.lower().strip()
        rows = [
            r
            for r in rows
            if q in (r.get("content") or "").lower()
            or q in (r.get("persona_key") or "").lower()
        ]

    if not rows:
        st.info("No transformations found.")
        return

    selected_ids = []
    for r in rows[:200]:
        with st.expander(
            f"#{r.get('id')} · {r.get('persona_key')} · {r.get('platform')}"
        ):
            content_key = f"content_{r['id']}"
            ready_key = f"ready_{r['id']}"
            new_content = st.text_area(
                "Content", r.get("content") or "", key=content_key
            )
            ready_flag = st.checkbox(
                "Ready for posting",
                value=bool(r.get("ready_for_posting")),
                key=ready_key,
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Save", key=f"save_{r['id']}"):
                    db.update_transformation(
                        r["id"],
                        {"content": new_content, "ready_for_posting": ready_flag},
                    )
                    st.success("Saved")
            with col2:
                if st.checkbox("Select for approval", key=f"sel_{r['id']}"):
                    selected_ids.append(r["id"])

    st.subheader("Approve → Schedule")
    platform = st.selectbox("Platform", ["twitter", "threads", "telegram"])  # noqa: E501
    when_minutes = st.slider("Schedule in minutes", 0, 240, 10)
    if st.button("Approve selected and schedule"):
        if not selected_ids:
            st.warning("No items selected.")
            return
        dt = datetime.now(timezone.utc) + timedelta(minutes=when_minutes)
        approved = db.approve_to_schedule(selected_ids, platform, dt.isoformat())
        st.success(f"Approved and scheduled {len(approved)} item(s).")
