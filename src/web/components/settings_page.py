import os
import streamlit as st


def render_settings_page():
    st.title("⚙️ Settings")

    st.subheader("Environment")
    st.text_input("SUPABASE_URL", os.getenv("SUPABASE_URL", ""), disabled=True)

    st.subheader("Appearance")
    theme = st.selectbox("Theme", ["System", "Light", "Dark"], index=0)
    spacing = st.slider("Content spacing", 0, 24, 8)
    st.caption("These control the current session only.")

    st.subheader("Shortcuts")
    st.markdown("- Publishing flow: Generate → Approve → Schedule → Post")
    st.markdown("- Collectors run from Collect tab")


