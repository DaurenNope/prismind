import os
import streamlit as st
import requests


def badge(text: str, ok: bool) -> str:
    color = "#28a745" if ok else "#dc3545"
    return f"<span style='background:{color};color:#fff;padding:4px 8px;border-radius:6px;margin-right:8px;font-size:12px;'>{text}</span>"


def render_status_bar():
    supabase_ok = bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

    # Autoposter health (optional)
    auto_ok = False
    auto_url = os.getenv("AUTOMATION_URL", "http://127.0.0.1:8000")
    try:
        r = requests.get(f"{auto_url}/health", timeout=2)
        auto_ok = r.status_code == 200
    except Exception:
        auto_ok = False

    html = (
        badge("Supabase", supabase_ok)
        + badge("Autoposter", auto_ok)
    )
    st.markdown(f"<div style='margin:6px 0'>{html}</div>", unsafe_allow_html=True)


