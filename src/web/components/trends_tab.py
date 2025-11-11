#!/usr/bin/env python3
"""
Trends Tab - Proactive Content Suggestions
Analyzes database posts to identify trends and suggest content ideas
"""
import streamlit as st
from datetime import datetime

from src.services.new_database_manager import NewDatabaseManager
from src.intelligence.trend_analyzer import TrendAnalyzer


def render_trends_tab():
    st.header("📈 Trend Analysis & Content Suggestions")
    st.markdown("Analyze your database to discover trending topics and get content ideas")

    # Initialize session state
    if 'trends_data' not in st.session_state:
        st.session_state.trends_data = None
        st.session_state.last_analysis = None

    # Controls
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        if st.button("🔍 Analyze Trends", type="primary"):
            with st.spinner("Analyzing posts from database..."):
                # Load posts using NewDatabaseManager
                db = NewDatabaseManager()
                posts = db.get_posts(limit=200)  # Analyze recent 200 posts
                posts = [p for p in posts if p is not None]

                # Analyze trends
                analyzer = TrendAnalyzer()
                analysis = analyzer.analyze_trends(posts, time_window_hours=72)

                st.session_state.trends_data = analysis
                st.session_state.last_analysis = datetime.now()
                st.success(f"Analyzed {analysis['recent_posts']} posts from last 72 hours")
                st.rerun()

    with col2:
        time_window = st.selectbox("Time Window", ["24h", "72h", "7 days"], index=1)

    with col3:
        if st.session_state.last_analysis:
            st.caption(f"Last: {st.session_state.last_analysis.strftime('%H:%M')}")

    # Show analysis results
    if not st.session_state.trends_data:
        st.info("👆 Click 'Analyze Trends' to discover trending topics and get content suggestions")

        # Show what this feature does
        with st.expander("ℹ️ What does this do?"):
            st.markdown("""
            **Trend Analysis automatically:**
            - 📊 Identifies trending topics from your collected posts
            - 🎯 Matches trends with your opinions from config
            - 💡 Suggests content: "People are talking about X, you could say Y"
            - 🛡️ Filters out political and religious topics
            - 📝 Provides draft content you can edit and publish

            Perfect for staying relevant and proactive with your content!
            """)
        return

    analysis = st.session_state.trends_data

    # Stats row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Posts Analyzed", analysis['recent_posts'])
    with col2:
        st.metric("🔥 Trending Topics", len(analysis['trending_topics']))
    with col3:
        st.metric("💡 Content Ideas", len(analysis['content_suggestions']))
    with col4:
        st.metric("🛡️ Filtered Out", analysis['avoided_sensitive_topics'])

    st.divider()

    # Content Suggestions (Priority)
    if analysis['content_suggestions']:
        st.subheader("💡 Content Suggestions")
        st.markdown("**Trending topics matched with your opinions**")

        for idx, suggestion in enumerate(analysis['content_suggestions'], 1):
            with st.expander(f"💡 {idx}. {suggestion['trend'].upper()} ({suggestion['mentions']} mentions)", expanded=(idx == 1)):
                st.markdown(f"**📊 Observation:** {suggestion['observation']}")
                st.markdown(f"**🎯 Your Angle:** {suggestion['your_angle']}")

                st.markdown("**📝 Your Opinion:**")
                st.info(suggestion['your_opinion'][:300] + ("..." if len(suggestion['your_opinion']) > 300 else ""))

                st.markdown("**✨ Suggested Draft:**")
                draft = st.text_area(
                    "Edit and approve:",
                    suggestion['suggested_content'],
                    height=150,
                    key=f"draft_{idx}"
                )

                col1, col2 = st.columns([1, 3])
                with col1:
                    if st.button("✅ Approve & Schedule", key=f"approve_{idx}", type="primary"):
                        st.success("✅ Scheduled! (Will integrate with scheduler)")
                        # TODO: Integrate with PublishingScheduler

                st.markdown("**📌 What people are saying:**")
                for ex_idx, example in enumerate(suggestion['examples'], 1):
                    platform_emoji = {"twitter": "🐦", "threads": "🧵", "reddit": "🔴", "telegram": "✈️"}.get(example['platform'], "📄")
                    st.caption(f"{platform_emoji} {example['snippet'][:120]}...")

    else:
        st.warning("⚠️ No content suggestions yet. This happens when trending topics don't match your opinions in `config/opinions.json`")

    st.divider()

    # Trending Topics (Full List)
    if analysis['trending_topics']:
        st.subheader("🔥 All Trending Topics")
        st.markdown(f"*Top {len(analysis['trending_topics'])} topics from last {analysis['time_window_hours']} hours*")

        # Create columns for better layout
        cols = st.columns(2)

        for idx, topic in enumerate(analysis['trending_topics']):
            col = cols[idx % 2]

            with col:
                with st.container():
                    st.markdown(f"**{topic['keyword'].upper()}**")
                    st.caption(f"{topic['mention_count']} mentions")

                    # Show one example
                    if topic['examples']:
                        ex = topic['examples'][0]
                        platform_emoji = {"twitter": "🐦", "threads": "🧵", "reddit": "🔴", "telegram": "✈️"}.get(ex['platform'], "📄")
                        st.caption(f"{platform_emoji} {ex['snippet'][:80]}...")

                    st.markdown("---")

    else:
        st.info("No trending topics found in this time window")

    # Raw data (for debugging)
    with st.expander("🔧 Raw Analysis Data"):
        st.json(analysis)



