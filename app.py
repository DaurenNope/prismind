#!/usr/bin/env python3
"""
🧠 PrisMind All-in-One Intelligence Platform
==========================================

Single-file Streamlit app with complete automation:
✅ Dashboard frontend
✅ Collection backend  
✅ AI analysis
✅ Health monitoring

Deploy to Streamlit Cloud for FREE automation!
"""

import streamlit as st
import pandas as pd
import asyncio
import os
import sys
import json
import time
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import warnings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

# Setup paths
sys.path.insert(0, str(Path(__file__).parent))

# Page configuration
st.set_page_config(
    page_title="🧠 PrisMind - Intelligence Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    .stButton button { width: 100%; }
    .metric-container { 
        background: #f0f2f6; 
        padding: 1rem; 
        border-radius: 0.5rem; 
        margin: 0.5rem 0;
    }
    .success-message { color: #28a745; }
    .error-message { color: #dc3545; }
    .info-message { color: #17a2b8; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
def init_session_state():
    if 'automation_enabled' not in st.session_state:
        st.session_state.automation_enabled = False
    if 'last_collection' not in st.session_state:
        st.session_state.last_collection = None
    if 'collection_stats' not in st.session_state:
        st.session_state.collection_stats = {"twitter": 0, "reddit": 0, "threads": 0}

init_session_state()

# Simple database managers for cloud deployment
class SimpleSupabaseManager:
    """Simple Supabase manager for cloud deployment"""
    def __init__(self, client):
        self.client = client
        self.table_name = 'posts'
    
    def get_all_posts(self, include_deleted=False):
        try:
            # Try to get all posts first, then filter in Python if needed
            response = self.client.table(self.table_name).select('*').execute()
            df = pd.DataFrame(response.data)
            
            # If we need to filter deleted posts, check if the column exists
            if not include_deleted and 'deleted' in df.columns:
                df = df[df['deleted'] == False]
            elif not include_deleted and 'deleted' not in df.columns:
                # If no deleted column exists, return all posts (assume none are deleted)
                pass
            
            # Since we're not using id as post_id anymore, we need to handle this differently
            # For now, we'll use the id as post_id for the app's internal use
            if not df.empty and 'id' in df.columns:
                df = df.rename(columns={'id': 'post_id'})
                
            return df
        except Exception as e:
            st.error(f"Error fetching posts: {e}")
            return pd.DataFrame()
    
    def get_posts(self, limit=100):
        try:
            response = self.client.table(self.table_name).select('*').limit(limit).execute()
            df = pd.DataFrame(response.data)
            
            # Filter deleted posts if the column exists
            if 'deleted' in df.columns:
                df = df[df['deleted'] == False]
            
            # Map 'id' column to 'post_id' for consistency with the rest of the app
            if not df.empty and 'id' in df.columns:
                df = df.rename(columns={'id': 'post_id'})
                
            return df.to_dict('records')
        except Exception as e:
            st.error(f"Error fetching posts: {e}")
            return []
    
    def add_post(self, post_data):
        try:
            # Prepare the data for Supabase
            # Generate a unique ID from the post_id or use a hash
            post_id = post_data.get('post_id', '')
            if post_id and str(post_id).isdigit():
                # Use the post_id as the database id if it's a reasonable size
                try:
                    db_id = int(post_id)
                    if db_id <= 2147483647:  # Max integer value
                        data = {'id': db_id}
                    else:
                        # If too large, use a hash of the post_id
                        data = {'id': hash(str(post_id)) % 2147483647}
                except (ValueError, OverflowError):
                    data = {'id': hash(str(post_id)) % 2147483647}
            else:
                # Use hash of URL or content as ID
                unique_string = post_data.get('url', '') or post_data.get('content', '') or str(post_data)
                data = {'id': hash(unique_string) % 2147483647}
            
            # Add the rest of the data
            data.update({
                'platform': post_data.get('platform'),
                'title': post_data.get('title'),
                'content': post_data.get('content'),
                'url': post_data.get('url'),
                'author': post_data.get('author'),
                'value_score': post_data.get('value_score', 0),
                'category': post_data.get('category'),
                'summary': post_data.get('ai_analysis'),  # Map ai_analysis to summary
                'smart_tags': post_data.get('smart_tags', '[]'),
                'ai_summary': post_data.get('ai_analysis')  # Also store in ai_summary field
            })
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            # Insert into Supabase
            response = self.client.table(self.table_name).insert(data).execute()
            return True
        except Exception as e:
            st.error(f"Error adding post to Supabase: {e}")
            return False

class SQLiteDatabaseManager:
    """Local SQLite database manager"""
    def __init__(self):
        self.db_path = "prismind.db"
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT UNIQUE,
                platform TEXT,
                title TEXT,
                content TEXT,
                url TEXT,
                author TEXT,
                score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ai_analysis TEXT,
                category TEXT,
                value_score REAL,
                deleted BOOLEAN DEFAULT FALSE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_all_posts(self, include_deleted=False):
        try:
            conn = sqlite3.connect(self.db_path)
            if include_deleted:
                query = "SELECT * FROM posts ORDER BY created_at DESC"
            else:
                query = "SELECT * FROM posts WHERE deleted = FALSE ORDER BY created_at DESC"
            
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"Error fetching posts: {e}")
            return pd.DataFrame()
    
    def get_posts(self, limit=100):
        try:
            conn = sqlite3.connect(self.db_path)
            query = f"SELECT * FROM posts WHERE deleted = FALSE ORDER BY created_at DESC LIMIT {limit}"
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df.to_dict('records')
        except Exception as e:
            st.error(f"Error fetching posts: {e}")
            return []
    
    def add_post(self, post_data):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO posts 
                (post_id, platform, title, content, url, author, score, ai_analysis, category, value_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data.get('post_id'),
                post_data.get('platform'),
                post_data.get('title'),
                post_data.get('content'),
                post_data.get('url'),
                post_data.get('author'),
                post_data.get('score', 0),
                post_data.get('ai_analysis'),
                post_data.get('category'),
                post_data.get('value_score', 0)
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            st.error(f"Error adding post: {e}")

class InMemoryDatabaseManager:
    """Simple in-memory storage for demo purposes"""
    def __init__(self):
        self.posts = []
    
    def get_all_posts(self, include_deleted=False):
        if include_deleted:
            return pd.DataFrame(self.posts)
        else:
            # Filter out deleted posts
            active_posts = [post for post in self.posts if not post.get('deleted', False)]
            return pd.DataFrame(active_posts)
    
    def get_posts(self, limit=100):
        return self.posts[:limit]
    
    def add_post(self, post_data):
        self.posts.append(post_data)

# Database manager wrapper
@st.cache_resource
def get_database_manager():
    """Get cached database manager"""
    try:
        # Try Supabase first, fallback to SQLite
        if os.getenv('SUPABASE_URL'):
            try:
                from supabase import create_client
                url = os.getenv('SUPABASE_URL')
                key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
                if url and key:
                    # Test the connection first
                    import requests
                    try:
                        # Test with a more specific endpoint
                        test_url = f"{url}/rest/v1/"
                        response = requests.get(test_url, headers={"apikey": key}, timeout=10)
                        if response.status_code in [200, 401]:  # 401 means auth works but no table access
                            client = create_client(url, key)
                            return SimpleSupabaseManager(client)
                        else:
                            st.warning("⚠️ Supabase project not accessible, using local database")
                            return SQLiteDatabaseManager()
                    except Exception as e:
                        st.warning(f"⚠️ Supabase connection failed: {e}, using local database")
                        return SQLiteDatabaseManager()
            except ImportError:
                st.error("❌ Supabase library not available. Install with: pip install supabase")
                return SQLiteDatabaseManager()
        else:
            # Use local SQLite database
            return SQLiteDatabaseManager()
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        return SQLiteDatabaseManager()

# Collection functions
async def run_twitter_collection():
    """Run Twitter bookmark collection"""
    try:
        from collect_multi_platform import collect_twitter_bookmarks
        db_manager = get_database_manager()
        if db_manager is None:
            return 0
        
        # Get existing posts to avoid duplicates
        if hasattr(db_manager, 'get_all_posts'):
            existing_posts = db_manager.get_all_posts(include_deleted=False)
            if not existing_posts.empty and 'post_id' in existing_posts.columns:
                existing_ids = set(existing_posts['post_id'].tolist())
            else:
                existing_ids = set()
        else:
            existing_ids = set()
        
        count = await collect_twitter_bookmarks(db_manager, existing_ids)
        return count
    except Exception as e:
        st.error(f"Twitter collection error: {e}")
        return 0

def run_reddit_collection():
    """Run Reddit saved posts collection"""
    try:
        from collect_multi_platform import collect_reddit_bookmarks
        db_manager = get_database_manager()
        if db_manager is None:
            return 0
        
        # Get existing posts to avoid duplicates  
        if hasattr(db_manager, 'get_all_posts'):
            existing_posts = db_manager.get_all_posts(include_deleted=False)
            if not existing_posts.empty and 'post_id' in existing_posts.columns:
                existing_ids = set(existing_posts['post_id'].tolist())
            else:
                existing_ids = set()
        else:
            existing_ids = set()
        
        count = collect_reddit_bookmarks(db_manager, existing_ids)
        return count
    except Exception as e:
        st.error(f"Reddit collection error: {e}")
        return 0

async def run_threads_collection():
    """Run Threads saved posts collection"""
    try:
        from collect_multi_platform import collect_threads_bookmarks
        db_manager = get_database_manager()
        if db_manager is None:
            return 0
        
        # Get existing posts to avoid duplicates
        if hasattr(db_manager, 'get_all_posts'):
            existing_posts = db_manager.get_all_posts(include_deleted=False)
            if not existing_posts.empty and 'post_id' in existing_posts.columns:
                existing_ids = set(existing_posts['post_id'].tolist())
            else:
                existing_ids = set()
        else:
            existing_ids = set()
        
        count = await collect_threads_bookmarks(db_manager, existing_ids)
        return count
    except Exception as e:
        st.error(f"Threads collection error: {e}")
        return 0

# Sidebar automation controls
with st.sidebar:
    st.title("🤖 Automation Hub")
    
    # System status
    st.subheader("📊 System Status")
    
    # API Keys status
    api_status = {
        "🔑 Supabase": bool(os.getenv('SUPABASE_URL')) and bool(os.getenv('SUPABASE_SERVICE_ROLE_KEY')),
        "🤖 Mistral AI": bool(os.getenv('MISTRAL_API_KEY')),
        "🧠 Gemini AI": bool(os.getenv('GEMINI_API_KEY')),
        "🤖 Reddit API": bool(os.getenv('REDDIT_CLIENT_ID')),
        "🐦 Twitter": bool(os.getenv('TWITTER_USERNAME')),
        "🧵 Threads": bool(os.getenv('THREADS_USERNAME'))
    }
    
    for service, status in api_status.items():
        if status:
            st.success(f"✅ {service}")
        else:
            st.error(f"❌ {service}")
    
    st.divider()
    
    # Collection controls
    st.subheader("🚀 Manual Collection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🐦 Twitter", help="Collect Twitter bookmarks", type="secondary"):
            with st.spinner("🔄 Collecting Twitter..."):
                count = asyncio.run(run_twitter_collection())
                if count > 0:
                    st.success(f"✅ Collected {count} Twitter posts!")
                    st.session_state.collection_stats["twitter"] += count
                    st.session_state.last_collection = datetime.now().strftime("%H:%M")
                else:
                    st.info("📭 No new Twitter posts found")
    
    with col2:
        if st.button("🤖 Reddit", help="Collect Reddit saved posts", type="secondary"):
            with st.spinner("🔄 Collecting Reddit..."):
                count = run_reddit_collection()
                if count > 0:
                    st.success(f"✅ Collected {count} Reddit posts!")
                    st.session_state.collection_stats["reddit"] += count
                    st.session_state.last_collection = datetime.now().strftime("%H:%M")
                else:
                    st.info("📭 No new Reddit posts found")
    
    if st.button("🧵 Threads", help="Collect Threads saved posts", type="secondary"):
        with st.spinner("🔄 Collecting Threads..."):
            count = asyncio.run(run_threads_collection())
            if count > 0:
                st.success(f"✅ Collected {count} Threads posts!")
                st.session_state.collection_stats["threads"] += count
                st.session_state.last_collection = datetime.now().strftime("%H:%M")
            else:
                st.info("📭 No new Threads posts found")
    
    if st.button("🚀 Collect All", help="Collect from all platforms", type="primary"):
        with st.spinner("🔄 Collecting from all platforms..."):
            twitter_count = asyncio.run(run_twitter_collection())
            reddit_count = run_reddit_collection()
            threads_count = asyncio.run(run_threads_collection())
            
            total = twitter_count + reddit_count + threads_count
            if total > 0:
                st.success(f"✅ Collected {total} total posts!")
                st.session_state.collection_stats["twitter"] += twitter_count
                st.session_state.collection_stats["reddit"] += reddit_count
                st.session_state.collection_stats["threads"] += threads_count
                st.session_state.last_collection = datetime.now().strftime("%H:%M")
            else:
                st.info("📭 No new posts found on any platform")
    
    st.divider()
    
    # Collection statistics
    st.subheader("📈 Session Stats")
    if st.session_state.last_collection:
        st.metric("Last Collection", st.session_state.last_collection)
    
    stats = st.session_state.collection_stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Twitter", stats["twitter"])
    with col2:
        st.metric("Reddit", stats["reddit"])
    with col3:
        st.metric("Threads", stats["threads"])

# Main content area
st.title("🧠 PrisMind - Intelligent Bookmark Platform")
st.markdown("*Transform your social media bookmarks into structured intelligence*")

# Create tabs for different views
tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "🎯 Browse Posts", "⚙️ Settings"])

with tab1:
    st.header("📊 Intelligence Dashboard")
    
    # Database stats
    db_manager = get_database_manager()
    if db_manager:
        try:
            # Get posts data
            if hasattr(db_manager, 'get_all_posts'):
                posts_df = db_manager.get_all_posts()
            elif hasattr(db_manager, 'get_posts'):
                posts_data = db_manager.get_posts(limit=1000)
                posts_df = pd.DataFrame(posts_data)
            else:
                posts_df = pd.DataFrame()
            
            if not posts_df.empty:
                # Overview metrics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        label="📚 Total Posts",
                        value=len(posts_df)
                    )
                
                with col2:
                    analyzed = len(posts_df.dropna(subset=['category'])) if 'category' in posts_df.columns else 0
                    st.metric(
                        label="🤖 AI Analyzed", 
                        value=analyzed,
                        delta=f"{analyzed/len(posts_df)*100:.1f}%" if len(posts_df) > 0 else "0%"
                    )
                
                with col3:
                    platforms = posts_df['platform'].nunique() if 'platform' in posts_df.columns else 0
                    st.metric(
                        label="🌐 Platforms",
                        value=platforms
                    )
                
                with col4:
                    avg_score = posts_df['value_score'].mean() if 'value_score' in posts_df.columns else 0
                    st.metric(
                        label="⭐ Avg Score",
                        value=f"{avg_score:.1f}/10" if avg_score > 0 else "N/A"
                    )
                
                # Platform breakdown
                if 'platform' in posts_df.columns:
                    st.subheader("📈 Platform Distribution")
                    platform_counts = posts_df['platform'].value_counts()
                    
                    col1, col2 = st.columns([2, 1])
                    with col1:
                        st.bar_chart(platform_counts)
                    with col2:
                        for platform, count in platform_counts.items():
                            st.metric(f"{platform.title()}", count)
                
                # Recent activity
                if 'created_timestamp' in posts_df.columns:
                    st.subheader("📅 Recent Activity")
                    posts_df['created_timestamp'] = pd.to_datetime(posts_df['created_timestamp'], errors='coerce')
                    recent_posts = posts_df.nlargest(10, 'created_timestamp')
                    
                    for _, post in recent_posts.head(5).iterrows():
                        platform_emoji = {"twitter": "🐦", "reddit": "🤖", "threads": "🧵"}.get(post.get('platform', ''), "📝")
                        st.write(f"{platform_emoji} **{post.get('author', 'Unknown')}**: {post.get('content', 'No content')[:100]}...")
                
            else:
                st.info("📭 No posts in database yet. Use the collection buttons in the sidebar to get started!")
                st.markdown("""
                **Getting Started:**
                1. Configure your API keys in the Settings tab
                2. Use the sidebar buttons to collect bookmarks
                3. Watch your intelligence dashboard grow!
                """)
        
        except Exception as e:
            st.error(f"❌ Could not load dashboard data: {e}")
    else:
        st.error("❌ Database not available. Please check your configuration.")

with tab2:
    st.header("🎯 Browse Your Bookmarks")
    
    db_manager = get_database_manager()
    if db_manager:
        try:
            # Get posts data
            if hasattr(db_manager, 'get_all_posts'):
                posts_df = db_manager.get_all_posts()
            elif hasattr(db_manager, 'get_posts'):
                posts_data = db_manager.get_posts(limit=100)
                posts_df = pd.DataFrame(posts_data)
            else:
                posts_df = pd.DataFrame()
            
            if not posts_df.empty:
                # Filters
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    platform_filter = st.selectbox(
                        "Platform", 
                        ['All'] + list(posts_df['platform'].unique()) if 'platform' in posts_df.columns else ['All']
                    )
                
                with col2:
                    category_filter = st.selectbox(
                        "Category",
                        ['All'] + list(posts_df['category'].dropna().unique()) if 'category' in posts_df.columns else ['All']
                    )
                
                with col3:
                    sort_by = st.selectbox(
                        "Sort by",
                        ["Recent", "Value Score", "Author"]
                    )
                
                # Apply filters
                filtered_df = posts_df.copy()
                
                if platform_filter != 'All' and 'platform' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['platform'] == platform_filter]
                
                if category_filter != 'All' and 'category' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['category'] == category_filter]
                
                # Sort
                if sort_by == "Recent" and 'created_timestamp' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values('created_timestamp', ascending=False)
                elif sort_by == "Value Score" and 'value_score' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values('value_score', ascending=False, na_last=True)
                elif sort_by == "Author" and 'author' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values('author')
                
                # Display posts
                st.write(f"📊 Showing {len(filtered_df)} posts")
                
                for idx, post in filtered_df.head(20).iterrows():
                    platform_emoji = {"twitter": "🐦", "reddit": "🤖", "threads": "🧵"}.get(post.get('platform', ''), "📝")
                    score = post.get('value_score', 'N/A')
                    score_display = f"⭐{score}/10" if score != 'N/A' else "⭐N/A"
                    
                    with st.container():
                        st.markdown(f"""
                        **{platform_emoji} {post.get('author', 'Unknown')}** {score_display}
                        
                        {post.get('content', 'No content available')[:300]}...
                        
                        *Category: {post.get('category', 'Uncategorized')} | Platform: {post.get('platform', 'Unknown')}*
                        """)
                        
                        if post.get('url'):
                            st.markdown(f"🔗 [View Original]({post.get('url')})")
                        
                        st.divider()
                
            else:
                st.info("📭 No posts found. Start collecting from the sidebar!")
                
        except Exception as e:
            st.error(f"❌ Could not load posts: {e}")

with tab3:
    st.header("⚙️ Configuration")
    
    st.subheader("🔑 API Configuration")
    st.markdown("""
    Configure your API keys in Streamlit Cloud:
    1. Go to your app settings
    2. Click "Secrets"
    3. Add your API keys in TOML format:
    """)
    
    st.code("""
[secrets]
SUPABASE_URL = "your_supabase_url"
SUPABASE_SERVICE_ROLE_KEY = "your_service_key"
MISTRAL_API_KEY = "your_mistral_key"
GEMINI_API_KEY = "your_gemini_key"
REDDIT_CLIENT_ID = "your_reddit_client_id"
REDDIT_CLIENT_SECRET = "your_reddit_secret"
REDDIT_USERNAME = "your_reddit_username"
REDDIT_PASSWORD = "your_reddit_password"
TWITTER_USERNAME = "your_twitter_username"
THREADS_USERNAME = "your_threads_username"
    """)
    
    st.subheader("🗄️ Database Connection")
    if st.button("Test Database Connection"):
        db_manager = get_database_manager()
        if db_manager:
            try:
                if hasattr(db_manager, 'get_all_posts'):
                    posts_df = db_manager.get_all_posts()
                    st.success(f"✅ Database connected! Found {len(posts_df)} posts.")
                elif hasattr(db_manager, 'get_posts'):
                    posts = db_manager.get_posts(limit=1)
                    st.success(f"✅ Database connected!")
                else:
                    st.success("✅ Database manager loaded successfully!")
            except Exception as e:
                st.error(f"❌ Database test failed: {e}")
        else:
            st.error("❌ Could not initialize database manager")
    
    st.subheader("ℹ️ About")
    st.markdown("""
    **PrisMind All-in-One** - Your complete social media intelligence platform
    
    - 🤖 **Automated collection** from Twitter, Reddit, Threads
    - 🧠 **AI-powered analysis** and categorization  
    - 📊 **Intelligence dashboard** with insights
    - 🔄 **Real-time manual triggers**
    - 🆓 **100% FREE** on Streamlit Cloud
    
    Built with ❤️ by the PrisMind team
    """)

# Footer
st.markdown("---")
st.markdown("🧠 **PrisMind** - Transform your bookmarks into intelligence | 🚀 Powered by Streamlit Cloud")
