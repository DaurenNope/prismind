import streamlit as st
from typing import List, Optional
from datetime import datetime

from src.utils.diary_storage import DiaryStorage
from src.core.discovery.profile_manager import ProfileManager


def render_diary_tab():
    st.subheader("📓 Builder Diary")
    st.caption("Drop quick updates so the system can personalize analysis and suggestions.")

    storage = DiaryStorage()
    # Load profiles for dropdown (fallback to text input if none)
    try:
        pm = ProfileManager()
        profiles = pm.list_profiles()
        profile_options = [""] + [f"{p.get('id')} — {p.get('emoji') or ''} {p.get('name') or ''}".strip() for p in profiles]
        id_by_label = {profile_options[i]: (profiles[i-1].get("id") if i > 0 else "") for i in range(len(profile_options))}
    except Exception:
        profiles = []
        profile_options = [""]
        id_by_label = { "": "" }

    with st.form("diary_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2,2,1])
        with col1:
            if profiles:
                use_active = st.checkbox("Use active profile", value=True, help="Pull from Profile Manager's active profile")
                if use_active:
                    try:
                        active = pm.get_active_profile()
                        profile_key = (active or {}).get("id") or None
                        st.text_input("Profile (active)", value=profile_key or "", disabled=True)
                    except Exception:
                        profile_key = None
                else:
                    selected_label = st.selectbox("Profile (optional)", options=profile_options, index=0)
                    profile_key = id_by_label.get(selected_label) or None
            else:
                profile_key = st.text_input("Profile (optional)", placeholder="e.g. defi_protocol_alpha").strip() or None
        with col2:
            tags_text = st.text_input("Tags (optional)", placeholder="comma-separated, e.g. onboarding,metrics")
        with col3:
            limit_preview = st.number_input("Show", min_value=5, max_value=200, value=50, step=5)

        shipped = st.text_area("What did you ship or learn?", height=100, placeholder="Short note about today’s progress")
        blockers = st.text_area("Any blockers?", height=80, placeholder="Optional")
        focus = st.text_area("What’s your current focus?", height=80, placeholder="Optional")

        submitted = st.form_submit_button("Save Entry")
        if submitted and shipped.strip():
            tags = [t.strip() for t in (tags_text or "").split(",") if t.strip()]
            storage.add_entry(
                shipped=shipped,
                profile_key=profile_key,
                blockers=blockers,
                focus=focus,
                tags=tags or None,
            )
            st.success("Saved diary entry.")
            st.rerun()

    st.divider()
    st.markdown("### Recent Entries")
    st.caption("Manage profiles in the Profiles tab to keep diary tied to the right context.")

    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        if profiles:
            selected_filter_label = st.selectbox("Filter by profile", options=profile_options, index=0, key="diary_filter_profile")
            filter_profile = id_by_label.get(selected_filter_label) or None
        else:
            filter_profile = st.text_input("Filter by profile", placeholder="Leave empty to show all").strip() or None
    with filter_col2:
        limit = limit_preview

    entries = storage.load_entries(profile_key=(filter_profile or None), limit=int(limit))

    if not entries:
        st.info("No diary entries yet. Add your first update above.")
        return

    for idx, e in enumerate(entries):
        with st.expander(f"{e.get('timestamp', '')} • {e.get('profile_key') or 'all-profiles'}"):
            st.write(f"**Shipped / Learned**")
            st.write(e.get("shipped") or "")

            if e.get("focus"):
                st.write("")
                st.write(f"**Focus**")
                st.write(e.get("focus"))

            if e.get("blockers"):
                st.write("")
                st.write(f"**Blockers**")
                st.write(e.get("blockers"))

            tags = e.get("tags") or []
            if tags:
                st.caption("Tags: " + ", ".join(tags))


