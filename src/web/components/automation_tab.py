#!/usr/bin/env python3
"""
Automation Tab for Streamlit UI
Control autonomous intelligence automation
"""

import streamlit as st
from datetime import datetime
import asyncio


def render_automation_tab():
    """Render the automation control tab"""
    
    st.header("🤖 Autonomous Intelligence")
    
    # Import here to avoid circular imports
    from src.services.intelligence_automation import IntelligenceAutomation
    from src.agents.enhanced_librarian_agent import EnhancedLibrarianAgent
    from src.services.new_database_manager import get_database_manager
    
    # Initialize session state
    if 'automation' not in st.session_state:
        st.session_state.automation = None
    if 'automation_running' not in st.session_state:
        st.session_state.automation_running = False
    
    # Control Panel
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("▶️ Start Scheduler", use_container_width=True):
            if not st.session_state.automation_running:
                st.session_state.automation = IntelligenceAutomation()
                st.session_state.automation.start(mode="rotation")
                st.session_state.automation_running = True
                st.success("✅ Scheduler started!")
                st.rerun()
            else:
                st.warning("⚠️ Already running!")
    
    with col2:
        if st.button("⏸️ Stop Scheduler", use_container_width=True):
            if st.session_state.automation_running and st.session_state.automation:
                st.session_state.automation.stop()
                st.session_state.automation_running = False
                st.success("🛑 Scheduler stopped!")
                st.rerun()
            else:
                st.warning("⚠️ Not running!")
    
    with col3:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
    
    # Status Display
    st.markdown("---")
    st.subheader("📊 Scheduler Status")
    
    if st.session_state.automation and st.session_state.automation_running:
        status = st.session_state.automation.get_status()
        metrics = status["metrics"]
        jobs = status["scheduled_jobs"]
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Runs", metrics["total_runs"])
        with col2:
            st.metric("Successful", metrics["successful_runs"])
        with col3:
            st.metric("Discoveries", metrics["total_discoveries"])
        with col4:
            st.metric("Avg Quality", f"{metrics['avg_quality']:.2f}")
        
        # Last run
        if metrics["last_run"]:
            st.info(f"🕐 Last run: {metrics['last_run']}")
        
        # Scheduled jobs
        if jobs:
            st.subheader("📅 Scheduled Jobs")
            
            for job in jobs:
                with st.expander(f"⏰ {job['name']}"):
                    st.write(f"**ID:** {job['id']}")
                    st.write(f"**Next Run:** {job['next_run']}")
        
    else:
        st.info("⚪ Scheduler not running. Click 'Start Scheduler' to begin autonomous discovery.")
    
    # Manual Discovery
    st.markdown("---")
    st.subheader("🔍 Manual Discovery")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        profile = st.selectbox(
            "Select Profile",
            ["work", "startup", "learning", "trends"],
            format_func=lambda x: {
                "work": "💼 Work & Professional",
                "startup": "🚀 Startup & Business",
                "learning": "📚 Learning & Education",
                "trends": "📰 Tech Trends & News"
            }[x]
        )
    
    with col2:
        if st.button("Run Discovery Now", use_container_width=True):
            with st.spinner(f"Running discovery for {profile} profile..."):
                automation = IntelligenceAutomation()
                result = asyncio.run(automation.scheduled_discovery(profile))
                
                if result["status"] == "success":
                    st.success(
                        f"✅ Discovery Complete!\n\n"
                        f"Discovered: {result['discovered']}\n"
                        f"High-quality: {result['high_quality']}\n"
                        f"Saved: {result['saved']}"
                    )
                else:
                    st.error(f"❌ Error: {result['error']}")
    
    # Librarian Features
    st.markdown("---")
    st.subheader("📚 Librarian Features")
    
    tab1, tab2, tab3 = st.tabs(["Collections", "Reading Lists", "Digests"])
    
    with tab1:
        render_collections_view()
    
    with tab2:
        render_reading_lists()
    
    with tab3:
        render_digest_generator()


def render_collections_view():
    """Render thematic collections view"""
    
    from src.agents.enhanced_librarian_agent import EnhancedLibrarianAgent
    from src.services.new_database_manager import get_database_manager
    
    st.write("View your curated thematic collections")
    
    if st.button("📚 Curate Collections"):
        with st.spinner("Curating your content..."):
            db = get_database_manager()
            librarian = EnhancedLibrarianAgent(db)
            
            # Get posts
            posts = db.get_posts(limit=100)
            post_items = [
                {
                    "post": post,
                    "quality_score": post.quality_score if hasattr(post, 'quality_score') else 0.5,
                    "topics": []
                }
                for post in posts
            ]
            
            # Curate
            curated = asyncio.run(librarian.curate_content(post_items))
            
            # Display collections
            if curated["collections"]:
                for name, items in curated["collections"].items():
                    emoji_map = {
                        "ai_breakthroughs": "🧠",
                        "startup_stories": "🚀",
                        "dev_tools": "🛠️",
                        "learning_resources": "📚",
                        "industry_news": "📈"
                    }
                    
                    emoji = emoji_map.get(name, "📦")
                    display_name = name.replace("_", " ").title()
                    
                    with st.expander(f"{emoji} {display_name} ({len(items)} items)"):
                        for item in items[:5]:
                            post = item.get("post")
                            if post and hasattr(post, 'content'):
                                st.write(f"• {post.content[:100]}...")
            else:
                st.info("No collections yet. Run discovery first!")
            
            # Stats
            st.markdown("---")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Must-Read", len(curated["must_read"]))
            with col2:
                st.metric("Interesting", len(curated["interesting"]))
            with col3:
                st.metric("Quick Reads", len(curated["quick_reads"]))
            with col4:
                st.metric("Deep Dives", len(curated["deep_dives"]))


def render_reading_lists():
    """Render reading lists management"""
    
    st.write("Create and manage reading lists")
    
    list_type = st.selectbox(
        "Create Reading List",
        ["AI & Machine Learning", "Startups & Business", "Developer Tools", "Custom"]
    )
    
    if st.button("Create List"):
        from src.agents.enhanced_librarian_agent import EnhancedLibrarianAgent
        from src.services.new_database_manager import get_database_manager
        
        with st.spinner(f"Creating {list_type} reading list..."):
            db = get_database_manager()
            librarian = EnhancedLibrarianAgent(db)
            
            # Get relevant posts
            posts = db.get_posts(limit=100)
            
            # Filter by type
            keywords = {
                "AI & Machine Learning": ['ai', 'machine learning', 'llm', 'neural'],
                "Startups & Business": ['startup', 'founder', 'funding', 'vc'],
                "Developer Tools": ['tool', 'framework', 'library', 'vscode']
            }.get(list_type, [])
            
            filtered = [
                {"post": p, "quality_score": 0.7}
                for p in posts
                if hasattr(p, 'content') and any(kw in p.content.lower() for kw in keywords)
            ]
            
            # Create list
            reading_list = asyncio.run(librarian.create_reading_list(
                list_type,
                filtered[:20],
                f"Curated {list_type.lower()} content"
            ))
            
            st.success(f"✅ Created '{reading_list['name']}' with {reading_list['progress']['total']} items!")


def render_digest_generator():
    """Render digest generator"""
    
    st.write("Generate thematic digests")
    
    theme = st.text_input("Digest Theme", value="This Week in Tech")
    days = st.slider("Include posts from last N days", 1, 30, 7)
    
    if st.button("Generate Digest"):
        from src.agents.enhanced_librarian_agent import EnhancedLibrarianAgent
        from src.services.new_database_manager import get_database_manager
        
        with st.spinner(f"Generating '{theme}' digest..."):
            db = get_database_manager()
            librarian = EnhancedLibrarianAgent(db)
            
            # Get posts
            posts = db.get_posts(limit=100)
            post_items = [
                {
                    "post": post,
                    "quality_score": post.quality_score if hasattr(post, 'quality_score') else 0.5,
                    "topics": []
                }
                for post in posts[:50]
            ]
            
            # Generate digest
            digest = asyncio.run(librarian.create_thematic_digest(theme, post_items))
            
            # Display
            st.text_area("Digest", digest, height=400)
            
            # Download button
            st.download_button(
                "📥 Download Digest",
                digest,
                file_name=f"digest_{theme.replace(' ', '_')}.txt",
                mime="text/plain"
            )
