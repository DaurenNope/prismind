#!/usr/bin/env python3
"""
🧠 PrisMind Demo - Streamlit Cloud Compatible
============================================

Simplified version that works perfectly in Streamlit Cloud
with mock data and AI analysis demonstration.
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import time

# Page configuration
st.set_page_config(
    page_title="🧠 PrisMind - Intelligence Platform",
    page_icon="🧠",
    layout="wide"
)

# Initialize session state
if 'posts_data' not in st.session_state:
    st.session_state.posts_data = []
if 'collection_count' not in st.session_state:
    st.session_state.collection_count = 0

def create_mock_posts():
    """Create mock posts for demonstration"""
    mock_posts = [
        {
            "post_id": "demo_1",
            "platform": "twitter",
            "author": "TechGuru",
            "content": "Just discovered this amazing AI framework that can process natural language queries in real-time. The potential for automation is incredible! 🚀 #AI #MachineLearning",
            "category": "Technology",
            "value_score": 8.5,
            "sentiment": "Positive",
            "created_at": datetime.now() - timedelta(hours=2),
            "url": "https://twitter.com/example/status/123"
        },
        {
            "post_id": "demo_2", 
            "platform": "reddit",
            "author": "DataScientist",
            "content": "I've been working with large language models for the past year, and here's what I've learned about prompt engineering. The key is being specific and providing context...",
            "category": "Learning",
            "value_score": 9.2,
            "sentiment": "Informative",
            "created_at": datetime.now() - timedelta(hours=5),
            "url": "https://reddit.com/r/MachineLearning/comments/example"
        },
        {
            "post_id": "demo_3",
            "platform": "threads",
            "author": "BusinessInsights",
            "content": "Market research shows that companies using AI for customer service see 40% improvement in response times and 60% higher customer satisfaction rates.",
            "category": "Business",
            "value_score": 7.8,
            "sentiment": "Analytical", 
            "created_at": datetime.now() - timedelta(hours=8),
            "url": "https://threads.net/@business/post/example"
        }
    ]
    return mock_posts

# Custom CSS
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    .stButton button { width: 100%; }
    .demo-post {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #007bff;
    }
    .platform-twitter { border-left-color: #1da1f2; }
    .platform-reddit { border-left-color: #ff4500; }
    .platform-threads { border-left-color: #000; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("🤖 PrisMind Demo")
    
    # Status indicators
    st.subheader("📊 System Status")
    
    # Check environment variables
    supabase_configured = bool(os.getenv('SUPABASE_URL'))
    api_keys_configured = bool(os.getenv('MISTRAL_API_KEY')) or bool(os.getenv('GEMINI_API_KEY'))
    
    st.success("✅ Demo Mode Active") 
    if supabase_configured:
        st.success("✅ Database Connected")
    else:
        st.info("ℹ️ Using Demo Data")
        
    if api_keys_configured:
        st.success("✅ AI Analysis Ready")
    else:
        st.info("ℹ️ Mock AI Analysis")
    
    st.divider()
    
    # Demo controls
    st.subheader("🚀 Demo Collection")
    
    if st.button("📥 Simulate Collection", type="primary"):
        with st.spinner("Collecting bookmarks..."):
            time.sleep(2)  # Simulate processing time
            
            # Add mock posts to session state
            if not st.session_state.posts_data:
                st.session_state.posts_data = create_mock_posts()
            else:
                # Add a new random post
                new_post = {
                    "post_id": f"demo_{len(st.session_state.posts_data) + 1}",
                    "platform": ["twitter", "reddit", "threads"][st.session_state.collection_count % 3],
                    "author": f"User{st.session_state.collection_count + 1}",
                    "content": f"This is demo post #{st.session_state.collection_count + 1} with AI analysis and categorization.",
                    "category": ["Technology", "Learning", "Business", "Research"][st.session_state.collection_count % 4],
                    "value_score": 7 + (st.session_state.collection_count % 3),
                    "sentiment": "Positive",
                    "created_at": datetime.now(),
                    "url": f"https://example.com/post/{st.session_state.collection_count}"
                }
                st.session_state.posts_data.append(new_post)
            
            st.session_state.collection_count += 1
            st.success(f"✅ Collected {len(st.session_state.posts_data)} posts!")
            st.rerun()
    
    if st.button("🧹 Clear Demo Data"):
        st.session_state.posts_data = []
        st.session_state.collection_count = 0
        st.success("✅ Demo data cleared!")
        st.rerun()
    
    # Stats
    if st.session_state.posts_data:
        st.subheader("📈 Demo Stats")
        st.metric("Total Posts", len(st.session_state.posts_data))
        st.metric("Collections", st.session_state.collection_count)

# Main content
st.title("🧠 PrisMind - Intelligence Platform Demo")
st.markdown("*Experience the power of automated social media intelligence*")

# Show configuration status
if not os.getenv('SUPABASE_URL'):
    st.info("📝 **Demo Mode**: This is a demonstration with sample data. Configure your API keys to connect real data sources.")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🎯 Browse Posts", "⚙️ Configuration"])

with tab1:
    st.header("📊 Intelligence Dashboard")
    
    if st.session_state.posts_data:
        posts_df = pd.DataFrame(st.session_state.posts_data)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📚 Total Posts", len(posts_df))
        
        with col2:
            st.metric("🤖 AI Analyzed", len(posts_df), "100%")
        
        with col3:
            platforms = posts_df['platform'].nunique()
            st.metric("🌐 Platforms", platforms)
        
        with col4:
            avg_score = posts_df['value_score'].mean()
            st.metric("⭐ Avg Score", f"{avg_score:.1f}/10")
        
        # Platform distribution
        st.subheader("📈 Platform Distribution")
        platform_counts = posts_df['platform'].value_counts()
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.bar_chart(platform_counts)
        with col2:
            for platform, count in platform_counts.items():
                emoji = {"twitter": "🐦", "reddit": "🤖", "threads": "🧵"}.get(platform, "📝")
                st.metric(f"{emoji} {platform.title()}", count)
        
        # Category breakdown
        st.subheader("🏷️ Content Categories")
        if 'category' in posts_df.columns:
            category_counts = posts_df['category'].value_counts()
            st.bar_chart(category_counts)
    
    else:
        st.info("📭 No data yet. Click 'Simulate Collection' in the sidebar to see the demo in action!")
        
        # Show what the platform can do
        st.subheader("🚀 PrisMind Capabilities")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            **🤖 AI Analysis**
            - Content categorization
            - Sentiment analysis
            - Value scoring (1-10)
            - Concept extraction
            """)
        
        with col2:
            st.markdown("""
            **📊 Multi-Platform**
            - Twitter bookmarks
            - Reddit saved posts  
            - Threads collections
            - Unified dashboard
            """)
        
        with col3:
            st.markdown("""
            **🔄 Automation**
            - Scheduled collection
            - Real-time analysis
            - Smart categorization
            - Cloud synchronization
            """)

with tab2:
    st.header("🎯 Browse Your Intelligence")
    
    if st.session_state.posts_data:
        posts_df = pd.DataFrame(st.session_state.posts_data)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            platform_filter = st.selectbox("Platform", ['All'] + list(posts_df['platform'].unique()))
        
        with col2:
            category_filter = st.selectbox("Category", ['All'] + list(posts_df['category'].unique()))
        
        with col3:
            sort_by = st.selectbox("Sort by", ["Recent", "Value Score", "Platform"])
        
        # Apply filters
        filtered_df = posts_df.copy()
        
        if platform_filter != 'All':
            filtered_df = filtered_df[filtered_df['platform'] == platform_filter]
        
        if category_filter != 'All':
            filtered_df = filtered_df[filtered_df['category'] == category_filter]
        
        # Sort
        if sort_by == "Recent":
            filtered_df = filtered_df.sort_values('created_at', ascending=False)
        elif sort_by == "Value Score":
            filtered_df = filtered_df.sort_values('value_score', ascending=False)
        elif sort_by == "Platform":
            filtered_df = filtered_df.sort_values('platform')
        
        # Display posts
        st.write(f"📊 Showing {len(filtered_df)} posts")
        
        for _, post in filtered_df.iterrows():
            platform_emoji = {"twitter": "🐦", "reddit": "🤖", "threads": "🧵"}.get(post['platform'], "📝")
            platform_class = f"platform-{post['platform']}"
            
            st.markdown(f"""
            <div class="demo-post {platform_class}">
                <strong>{platform_emoji} {post['author']}</strong> 
                <span style="float: right;">⭐ {post['value_score']}/10</span>
                <br><br>
                {post['content'][:200]}{'...' if len(post['content']) > 200 else ''}
                <br><br>
                <small>
                    📂 {post['category']} | 
                    😊 {post['sentiment']} | 
                    🕒 {post['created_at'].strftime('%H:%M')}
                </small>
            </div>
            """, unsafe_allow_html=True)
    
    else:
        st.info("📭 No posts to display. Simulate some data collection first!")

with tab3:
    st.header("⚙️ Configuration")
    
    st.subheader("🔗 Connect Your Data Sources")
    
    # Show current configuration status
    config_status = {
        "Supabase Database": bool(os.getenv('SUPABASE_URL')),
        "Mistral AI": bool(os.getenv('MISTRAL_API_KEY')),
        "Gemini AI": bool(os.getenv('GEMINI_API_KEY')),
        "Reddit API": bool(os.getenv('REDDIT_CLIENT_ID')),
        "Twitter Account": bool(os.getenv('TWITTER_USERNAME')),
        "Threads Account": bool(os.getenv('THREADS_USERNAME'))
    }
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Current Configuration:**")
        for service, configured in config_status.items():
            status = "✅" if configured else "❌"
            st.write(f"{status} {service}")
    
    with col2:
        st.markdown("**To enable real data:**")
        st.write("1. Add your API keys in Streamlit secrets")
        st.write("2. Configure social media accounts") 
        st.write("3. Set up Supabase database")
        st.write("4. Enable automated collection")
    
    st.subheader("📋 Secrets Configuration")
    
    st.markdown("Add this to your Streamlit Cloud app secrets:")
    
    secrets_template = """[secrets]
SUPABASE_URL = "your_supabase_url"
SUPABASE_SERVICE_ROLE_KEY = "your_service_key"
MISTRAL_API_KEY = "your_mistral_key" 
GEMINI_API_KEY = "your_gemini_key"
REDDIT_CLIENT_ID = "your_reddit_id"
REDDIT_CLIENT_SECRET = "your_reddit_secret"
REDDIT_USERNAME = "your_reddit_username"
TWITTER_USERNAME = "your_twitter_username"
THREADS_USERNAME = "your_threads_username"
"""
    
    st.code(secrets_template, language="toml")
    
    st.subheader("ℹ️ About This Demo")
    st.markdown("""
    **PrisMind Intelligence Platform** transforms your social media bookmarks into structured knowledge.
    
    **🎯 This demo shows:**
    - AI-powered content analysis
    - Multi-platform aggregation  
    - Intelligent categorization
    - Real-time dashboard
    
    **🚀 Full version includes:**
    - Automated collection (every 6 hours)
    - Real social media integration
    - Advanced AI analysis with multiple providers
    - Cloud database synchronization
    - Export to Notion, Obsidian, etc.
    
    **💰 Cost: FREE forever** on Streamlit Cloud!
    """)

# Footer
st.markdown("---")
st.markdown("🧠 **PrisMind Demo** - Experience intelligent bookmark management | [Get Full Version](https://github.com/DaurenNope/prismind)")
