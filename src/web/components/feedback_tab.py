"""
Feedback Tab Component

Provides UI for rating and reviewing rewrites.
"""

import streamlit as st
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def render_feedback_tab():
    """Render the feedback and review interface"""

    st.header("📝 Rewrite Feedback & Review")

    # Import feedback tracker
    try:
        from src.publishing.feedback_tracker import FeedbackTracker
        tracker = FeedbackTracker()
    except Exception as e:
        st.error(f"Failed to initialize feedback tracker: {e}")
        return

    # Create tabs for different views
    tab1, tab2, tab3 = st.tabs(["📊 Statistics", "✍️ Rate Rewrites", "🎯 Learning Insights"])

    # Tab 1: Statistics
    with tab1:
        render_feedback_stats(tracker)

    # Tab 2: Rate Rewrites
    with tab2:
        render_rating_interface(tracker)

    # Tab 3: Learning Insights
    with tab3:
        render_learning_insights(tracker)


def render_feedback_stats(tracker):
    """Render feedback statistics"""

    st.subheader("📊 Feedback Statistics")

    # Time range selector
    col1, col2 = st.columns([3, 1])
    with col1:
        days_back = st.selectbox(
            "Time Range",
            options=[7, 30, 90, 365],
            format_func=lambda x: f"Last {x} days",
            index=1
        )

    with col2:
        if st.button("🔄 Refresh Stats", use_container_width=True):
            st.rerun()

    # Get statistics
    with st.spinner("Loading feedback statistics..."):
        stats = asyncio.run(tracker.get_feedback_stats(days_back=days_back))

    if stats.get('error'):
        st.error(f"Error loading stats: {stats['error']}")
        return

    # Display overview metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Feedback", stats.get('total_count', 0))

    with col2:
        avg_rating = stats.get('avg_rating', 0)
        st.metric("Avg Rating", f"{avg_rating:.2f} ⭐")

    with col3:
        approval_rate = stats.get('approval_rate', 0)
        st.metric("Approval Rate", f"{approval_rate:.1f}%")

    with col4:
        approvals = stats.get('approvals', 0)
        rejections = stats.get('rejections', 0)
        st.metric("Approvals", f"👍 {approvals} / 👎 {rejections}")

    st.divider()

    # Rating distribution
    if stats.get('rating_distribution'):
        st.subheader("Rating Distribution")

        rating_dist = stats['rating_distribution']

        # Sort by rating
        sorted_ratings = sorted(rating_dist.items())

        # Display as bar chart
        import pandas as pd
        df = pd.DataFrame(sorted_ratings, columns=['Rating', 'Count'])
        st.bar_chart(df.set_index('Rating'), use_container_width=True)

    # Feedback types
    if stats.get('feedback_types'):
        st.subheader("Feedback Types")

        feedback_types = stats['feedback_types']

        cols = st.columns(len(feedback_types))
        for i, (ftype, count) in enumerate(feedback_types.items()):
            with cols[i]:
                st.metric(ftype.title(), count)


def render_rating_interface(tracker):
    """Render interface for rating rewrites"""

    st.subheader("✍️ Rate Recent Rewrites")

    st.info("""
    Rate the quality of rewrites to help improve the system.
    Your feedback will be used to learn what works and what doesn't.
    """)

    # Simple rating form
    with st.form("rating_form", clear_on_submit=True):
        st.write("### Rate a Rewrite")

        rewrite_id = st.text_input(
            "Rewrite ID",
            placeholder="Enter rewrite ID (from logs or database)",
            help="Unique identifier for the rewrite you want to rate"
        )

        # Rating type selector
        rating_type = st.radio(
            "Rating Type",
            options=["thumbs", "stars"],
            format_func=lambda x: "👍 / 👎 Thumbs" if x == "thumbs" else "⭐ Stars (1-5)",
            horizontal=True
        )

        if rating_type == "thumbs":
            rating_value = st.radio(
                "Your Rating",
                options=[-1, 1],
                format_func=lambda x: "👍 Approve" if x == 1 else "👎 Reject",
                horizontal=True
            )
        else:
            rating_value = st.slider("Rating", min_value=1, max_value=5, value=3)

        notes = st.text_area(
            "Feedback Notes (Optional)",
            placeholder="What did you like or dislike about this rewrite?",
            help="Provide specific feedback to help improve future rewrites"
        )

        # Metadata (optional)
        with st.expander("📋 Additional Information (Optional)"):
            col1, col2 = st.columns(2)
            with col1:
                persona = st.text_input("Persona", placeholder="e.g., qronoya")
                content_type = st.text_input("Content Type", placeholder="e.g., insight")
            with col2:
                platform = st.text_input("Platform", placeholder="e.g., twitter")
                length = st.number_input("Length", min_value=0, value=0)

        submitted = st.form_submit_button("💾 Submit Feedback", use_container_width=True)

        if submitted:
            if not rewrite_id:
                st.error("⚠️ Please enter a rewrite ID")
            else:
                # Prepare metadata
                metadata = {}
                if persona:
                    metadata['persona'] = persona
                if platform:
                    metadata['platform'] = platform
                if content_type:
                    metadata['content_type'] = content_type
                if length > 0:
                    metadata['length'] = length

                # Store feedback
                with st.spinner("Saving feedback..."):
                    feedback_type = "thumbs" if rating_type == "thumbs" else "rating"
                    record_id = asyncio.run(tracker.store_feedback(
                        rewrite_id=rewrite_id,
                        rating=rating_value,
                        feedback_type=feedback_type,
                        notes=notes if notes else None,
                        metadata=metadata if metadata else None
                    ))

                if record_id:
                    st.success(f"✅ Feedback saved! (ID: {record_id})")
                else:
                    st.error("❌ Failed to save feedback")

    st.divider()

    # Recent feedback
    st.subheader("📜 Recent Feedback")

    # This would ideally show recent feedback entries
    # For now, show a placeholder
    st.info("Recent feedback entries will appear here")


def render_learning_insights(tracker):
    """Render learning insights from feedback"""

    st.subheader("🎯 Learning Insights")

    st.info("""
    Analyze feedback to learn patterns and improve rewrite quality.
    Compare what users approve vs reject to identify successful strategies.
    """)

    # Persona/platform selector
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        persona = st.selectbox(
            "Persona",
            options=["", "qronoya", "aspandead", "claimzilla"],
            format_func=lambda x: "All Personas" if x == "" else x.title()
        )

    with col2:
        platform = st.selectbox(
            "Platform",
            options=["", "twitter", "threads", "telegram"],
            format_func=lambda x: "All Platforms" if x == "" else x.title()
        )

    with col3:
        analyze_btn = st.button("🔍 Analyze", use_container_width=True)

    if analyze_btn:
        if not persona or not platform:
            st.warning("⚠️ Please select both persona and platform for analysis")
        else:
            with st.spinner("Analyzing feedback patterns..."):
                insights = asyncio.run(tracker.learn_from_feedback(
                    persona=persona,
                    platform=platform
                ))

            if insights.get('error'):
                st.error(f"Error analyzing feedback: {insights['error']}")
                return

            # Display results
            col1, col2 = st.columns(2)

            with col1:
                st.metric("✅ Approved Rewrites", insights.get('approved_count', 0))

            with col2:
                st.metric("❌ Rejected Rewrites", insights.get('rejected_count', 0))

            st.divider()

            # Approved patterns
            if insights.get('approved_patterns'):
                st.subheader("✅ What Users Like")
                approved = insights['approved_patterns']

                if 'content_types' in approved:
                    st.write("**Content Types:**")
                    for ctype, count in approved['content_types'].items():
                        st.write(f"- {ctype}: {count} occurrences")

                if 'avg_length' in approved:
                    st.write(f"**Average Length:** {approved['avg_length']} characters")

                if 'emoji_usage' in approved:
                    emoji_pct = approved['emoji_usage'] * 100
                    st.write(f"**Emoji Usage:** {emoji_pct:.0f}%")

            st.divider()

            # Rejected patterns
            if insights.get('rejected_patterns'):
                st.subheader("❌ What Users Dislike")
                rejected = insights['rejected_patterns']

                if 'content_types' in rejected:
                    st.write("**Content Types:**")
                    for ctype, count in rejected['content_types'].items():
                        st.write(f"- {ctype}: {count} occurrences")

                if 'avg_length' in rejected:
                    st.write(f"**Average Length:** {rejected['avg_length']} characters")

                if 'emoji_usage' in rejected:
                    emoji_pct = rejected['emoji_usage'] * 100
                    st.write(f"**Emoji Usage:** {emoji_pct:.0f}%")

            st.divider()

            # Suggestions
            if insights.get('suggestions'):
                st.subheader("💡 Improvement Suggestions")
                for suggestion in insights['suggestions']:
                    st.write(f"- {suggestion}")
            else:
                st.info("Not enough data to generate suggestions yet. Keep providing feedback!")

    st.divider()

    # Top rated rewrites
    st.subheader("🏆 Top Rated Rewrites")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Show Approved Rewrites (⭐4+)", use_container_width=True):
            with st.spinner("Loading approved rewrites..."):
                approved = asyncio.run(tracker.get_approved_rewrites(limit=10))

            if approved:
                for i, record in enumerate(approved, 1):
                    with st.expander(f"#{i} - Rating: {record.get('rating')} ⭐ - ID: {record.get('rewrite_id', 'N/A')[:16]}..."):
                        st.write(f"**Rating:** {record.get('rating')} stars")
                        st.write(f"**Type:** {record.get('feedback_type', 'N/A')}")

                        if record.get('notes'):
                            st.write(f"**Notes:** {record['notes']}")

                        if record.get('metadata'):
                            st.write(f"**Metadata:** {record['metadata']}")
            else:
                st.info("No approved rewrites found")

    with col2:
        if st.button("Show Rejected Rewrites (⭐2-)", use_container_width=True):
            with st.spinner("Loading rejected rewrites..."):
                rejected = asyncio.run(tracker.get_rejected_rewrites(limit=10))

            if rejected:
                for i, record in enumerate(rejected, 1):
                    with st.expander(f"#{i} - Rating: {record.get('rating')} ⭐ - ID: {record.get('rewrite_id', 'N/A')[:16]}..."):
                        st.write(f"**Rating:** {record.get('rating')} stars")
                        st.write(f"**Type:** {record.get('feedback_type', 'N/A')}")

                        if record.get('notes'):
                            st.write(f"**Notes:** {record['notes']}")

                        if record.get('metadata'):
                            st.write(f"**Metadata:** {record['metadata']}")
            else:
                st.info("No rejected rewrites found")
