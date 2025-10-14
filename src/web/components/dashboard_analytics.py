"""
Dashboard Analytics Components for PrisMind
Handles analytics and insights display
"""

import pandas as pd
import streamlit as st
from typing import Dict, Any, Optional


def render_analytics_tab():
    """Render the analytics tab with insights and statistics"""
    from src.services.new_database_manager import get_database_manager
    
    db_manager = get_database_manager()
    
    st.subheader("📊 Content Analytics")
    
    # Get analytics data
    analytics_data = db_manager.get_analytics()
    
    if not analytics_data:
        st.info("No analytics data available.")
        return
    
    # Overview metrics
    render_overview_metrics(analytics_data)
    
    # Platform distribution
    render_platform_distribution(analytics_data)
    
    # Top authors
    render_top_authors(analytics_data)
    
    # Content trends
    render_content_trends(analytics_data)
    
    # Value score distribution
    render_value_distribution(analytics_data)


def render_overview_metrics(analytics_data: Dict[str, Any]):
    """Render overview metrics"""
    st.subheader("📈 Overview")
    
    # Create metric columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_posts = analytics_data.get('total_posts', 0)
        st.metric("Total Posts", total_posts)
    
    with col2:
        avg_score = analytics_data.get('average_value_score', 0.0)
        st.metric("Avg Value Score", f"{avg_score:.2f}")
    
    with col3:
        total_authors = analytics_data.get('unique_authors', 0)
        st.metric("Unique Authors", total_authors)
    
    with col4:
        total_platforms = analytics_data.get('unique_platforms', 0)
        st.metric("Platforms", total_platforms)


def render_platform_distribution(analytics_data: Dict[str, Any]):
    """Render platform distribution chart"""
    st.subheader("🌐 Platform Distribution")
    
    platform_data = analytics_data.get('platform_distribution', {})
    
    if platform_data:
        # Create DataFrame for chart
        df = pd.DataFrame([
            {'Platform': platform, 'Count': data['count'], 'Percentage': data['percentage']}
            for platform, data in platform_data.items()
        ])
        
        # Display chart
        st.bar_chart(df.set_index('Platform')['Count'])
        
        # Display table
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No platform data available.")


def render_top_authors(analytics_data: Dict[str, Any]):
    """Render top authors by post count and value score"""
    st.subheader("👥 Top Authors")
    
    top_authors = analytics_data.get('top_authors', [])
    
    if top_authors:
        # Create DataFrame
        df = pd.DataFrame(top_authors)
        
        # Display table
        st.dataframe(
            df[['author', 'post_count', 'average_score', 'total_score']],
            use_container_width=True,
            column_config={
                'author': 'Author',
                'post_count': 'Posts',
                'average_score': 'Avg Score',
                'total_score': 'Total Score'
            }
        )
    else:
        st.info("No author data available.")


def render_content_trends(analytics_data: Dict[str, Any]):
    """Render content trends over time"""
    st.subheader("📈 Content Trends")
    
    trends_data = analytics_data.get('trends', {})
    
    if trends_data:
        # Daily posts trend
        daily_posts = trends_data.get('daily_posts', [])
        if daily_posts:
            df_daily = pd.DataFrame(daily_posts)
            st.line_chart(df_daily.set_index('date')['count'])
        
        # Value score trend
        score_trends = trends_data.get('score_trends', [])
        if score_trends:
            df_scores = pd.DataFrame(score_trends)
            st.line_chart(df_scores.set_index('date')['average_score'])
    else:
        st.info("No trend data available.")


def render_value_distribution(analytics_data: Dict[str, Any]):
    """Render value score distribution"""
    st.subheader("⭐ Value Score Distribution")
    
    score_distribution = analytics_data.get('score_distribution', {})
    
    if score_distribution:
        # Create distribution chart
        df = pd.DataFrame([
            {'Score Range': range_name, 'Count': count}
            for range_name, count in score_distribution.items()
        ])
        
        st.bar_chart(df.set_index('Score Range')['Count'])
        
        # Show statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("High Value Posts (>0.7)", score_distribution.get('High (0.7-1.0)', 0))
            st.metric("Medium Value Posts (0.4-0.7)", score_distribution.get('Medium (0.4-0.7)', 0))
        
        with col2:
            st.metric("Low Value Posts (<0.4)", score_distribution.get('Low (0.0-0.4)', 0))
            st.metric("Average Score", f"{analytics_data.get('average_value_score', 0.0):.2f}")
    else:
        st.info("No score distribution data available.")


def render_content_insights(analytics_data: Dict[str, Any]):
    """Render content insights and recommendations"""
    st.subheader("💡 Content Insights")
    
    insights = analytics_data.get('insights', [])
    
    if insights:
        for insight in insights:
            st.info(insight)
    else:
        st.info("No insights available.")


def render_export_options(analytics_data: Dict[str, Any]):
    """Render export options for analytics data"""
    st.subheader("📤 Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Export Analytics CSV"):
            # Convert analytics data to CSV
            df = pd.DataFrame([analytics_data])
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="prismind_analytics.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("Export Summary Report"):
            # Generate summary report
            report = generate_summary_report(analytics_data)
            st.download_button(
                label="Download Report",
                data=report,
                file_name="prismind_summary.txt",
                mime="text/plain"
            )


def generate_summary_report(analytics_data: Dict[str, Any]) -> str:
    """Generate a text summary report"""
    report = "PrisMind Analytics Summary Report\n"
    report += "=" * 40 + "\n\n"
    
    # Overview
    report += f"Total Posts: {analytics_data.get('total_posts', 0)}\n"
    report += f"Average Value Score: {analytics_data.get('average_value_score', 0.0):.2f}\n"
    report += f"Unique Authors: {analytics_data.get('unique_authors', 0)}\n"
    report += f"Platforms: {analytics_data.get('unique_platforms', 0)}\n\n"
    
    # Platform distribution
    platform_data = analytics_data.get('platform_distribution', {})
    if platform_data:
        report += "Platform Distribution:\n"
        for platform, data in platform_data.items():
            report += f"  {platform}: {data['count']} posts ({data['percentage']:.1f}%)\n"
        report += "\n"
    
    # Top authors
    top_authors = analytics_data.get('top_authors', [])
    if top_authors:
        report += "Top Authors:\n"
        for author in top_authors[:5]:
            report += f"  {author['author']}: {author['post_count']} posts (avg score: {author['average_score']:.2f})\n"
        report += "\n"
    
    # Insights
    insights = analytics_data.get('insights', [])
    if insights:
        report += "Key Insights:\n"
        for insight in insights:
            report += f"  • {insight}\n"
    
    return report





