#!/usr/bin/env python3
import streamlit as st
from datetime import datetime
from pathlib import Path

from src.services.new_database_manager import NewDatabaseManager
from src.database.database_agent import DatabaseAgent


def render_system_status_tab():
    st.header("🩺 System Status")

    ok = True

    # Supabase ping
    try:
        db = NewDatabaseManager()
        _ = db.get_posts(limit=1)
        st.success("Supabase: OK")
    except Exception as e:
        ok = False
        st.error(f"Supabase: FAIL - {e}")

    st.markdown("---")
    st.subheader("Database Health & Activity")
    try:
        agent = DatabaseAgent()
        health = agent.health_report()
        activity_60 = agent.recent_activity(minutes=60)
        cols = st.columns(3)
        cols[0].metric("Supabase", "OK" if health.get("supabase_ok") else "FAIL")
        cols[1].metric("SQLite", "OK" if health.get("sqlite_ok") else "FAIL")
        latest_ids = health.get("latest_ids", {})
        cols[2].caption(f"Latest IDs: Tw={latest_ids.get('twitter') or '-'} Rd={latest_ids.get('reddit') or '-'} Th={latest_ids.get('threads') or '-'}")

        st.caption(f"Recent activity (60m) → Twitter: {activity_60.get('twitter',0)} | Reddit: {activity_60.get('reddit',0)} | Threads: {activity_60.get('threads',0)}")
    except Exception as e:
        st.info(f"Health unavailable: {e}")

    st.markdown("---")
    st.subheader("Collection Freshness")
    try:
        # Threshold controls (session-local)
        if "freshness_thresholds" not in st.session_state:
            st.session_state.freshness_thresholds = {"twitter": 180, "reddit": 180, "threads": 180}
        col_t, col_r, col_th = st.columns(3)
        st.session_state.freshness_thresholds["twitter"] = col_t.number_input("Twitter threshold (min)", min_value=30, max_value=1440, value=int(st.session_state.freshness_thresholds["twitter"]))
        st.session_state.freshness_thresholds["reddit"] = col_r.number_input("Reddit threshold (min)", min_value=30, max_value=1440, value=int(st.session_state.freshness_thresholds["reddit"]))
        st.session_state.freshness_thresholds["threads"] = col_th.number_input("Threads threshold (min)", min_value=30, max_value=1440, value=int(st.session_state.freshness_thresholds["threads"]))
        thresholds = dict(st.session_state.freshness_thresholds)
        metrics_rows = []
        for plat in ["twitter", "reddit", "threads"]:
            m = agent.get_collection_metrics(plat) or {}
            metrics_rows.append({
                "platform": plat,
                "last_run_at": m.get("last_run_at") or "-",
                "last_count": m.get("last_count") or 0,
                "last_success": bool(m.get("last_success")) if m.get("last_success") is not None else False,
                "consecutive_failures": m.get("consecutive_failures") or 0,
            })
        st.dataframe(metrics_rows, hide_index=True, use_container_width=True)

        stale = agent.detect_stale_collections(thresholds)
        if stale:
            st.warning("Stale platforms detected:")
            for k, v in stale.items():
                st.caption(f" - {k}: {v['age_minutes']} min (threshold {v['threshold']} min)")
            col_a, col_b = st.columns(2)
            if col_a.button("🔔 Notify Stale", use_container_width=True):
                agent.notify_stale(stale)
                st.success("Notifications sent (or logged)")
            if col_b.button("⚙️ Trigger Collections", use_container_width=True):
                import asyncio
                res = asyncio.run(agent.trigger_collections(list(stale.keys())))
                st.success(f"Triggered: {res}")
        else:
            st.success("All platforms fresh within thresholds")
    except Exception as e:
        st.info(f"Freshness unavailable: {e}")

    # Cookie freshness
    st.subheader("Cookies")
    for name, path in [("Twitter", "config/twitter_cookies.json"), ("Threads", "config/threads_cookies.json")]:
        p = Path(path)
        if p.exists():
            age_min = int((datetime.now().timestamp() - p.stat().st_mtime) / 60)
            st.write(f"{name}: age ~{age_min} min")
        else:
            st.warning(f"{name}: missing")

    # Posting queue summary
    st.subheader("Queue")
    try:
        from src.database.publishing.bridge import MimesisDB
        pdb = MimesisDB()
        scheduled = pdb.list_scheduled_posts()
        pending = len([p for p in scheduled if p.get('status') == 'pending'])
        retry = len([p for p in scheduled if p.get('status') == 'retry'])
        posted = len([p for p in scheduled if p.get('status') == 'posted'])
        st.write(f"Pending: {pending} | Retry: {retry} | Posted: {posted}")

        # Error surface: show retry items (possible failures)
        failing = [
            {
                'id': p.get('id'),
                'platform': p.get('platform'),
                'scheduled_time': p.get('scheduled_time'),
                'status': p.get('status'),
                'error': p.get('error') or p.get('last_error')
            }
            for p in scheduled if p.get('status') == 'retry'
        ][:25]
        if failing:
            st.subheader("Recent Failures / Retries")
            st.dataframe(failing, use_container_width=True)
    except Exception:
        st.info("Queue unavailable")

    if ok:
        st.success("Overall: GREEN")
    else:
        st.warning("Overall: ATTENTION NEEDED")


