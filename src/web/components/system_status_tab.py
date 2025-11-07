#!/usr/bin/env python3
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
import time

from src.services.new_database_manager import NewDatabaseManager
from src.database.database_agent import DatabaseAgent
from src.services.cancel_manager import request_cancel, clear_cancel


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
    st.subheader("Controls")
    try:
        colx, coly, colz = st.columns(3)
        if colx.button("🛑 Stop Analysis", use_container_width=True):
            request_cancel("analysis")
            st.success("Analysis cancel requested")
        if coly.button("🛑 Stop Collections", use_container_width=True):
            request_cancel("all")
            st.success("Global cancel requested")
        if colz.button("✅ Clear Cancels", use_container_width=True):
            clear_cancel("analysis"); clear_cancel("all")
            st.success("Cancel flags cleared")
    except Exception as e:
        st.info(f"Controls unavailable: {e}")

    st.markdown("---")
    st.subheader("Quality Control & Monitoring")
    try:
        agent = DatabaseAgent()
        
        # Get quality metrics
        quality_24h = agent.get_quality_metrics(hours=24)
        quality_7d = agent.get_quality_metrics(hours=168)  # 7 days
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Avg Quality (24h)", f"{quality_24h.get('avg_quality', 0):.1f}/10")
        with col2:
            st.metric("Low Quality %", f"{quality_24h.get('low_quality_percentage', 0):.1f}%")
        with col3:
            st.metric("Avg Value (24h)", f"{quality_24h.get('avg_value', 0):.1f}/10")
        with col4:
            st.metric("Posts Analyzed", quality_24h.get('count', 0))
        
        # Quality trends
        if quality_24h.get('count', 0) > 0:
            trends = agent.get_quality_trends(days=7)
            if trends.get('quality'):
                st.markdown("**Quality Trends (7 days)**")
                import pandas as pd
                df_trends = pd.DataFrame({
                    'Quality Score': trends.get('quality', []),
                    'Value Score': trends.get('value', []),
                })
                if not df_trends.empty:
                    st.line_chart(df_trends)
        
        # Quality alerts
        if quality_24h.get('low_quality_percentage', 0) > 30:
            st.warning(f"⚠️ High percentage of low-quality posts: {quality_24h.get('low_quality_percentage', 0):.1f}%")
        if quality_24h.get('avg_quality', 0) < 5.0:
            st.error(f"❌ Average quality score is low: {quality_24h.get('avg_quality', 0):.1f}/10")
        
        # Backfill button for existing posts
        st.markdown("---")
        if st.button("🔄 Backfill Quality Metrics", help="Track quality metrics for existing posts"):
            with st.spinner("Backfilling quality metrics..."):
                try:
                    tracked = agent.backfill_quality_metrics(limit=1000)
                    st.success(f"✅ Tracked quality metrics for {tracked} posts")
                except Exception as e:
                    st.error(f"❌ Backfill failed: {e}")
        
    except Exception as e:
        st.info(f"Quality monitoring unavailable: {e}")
    
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
    with st.expander("Collection Freshness", expanded=False):
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

    st.markdown("---")
    st.subheader("Analyzer Performance & Fill Rate")
    try:
        from src.database.manager import SupabaseManager
        supabase = SupabaseManager()
        if supabase:
            # Get analyzer stats
            analyzed = supabase.client.table("posts").select("post_id").not_.is_("analyzed_at", "null").execute().data
            total = supabase.client.table("posts").select("post_id").execute().data
            analyzed_count = len(analyzed) if analyzed else 0
            total_count = len(total) if total else 0
            
            # Calculate fill rates for essential fields
            essential_fields = ['ai_summary', 'value_score', 'tags', 'key_concepts', 'topic', 'rewrite_score', 'best_persona_key']
            fill_stats = {}
            if analyzed_count > 0:
                sample = supabase.client.table("posts").select(",".join(essential_fields)).not_.is_("analyzed_at", "null").limit(100).execute().data
                for field in essential_fields:
                    filled = sum(1 for p in sample if p.get(field) not in (None, '', [], {})) if sample else 0
                    fill_stats[field] = (filled / len(sample) * 100) if sample else 0
            
            cols = st.columns(4)
            cols[0].metric("Analyzed Posts", f"{analyzed_count}/{total_count}")
            cols[1].metric("Analysis Rate", f"{(analyzed_count/total_count*100):.1f}%" if total_count > 0 else "0%")
            if fill_stats:
                avg_fill = sum(fill_stats.values()) / len(fill_stats) if fill_stats else 0
                cols[2].metric("Avg Fill Rate", f"{avg_fill:.1f}%")
                cols[3].metric("Completeness", "✅ Good" if avg_fill > 80 else "⚠️ Needs Work")
            
            with st.expander("Field Fill Rates", expanded=False):
                for field, rate in sorted(fill_stats.items(), key=lambda x: x[1]):
                    status = "✅" if rate > 80 else "⚠️" if rate > 50 else "❌"
                    st.progress(rate/100, text=f"{status} {field}: {rate:.1f}%")
        else:
            st.info("Supabase not available for analyzer metrics")
    except Exception as e:
        st.info(f"Analyzer metrics unavailable: {e}")
    
    st.markdown("---")
    st.subheader("ID Format Health")
    try:
        id_report = agent.id_format_report(sample_limit=1000)
        for plat, stats in id_report.items():
            bad = stats.get("bad", 0)
            checked = stats.get("checked", 0)
            if checked == 0:
                st.caption(f"{plat.title()}: n/a")
            else:
                status = "✅" if bad == 0 else "⚠️"
                st.caption(f"{status} {plat.title()}: {checked} checked, {bad} bad")
    except Exception as e:
        st.info(f"ID checks unavailable: {e}")

    # Cookie freshness
    with st.expander("Cookies", expanded=False):
        # Show freshest file among common locations
        cookie_paths = {
            "Twitter": ["config/twitter_cookies.json", "cookies/twitter_cookies.json"],
            "Threads": ["config/threads_cookies.json", "cookies/threads_cookies.json"],
        }
        now = time.time()
        for name, paths in cookie_paths.items():
            mtimes = []
            for pth in paths:
                p = Path(pth)
                if p.exists():
                    mtimes.append((pth, p.stat().st_mtime))
            if mtimes:
                freshest = min(mtimes, key=lambda x: now - x[1])
                age_min = int((now - freshest[1]) / 60)
                st.write(f"{name}: age ~{age_min} min ({freshest[0]})")
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

    st.markdown("---")
    st.subheader("Analyzer Performance")
    try:
        # Prefer Supabase for analyzer stats
        from src.database.manager import SupabaseManager
        sm = SupabaseManager()

        # Totals
        analyzed = sm.client.table("posts").select("id", count='exact').not_.is_("analyzed_at", "null").execute().count or 0
        unanalyzed = sm.client.table("posts").select("id", count='exact').is_("analyzed_at", "null").execute().count or 0

        # Recent window (24h)
        from datetime import datetime, timedelta
        since = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        recent = sm.client.table("posts").select("id", count='exact').gt("created_at", since).execute().count or 0

        # Averages
        rows = sm.client.table("posts").select("value_score,quality_score").not_.is_("analyzed_at", "null").order("created_at", desc=True).limit(1000).execute().data or []
        vs = [float(r.get("value_score") or 0) for r in rows]
        qs = [float(r.get("quality_score") or 0) for r in rows]
        avg_vs = round(sum(vs)/len(vs), 2) if vs else 0
        avg_qs = round(sum(qs)/len(qs), 2) if qs else 0

        # Model usage breakdown
        models = {}
        for r in (sm.client.table("posts").select("analysis_model").not_.is_("analyzed_at", "null").order("created_at", desc=True).limit(1000).execute().data or []):
            m = (r.get("analysis_model") or "").strip() or "unknown"
            models[m] = models.get(m, 0) + 1

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Analyzed", analyzed)
        c2.metric("Unanalyzed", unanalyzed)
        c3.metric("Avg Value (last 1k)", avg_vs)
        c4.metric("Avg Quality (last 1k)", avg_qs)

        if models:
            st.caption("Model usage (last 1k analyzed)")
            st.write({k: models[k] for k in sorted(models.keys())})
    except Exception as e:
        st.info(f"Analyzer metrics unavailable: {e}")


