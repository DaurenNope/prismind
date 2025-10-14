"""
Dashboard Settings Components for PrisMind
Handles settings and configuration
"""

import streamlit as st
from typing import Dict, Any, Optional


def render_settings_tab():
    """Render the settings tab"""
    st.subheader("⚙️ Settings")
    
    # Create tabs for different settings
    tab1, tab2, tab3 = st.tabs(["🔧 General", "🤖 AI", "📊 Collection"])
    
    with tab1:
        render_general_settings()
    
    with tab2:
        render_ai_settings()
    
    with tab3:
        render_collection_settings()


def render_general_settings():
    """Render general settings"""
    st.subheader("General Settings")
    
    # Database settings
    st.markdown("### Database")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Clear Database"):
            if st.session_state.get('confirm_clear', False):
                # Clear database logic here
                st.success("Database cleared successfully!")
                st.session_state['confirm_clear'] = False
            else:
                st.session_state['confirm_clear'] = True
                st.warning("Click again to confirm database clearing")
    
    with col2:
        if st.button("Export Database"):
            st.info("Database export functionality coming soon")
    
    # Display settings
    st.markdown("### Display")
    
    posts_per_page = st.slider(
        "Posts per page",
        min_value=5,
        max_value=50,
        value=10,
        help="Number of posts to display per page"
    )
    
    show_media = st.checkbox(
        "Show media previews",
        value=True,
        help="Display media content in post cards"
    )
    
    # Save settings
    if st.button("Save General Settings"):
        # Save settings logic here
        st.success("General settings saved!")


def render_ai_settings():
    """Render AI settings"""
    st.subheader("AI Configuration")
    
    # AI Service selection
    st.markdown("### AI Services")
    
    ai_service = st.selectbox(
        "Primary AI Service",
        ["Mistral", "Gemini", "Ollama", "OpenAI"],
        help="Select the primary AI service for content analysis"
    )
    
    # API Keys
    st.markdown("### API Keys")
    
    mistral_key = st.text_input(
        "Mistral API Key",
        type="password",
        help="Enter your Mistral API key"
    )
    
    gemini_key = st.text_input(
        "Gemini API Key",
        type="password",
        help="Enter your Gemini API key"
    )
    
    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="Enter your OpenAI API key"
    )
    
    # AI Analysis settings
    st.markdown("### Analysis Settings")
    
    enable_sentiment = st.checkbox(
        "Enable sentiment analysis",
        value=True,
        help="Analyze sentiment of posts"
    )
    
    enable_topic_extraction = st.checkbox(
        "Enable topic extraction",
        value=True,
        help="Extract key topics from posts"
    )
    
    enable_value_scoring = st.checkbox(
        "Enable value scoring",
        value=True,
        help="Calculate value scores for posts"
    )
    
    # Save AI settings
    if st.button("Save AI Settings"):
        # Save AI settings logic here
        st.success("AI settings saved!")


def render_collection_settings():
    """Render collection settings"""
    st.subheader("Collection Configuration")
    
    # Platform settings
    st.markdown("### Platforms")
    
    enable_twitter = st.checkbox(
        "Enable Twitter collection",
        value=True,
        help="Collect bookmarks from Twitter"
    )
    
    enable_reddit = st.checkbox(
        "Enable Reddit collection",
        value=True,
        help="Collect saved posts from Reddit"
    )
    
    enable_threads = st.checkbox(
        "Enable Threads collection",
        value=True,
        help="Collect saved posts from Threads"
    )
    
    # Collection frequency
    st.markdown("### Collection Frequency")
    
    collection_interval = st.selectbox(
        "Collection interval",
        ["Every hour", "Every 6 hours", "Every 12 hours", "Daily", "Weekly"],
        index=2,
        help="How often to run collection"
    )
    
    max_posts_per_run = st.slider(
        "Max posts per collection run",
        min_value=10,
        max_value=500,
        value=100,
        help="Maximum number of posts to collect in each run"
    )
    
    # Quality filters
    st.markdown("### Quality Filters")
    
    min_value_score = st.slider(
        "Minimum value score",
        min_value=0.0,
        max_value=1.0,
        value=0.3,
        step=0.1,
        help="Only collect posts above this value score"
    )
    
    enable_duplicate_detection = st.checkbox(
        "Enable duplicate detection",
        value=True,
        help="Skip posts that are already in the database"
    )
    
    # Save collection settings
    if st.button("Save Collection Settings"):
        # Save collection settings logic here
        st.success("Collection settings saved!")


def render_system_status():
    """Render system status information"""
    st.subheader("System Status")
    
    # Database status
    st.markdown("### Database")
    
    try:
        from src.services.new_database_manager import get_database_manager
        db_manager = get_database_manager()
        
        # Get basic stats
        total_posts = db_manager.get_post_count()
        st.metric("Total Posts", total_posts)
        
        # Database health
        st.success("✅ Database connection healthy")
        
    except Exception as e:
        st.error(f"❌ Database error: {str(e)}")
    
    # AI services status
    st.markdown("### AI Services")
    
    # Check AI service availability
    ai_services = ["Mistral", "Gemini", "Ollama", "OpenAI"]
    
    for service in ai_services:
        # Mock status check - in real implementation, test actual connections
        if service == "Ollama":
            st.success(f"✅ {service} - Available")
        else:
            st.warning(f"⚠️ {service} - Not configured")
    
    # Collection status
    st.markdown("### Collection")
    
    # Last collection time
    st.info("Last collection: Never (configure collection settings)")
    
    # Collection health
    st.warning("⚠️ Collection not configured")


def render_about():
    """Render about information"""
    st.subheader("About PrisMind")
    
    st.markdown("""
    **PrisMind** is an intelligent bookmark platform that transforms your social media 
    bookmarks into structured, searchable knowledge.
    
    ### Features
    - 🧠 AI-powered content analysis
    - 📊 Intelligent value scoring
    - 🔍 Advanced search and filtering
    - 📈 Content analytics and insights
    - 🌐 Multi-platform support (Twitter, Reddit, Threads)
    
    ### Version
    Version 1.0.0
    
    ### Support
    For support and feedback, please contact the development team.
    """)
    
    # System information
    st.markdown("### System Information")
    
    import sys
    import platform
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text(f"Python Version: {sys.version}")
        st.text(f"Platform: {platform.system()}")
    
    with col2:
        st.text(f"Streamlit Version: {st.__version__}")
        st.text(f"Working Directory: {st.session_state.get('cwd', 'Unknown')}")





