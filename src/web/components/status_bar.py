import os
import streamlit as st
import requests


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

    st.markdown(f"""
    <div style="display: flex; gap: 0.75rem; align-items: center; padding: 0.75rem 1rem;
                background: #f8fafc; border-radius: 12px; margin-bottom: 1rem; border: 1px solid #e2e8f0;">
        <span class="status-badge {'success' if supabase_ok else 'error'}">
            {'✅' if supabase_ok else '❌'} Supabase
        </span>
        <span class="status-badge {'success' if auto_ok else 'error'}">
            {'✅' if auto_ok else '❌'} Autoposter
        </span>
    </div>
    """, unsafe_allow_html=True)


