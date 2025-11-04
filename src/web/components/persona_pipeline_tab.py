#!/usr/bin/env python3
import streamlit as st
import asyncio
from typing import List

from src.pipeline.full_automation_loop import FullAutomationLoop
from src.publishing.worker import get_publisher_worker
from src.services.new_database_manager import NewDatabaseManager


def render_persona_pipeline_tab():
    if "publisher_running" not in st.session_state:
        st.session_state.publisher_running = False

    st.header("🎭 Persona Pipeline")

    loop = FullAutomationLoop()
    db = NewDatabaseManager()

    st.subheader("Controls")
    col1, col2, col3 = st.columns(3)

    with col1:
        platforms = st.multiselect(
            "Platforms",
            options=["twitter", "reddit", "threads"],
            default=["twitter", "reddit", "threads"],
        )
        min_match = st.slider("Min match score", 0.0, 1.0, 0.70, 0.01)
        schedule_min = st.slider("Schedule in (minutes)", 1, 180, 45, 1)
        analyze_limit = st.number_input("Analyze limit (0 = all)", 0, 5000, 0, 10)

    with col2:
        if st.button("📥 Collect", use_container_width=True):
            try:
                with st.spinner("Collecting..."):
                    results = asyncio.run(loop.run_collection(platforms=platforms or None))
                st.success(f"Collected: {sum(results.values())} total")
                st.json(results)
            except Exception as e:
                st.error(f"Collect failed: {e}")

        if st.button("🧠 Analyze", use_container_width=True):
            try:
                with st.spinner("Analyzing..."):
                    res = asyncio.run(loop.run_analysis(limit=(analyze_limit or None)))
                st.success(f"Analyzed: {res.get('analyzed', 0)}")
                st.json(res)
            except Exception as e:
                st.error(f"Analyze failed: {e}")

        if st.button("✍️ Generate + Schedule", use_container_width=True):
            try:
                with st.spinner("Transforming & scheduling..."):
                    res = asyncio.run(loop.run_transformation_and_scheduling(
                        min_match_score=min_match,
                        schedule_minutes=schedule_min
                    ))
                st.success(f"Transformed {res.get('transformed', 0)}, scheduled {res.get('scheduled', 0)}")
                st.json(res)
            except Exception as e:
                st.error(f"Transform/Schedule failed: {e}")

    with col3:
        if st.button(("🟢 Stop Publisher" if st.session_state.publisher_running else "🚀 Start Publisher"),
                     use_container_width=True):
            worker = get_publisher_worker()
            try:
                if st.session_state.publisher_running:
                    worker.stop()
                    st.session_state.publisher_running = False
                    st.success("Publisher stopped")
                else:
                    worker.start()
                    st.session_state.publisher_running = True
                    st.success("Publisher started")
            except Exception as e:
                st.error(f"Publisher control failed: {e}")

        if st.button("🔁 Retry failed posts", use_container_width=True):
            try:
                db.sb.client.table("scheduled_posts").update({"status": "pending"}).in_("status", ["failed","retry"]).execute()
                st.success("Set failed/retry posts back to pending")
            except Exception as e:
                st.error(f"Retry setup failed: {e}")

    st.markdown("---")
    st.subheader("📊 Status")
    try:
        pending = db.sb.client.table("scheduled_posts").select("id").eq("status","pending").execute().data
        retry = db.sb.client.table("scheduled_posts").select("id").eq("status","retry").execute().data
        posted = db.sb.client.table("scheduled_posts").select("id").eq("status","posted").limit(20).order("scheduled_time", desc=True).execute().data
        st.write(f"Pending: {len(pending)} | Retry: {len(retry)} | Recently posted: {len(posted)}")
    except Exception:
        st.info("Supabase not configured or unavailable.")

    st.markdown("---")
    st.subheader("🔎 Queue preview")
    try:
        queue = db.sb.client.table("scheduled_posts").select("*").in_("status", ["pending","retry"]).order("scheduled_time").limit(25).execute().data
        st.dataframe(queue, use_container_width=True)
    except Exception:
        st.info("Queue unavailable.")


