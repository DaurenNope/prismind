#!/usr/bin/env python3
"""
Dashboard Tab - Main Overview with Key Metrics and Quick Actions
"""

import streamlit as st

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import pandas as pd

from src.services.new_database_manager import NewDatabaseManager
from src.database.database_agent import DatabaseAgent
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def _parse_datetime(value: Any) -> Optional[datetime]:
    """Convert various timestamp formats to naive datetime."""
    if not value:
        return None

    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value

    try:
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(parsed):
            return None
        dt = parsed.to_pydatetime()
        return dt.replace(tzinfo=None)
    except Exception:
        return None


def render_dashboard_tab():
    """Render the main dashboard with overview metrics and quick actions"""
    # Load enhanced dashboard styles once per render
    st.markdown('<style>@import url("../styles/dashboard_enhancements.css");</style>', unsafe_allow_html=True)

    st.header("📊 Dashboard Overview")
    st.markdown("**Your intelligence hub - everything at a glance**")
    
    # Get database manager
    db = NewDatabaseManager()
    agent = DatabaseAgent()
    
    # Key Metrics Row
    st.subheader("📈 Key Metrics")
    
    # Get all posts for calculations
    all_posts = db.get_posts(limit=10000)
    total_posts = len(all_posts)
    
    # Calculate metrics
    analyzed_posts = [p for p in all_posts if p.get('analyzed_at') or p.get('ai_summary')]
    unanalyzed_posts = [p for p in all_posts if not (p.get('analyzed_at') or p.get('ai_summary'))]
    
    # Platform breakdown
    platform_counts = {}
    for post in all_posts:
        platform = post.get('platform', 'unknown')
        platform_counts[platform] = platform_counts.get(platform, 0) + 1
    
    # Quality metrics - handle non-numeric values
    quality_scores = []
    for p in analyzed_posts:
        qs = p.get('quality_score')
        if qs:
            try:
                quality_scores.append(float(qs))
            except (ValueError, TypeError):
                # Skip non-numeric quality scores
                pass
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
    
    value_scores = []
    for p in analyzed_posts:
        vs = p.get('value_score')
        if vs:
            try:
                value_scores.append(float(vs))
            except (ValueError, TypeError):
                # Skip non-numeric value scores
                pass
    avg_value = sum(value_scores) / len(value_scores) if value_scores else 0
    
    # Recent activity (last 24 hours)
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    recent_posts = []
    for post in all_posts:
        created_dt = _parse_datetime(post.get('created_at'))
        if created_dt and created_dt > yesterday:
            recent_posts.append(post)
    
    # Display metrics in cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{total_posts}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">📚 Total Posts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        analyzed_pct = int((len(analyzed_posts) / total_posts * 100)) if total_posts > 0 else 0
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{len(analyzed_posts)}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">🤖 Analyzed ({analyzed_pct}%)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{len(unanalyzed_posts)}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">⏳ Pending Analysis</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{len(recent_posts)}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">🕐 Last 24h</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        st.markdown(f"""
        <div style="background-color: #f9fafb; border: 1px solid #e5e7eb;
                    padding: 1.5rem; border-radius: 12px; color: #111827; text-align: center;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
            <div style="font-size: 2rem; font-weight: 700; margin-bottom: 0.5rem; color: #111827;">{len(platform_counts)}</div>
            <div style="font-size: 0.875rem; color: #6b7280;">🌐 Platforms</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # Platform Breakdown (compact)
    st.subheader("📊 Platform Breakdown")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Platform distribution chart
        if platform_counts:
            sorted_items = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)
            # Show only top 8 in the chart for readability
            top_items = sorted_items[:8]
            platform_df = pd.DataFrame([
                {'Platform': k.title(), 'Count': v}
                for k, v in top_items
            ])
            st.bar_chart(platform_df.set_index('Platform'), use_container_width=True)
    
    with col2:
        # Quality metrics
        st.markdown("**Quality Metrics**")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Avg Quality Score", f"{avg_quality:.1f}/10" if avg_quality > 0 else "N/A")
        with col_b:
            st.metric("Avg Value Score", f"{avg_value:.1f}/10" if avg_value > 0 else "N/A")
        
        # Platform list (preview + full in expander)
        st.markdown("**Platforms (top 8):**")
        sorted_items = sorted(platform_counts.items(), key=lambda x: x[1], reverse=True)
        preview = sorted_items[:8]
        remaining = sorted_items[8:]

        for platform, count in preview:
            platform_emoji = {
                'threads': '🧵',
                'twitter': '🐦',
                'reddit': '📱',
                'github': '💻',
                'telegram': '📢',
            }.get(str(platform).lower(), '📄')
            st.markdown(f"{platform_emoji} **{str(platform).title()}**: {count} posts")

        if remaining:
            with st.expander("Show all platforms", expanded=False):
                for platform, count in remaining:
                    platform_emoji = {
                        'threads': '🧵',
                        'twitter': '🐦',
                        'reddit': '📱',
                        'github': '💻',
                        'telegram': '📢',
                    }.get(str(platform).lower(), '📄')
                    st.markdown(f"{platform_emoji} **{str(platform).title()}**: {count} posts")
    
    st.divider()
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📥 Collect New Posts", use_container_width=True, type="primary"):
            st.session_state.quick_action = "collect"
            st.rerun()
    
    with col2:
        if st.button("🤖 Analyze Pending", use_container_width=True, type="primary"):
            st.session_state.quick_action = "analyze"
            st.rerun()
    
    with col3:
        if st.button("🔍 Quality Check", use_container_width=True, type="secondary"):
            st.session_state.quick_action = "quality_check"
            st.rerun()
    
    with col4:
        if st.button("📊 View Feed", use_container_width=True, type="secondary"):
            st.session_state.quick_action = "feed"
            st.rerun()
    
    st.divider()
    
    # Recent Activity
    st.subheader("🕐 Recent Activity")
    
    if recent_posts:
        st.info(f"**{len(recent_posts)} posts collected in the last 24 hours**")
        
        # Show recent posts in a table
        recent_data = []
        for post in recent_posts[:10]:  # Show last 10
            created_dt = _parse_datetime(post.get('created_at'))
            if created_dt:
                time_delta = now - created_dt
                seconds = max(int(time_delta.total_seconds()), 0)
                if seconds >= 3600:
                    time_str = f"{seconds // 3600}h ago"
                elif seconds >= 60:
                    time_str = f"{seconds // 60}m ago"
                else:
                    time_str = "Just now"
            else:
                time_str = "Unknown"
            
            recent_data.append({
                'Platform': post.get('platform', 'unknown').title(),
                'Author': post.get('author', 'Unknown')[:30],
                'Content': (post.get('content', '') or post.get('ai_summary', ''))[:50] + '...' if (post.get('content') or post.get('ai_summary')) else 'No content',
                'Time': time_str,
                'Analyzed': '✅' if post.get('analyzed_at') or post.get('ai_summary') else '⏳',
            })
        
        if recent_data:
            df_recent = pd.DataFrame(recent_data)
            st.dataframe(df_recent, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity in the last 24 hours. Start collecting posts!")
    
    st.divider()
    
    # System Health
    st.subheader("🩺 System Health")
    
    try:
        quality_metrics = agent.get_quality_metrics()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_q = quality_metrics.get('avg_quality_score', 0)
            st.metric("Avg Quality", f"{avg_q:.1f}/10" if avg_q > 0 else "N/A")
        
        with col2:
            low_q_pct = quality_metrics.get('low_quality_percentage', 0)
            st.metric("Low Quality %", f"{low_q_pct:.1f}%")
            if low_q_pct > 20:
                st.warning("⚠️ High percentage of low quality posts")
        
        with col3:
            avg_v = quality_metrics.get('avg_value_score', 0)
            st.metric("Avg Value", f"{avg_v:.1f}/10" if avg_v > 0 else "N/A")
        
        with col4:
            analyzed_count = quality_metrics.get('analyzed_count', 0)
            st.metric("Analyzed Posts", analyzed_count)
    
    except Exception as e:
        logger.warning(f"Failed to get quality metrics: {e}")
        st.info("Quality metrics unavailable")
    
    # Action handlers
    if st.session_state.get("quick_action") == "collect":
        st.session_state.quick_action = None
        st.info("💡 Navigate to the **Collect** tab to start collecting posts")
    
    elif st.session_state.get("quick_action") == "analyze":
        st.session_state.quick_action = None
        st.info("💡 Navigate to the **Analysis** tab to analyze pending posts")
    
    elif st.session_state.get("quick_action") == "quality_check":
        st.session_state.quick_action = None
        st.info("💡 Navigate to the **System** tab for quality control tools")
    
    elif st.session_state.get("quick_action") == "feed":
        st.session_state.quick_action = None
        st.info("💡 Navigate to the **Feed** tab to view your content feed")

