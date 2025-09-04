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

import asyncio
import json
import os
import sqlite3
import sys
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
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
    if 'background_collector' not in st.session_state:
        st.session_state.background_collector = None
    if 'background_running' not in st.session_state:
        st.session_state.background_running = False

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
            # First, check if this post already exists
            post_id = post_data.get('post_id', '')
            url = post_data.get('url', '')
            
            if post_id:
                # Check by post_id first
                try:
                    existing = self.client.table(self.table_name).select('id').eq('id', post_id).execute()
                    if existing.data:
                        print(f"⚠️ Post {post_id} already exists, skipping...")
                        return True  # Return True since it's already there
                except:
                    pass
            
            if url:
                # Also check by URL as backup
                try:
                    existing = self.client.table(self.table_name).select('id').eq('url', url).execute()
                    if existing.data:
                        print(f"⚠️ Post with URL {url} already exists, skipping...")
                        return True
                except:
                    pass
            
            # Generate a unique ID
            import hashlib
            import time
            
            # Create a unique identifier
            unique_string = f"{post_id}_{url}_{post_data.get('content', '')[:100]}"
            # Use SHA256 hash and take first 8 characters as hex, convert to int
            hash_object = hashlib.sha256(unique_string.encode())
            hash_hex = hash_object.hexdigest()[:8]
            db_id = int(hash_hex, 16) % 2147483647  # Ensure it fits in INTEGER range
            
            # Add timestamp to make it more unique
            timestamp = int(time.time() * 1000) % 1000000  # Last 6 digits of timestamp
            db_id = (db_id + timestamp) % 2147483647
            
            data = {'id': db_id}
            
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
    
    # Background collection controls
    st.subheader("🔄 Background Collection")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not st.session_state.background_running:
            if st.button("🚀 Start Background Collection", type="primary"):
                try:
                    from background_collector import start_background_collection
                    st.session_state.background_collector = start_background_collection()
                    st.session_state.background_running = True
                    st.success("✅ Background collection started!")
                    st.info("💡 Collection will run automatically every hour")
                except Exception as e:
                    st.error(f"❌ Failed to start background collection: {e}")
        else:
            st.success("🔄 Background collection is running")
    
    with col2:
        if st.session_state.background_running:
            if st.button("🛑 Stop Background Collection"):
                if st.session_state.background_collector:
                    st.session_state.background_collector.stop()
                st.session_state.background_running = False
                st.session_state.background_collector = None
                st.success("✅ Background collection stopped!")
    
    # Background collection status
    if st.session_state.background_running:
        st.info("""
        🔄 **Background Collection Active**
        
        - **Collection interval**: Every 60 minutes (configurable)
        - **Max posts per run**: 100 (configurable)
        - **Platforms**: Twitter (50 posts), Reddit (25 posts), Threads (disabled)
        - **Duplicate detection**: Automatic
        - **Error handling**: Automatic retry on failure
        
        💡 **Configuration**: Set environment variables:
        - `COLLECTION_INTERVAL_MINUTES`: Collection frequency
        - `MAX_POSTS_PER_RUN`: Max posts per collection cycle
        - `TWITTER_LIMIT`, `REDDIT_LIMIT`: Platform-specific limits
        """)
    
    st.divider()
    
    # Scraping statistics
    st.subheader("📈 Scraping Statistics")
    
    try:
        from scrape_state_manager import state_manager
        stats = state_manager.get_scraping_stats()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Posts Tracked", stats['total_posts'])
            for platform, count in stats['posts_by_platform'].items():
                st.metric(f"{platform.title()} Posts", count)
        
        with col2:
            for platform_stat in stats['platform_stats']:
                if platform_stat['last_scraped_at']:
                    last_scraped = platform_stat['last_scraped_at'][:19]  # Remove microseconds
                    st.metric(
                        f"{platform_stat['platform'].title()} Last Scrape", 
                        last_scraped,
                        delta=f"{platform_stat['total_posts_scraped']} posts"
                    )
        
        # Reset options
        st.subheader("🔄 Reset Options")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Reset Twitter State"):
                state_manager.reset_platform_state('twitter')
                st.success("✅ Twitter scraping state reset!")
                st.rerun()
        
        with col2:
            if st.button("Reset Reddit State"):
                state_manager.reset_platform_state('reddit')
                st.success("✅ Reddit scraping state reset!")
                st.rerun()
        
        with col3:
            if st.button("Reset All States"):
                state_manager.reset_platform_state('twitter')
                state_manager.reset_platform_state('reddit')
                st.success("✅ All scraping states reset!")
                st.rerun()
                
    except Exception as e:
        st.error(f"❌ Could not load scraping stats: {e}")
    
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
    
    # Initialize session state for pagination and filters
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'posts_per_page' not in st.session_state:
        st.session_state.posts_per_page = 10
    if 'search_query' not in st.session_state:
        st.session_state.search_query = ""
    
    db_manager = get_database_manager()
    if db_manager:
        try:
            # Cache posts data to avoid reloading
            @st.cache_data(ttl=300)  # Cache for 5 minutes
            def load_posts_data():
                if hasattr(db_manager, 'get_all_posts'):
                    return db_manager.get_all_posts()
                elif hasattr(db_manager, 'get_posts'):
                    posts_data = db_manager.get_posts(limit=1000)  # Increased limit
                    return pd.DataFrame(posts_data)
                else:
                    return pd.DataFrame()
            
            posts_df = load_posts_data()
            
            # Ensure posts_df is a valid DataFrame
            if posts_df is None:
                posts_df = pd.DataFrame()
            
            if not posts_df.empty and len(posts_df) > 0:
                # Search and filters section
                st.subheader("🔍 Search & Filters")
                
                # Search bar
                search_query = st.text_input(
                    "🔍 Search posts...",
                    value=st.session_state.search_query,
                    placeholder="Search by content, author, or title..."
                )
                st.session_state.search_query = search_query
                
                # Advanced filters
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    platform_filter = st.selectbox(
                        "🌐 Platform", 
                        ['All'] + list(posts_df['platform'].unique()) if 'platform' in posts_df.columns else ['All']
                    )
                
                with col2:
                    category_filter = st.selectbox(
                        "📂 Category",
                        ['All'] + list(posts_df['category'].dropna().unique()) if 'category' in posts_df.columns else ['All']
                    )
                
                with col3:
                    sort_by = st.selectbox(
                        "📊 Sort by",
                        ["Recent", "Value Score", "Author", "Platform"]
                    )
                
                with col4:
                    st.session_state.posts_per_page = st.selectbox(
                        "📄 Posts per page",
                        [5, 10, 20, 50],
                        index=1
                    )
                
                # Apply filters
                filtered_df = posts_df.copy()
                
                # Search filter
                if search_query:
                    try:
                        search_mask = (
                            filtered_df['content'].str.contains(search_query, case=False, na=False) |
                            filtered_df['author'].str.contains(search_query, case=False, na=False) |
                            filtered_df['title'].str.contains(search_query, case=False, na=False)
                        )
                        filtered_df = filtered_df[search_mask]
                    except Exception as e:
                        st.warning(f"⚠️ Search error: {e}")
                        # Fallback to simple search
                        search_mask = filtered_df.apply(
                            lambda row: search_query.lower() in str(row).lower(), axis=1
                        )
                        filtered_df = filtered_df[search_mask]
                
                # Platform filter
                if platform_filter != 'All' and 'platform' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['platform'] == platform_filter]
                
                # Category filter
                if category_filter != 'All' and 'category' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['category'] == category_filter]
                
                # Sort
                if sort_by == "Recent" and 'created_timestamp' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values('created_timestamp', ascending=False)
                elif sort_by == "Value Score" and 'value_score' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values('value_score', ascending=False, na_last=True)
                elif sort_by == "Author" and 'author' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values('author')
                elif sort_by == "Platform" and 'platform' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values('platform')
                
                # Pagination
                total_posts = len(filtered_df)
                total_pages = (total_posts + st.session_state.posts_per_page - 1) // st.session_state.posts_per_page
                
                # Pagination controls
                col1, col2, col3 = st.columns([1, 2, 1])
                
                with col1:
                    if st.button("⬅️ Previous") and st.session_state.current_page > 0:
                        st.session_state.current_page -= 1
                        st.rerun()
                
                with col2:
                    st.write(f"📄 Page {st.session_state.current_page + 1} of {total_pages} ({total_posts} total posts)")
                
                with col3:
                    if st.button("➡️ Next") and st.session_state.current_page < total_pages - 1:
                        st.session_state.current_page += 1
                        st.rerun()
                
                # Reset pagination when filters change
                if st.button("🔄 Reset to Page 1"):
                    st.session_state.current_page = 0
                    st.rerun()
                
                # Calculate current page data
                start_idx = st.session_state.current_page * st.session_state.posts_per_page
                end_idx = min(start_idx + st.session_state.posts_per_page, total_posts)
                
                try:
                    current_posts = filtered_df.iloc[start_idx:end_idx]
                except Exception as e:
                    st.error(f"❌ Pagination error: {e}")
                    current_posts = filtered_df.head(st.session_state.posts_per_page)
                
                # Create a super useful table view
                st.subheader(f"📊 Intelligent Table View ({start_idx + 1}-{end_idx} of {total_posts})")
                
                # Quick overview of current results
                if total_posts > 0:
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        platforms_in_view = filtered_df['platform'].nunique() if 'platform' in filtered_df.columns else 0
                        st.metric("🌐 Platforms", platforms_in_view)
                    
                    with col2:
                        categories_in_view = filtered_df['category'].nunique() if 'category' in filtered_df.columns else 0
                        st.metric("📂 Categories", categories_in_view)
                    
                    with col3:
                        avg_score = filtered_df['value_score'].mean() if 'value_score' in filtered_df.columns else 0
                        st.metric("⭐ Avg Score", f"{avg_score:.1f}/10" if avg_score > 0 else "N/A")
                    
                    with col4:
                        try:
                            if 'category' in filtered_df.columns and len(filtered_df) > 0:
                                category_mode = filtered_df['category'].mode()
                                if len(category_mode) > 0:
                                    top_category = category_mode.iloc[0]
                                    display_category = top_category[:15] + "..." if len(str(top_category)) > 15 else top_category
                                else:
                                    display_category = "N/A"
                            else:
                                display_category = "N/A"
                            st.metric("🏆 Top Category", display_category)
                        except Exception:
                            st.metric("🏆 Top Category", "N/A")
                    
                    st.divider()
                
                # Create a table-friendly DataFrame
                table_data = []
                
                # Show AI analysis status
                if len(current_posts) > 0:
                    ai_analyzed_count = 0
                    for _, post in current_posts.iterrows():
                        if post.get('ai_summary') and str(post.get('ai_summary')).strip() and str(post.get('ai_summary')) != 'None':
                            ai_analyzed_count += 1
                    
                    st.info(f"🤖 **AI Analysis Status:** {ai_analyzed_count}/{len(current_posts)} posts have AI summaries")
                    
                    # Add re-analysis option for posts without AI summaries
                    if ai_analyzed_count < len(current_posts):
                        if st.button("🤖 Re-analyze Posts Without AI Summary"):
                            st.info("🔄 This will trigger AI analysis for posts without summaries. Use the collection buttons in the sidebar to re-analyze.")
                
                for idx, post in current_posts.iterrows():
                    try:
                        # Get all possible date fields
                        date_fields = ['created_timestamp', 'created_at', 'saved_at', 'timestamp']
                        post_date = "Unknown"
                        
                        for date_field in date_fields:
                            if date_field in post and post[date_field] is not None:
                                try:
                                    post_date = pd.to_datetime(post[date_field]).strftime('%Y-%m-%d')
                                    break
                                except:
                                    continue
                        
                        # Get platform emoji
                        platform = str(post.get('platform', '')) if post.get('platform') is not None else ''
                        platform_emoji = {"twitter": "🐦", "reddit": "🤖", "threads": "🧵"}.get(platform, "📝")
                        
                        # Get score
                        score = post.get('value_score')
                        if score is not None and score != 'N/A':
                            try:
                                score_float = float(score)
                                score_display = f"{score_float:.1f}/10"
                            except (ValueError, TypeError):
                                score_display = "N/A"
                        else:
                            score_display = "N/A"
                        
                        # Get content preview
                        content = str(post.get('content', '')) if post.get('content') is not None else ''
                        content_preview = content[:100] + "..." if len(content) > 100 else content
                        
                        # Get AI summary - prioritize ai_summary field from IntelligentContentAnalyzer
                        summary_preview = ""
                        
                        # First try the main AI summary field
                        if 'ai_summary' in post and post['ai_summary'] is not None:
                            summary_text = str(post['ai_summary'])
                            if summary_text and summary_text.strip() and summary_text != 'None':
                                summary_preview = summary_text[:100] + "..." if len(summary_text) > 100 else summary_text
                        
                        # Fallback to other fields if ai_summary is empty
                        if not summary_preview:
                            fallback_fields = ['summary', 'ai_analysis', 'analysis', 'smart_tags', 'key_concepts']
                            for field in fallback_fields:
                                if field in post and post[field] is not None:
                                    try:
                                        summary_text = str(post[field])
                                        if summary_text and summary_text.strip() and summary_text != 'None':
                                            summary_preview = summary_text[:100] + "..." if len(summary_text) > 100 else summary_text
                                            break
                                    except:
                                        continue
                        
                        # If still no summary, create a basic one from content
                        if not summary_preview:
                            content = str(post.get('content', '')) if post.get('content') is not None else ''
                            if content and len(content) > 50:
                                summary_preview = f"📝 Content preview: {content[:80]}..."
                            else:
                                summary_preview = "🤖 AI analysis pending..."
                        
                        table_data.append({
                            'Platform': f"{platform_emoji} {platform.title()}",
                            'Author': str(post.get('author', 'Unknown')) if post.get('author') is not None else 'Unknown',
                            'Title': str(post.get('title', 'No title')) if post.get('title') is not None else 'No title',
                            'Content': content_preview,
                            'Category': str(post.get('category', 'Uncategorized')) if post.get('category') is not None else 'Uncategorized',
                            'Score': score_display,
                            'Date': post_date,
                            'AI Summary': summary_preview,
                            'URL': post.get('url', '') if post.get('url') is not None else ''
                        })
                    except Exception:
                        continue
                
                # Display as interactive table
                if table_data:
                    df_table = pd.DataFrame(table_data)
                    
                    # Add clickable URLs
                    def make_clickable(url):
                        if url and url != '':
                            return f'<a href="{url}" target="_blank">🔗 View</a>'
                        return ''
                    
                    df_table['Link'] = df_table['URL'].apply(make_clickable)
                    
                    # Display table with better formatting
                    st.dataframe(
                        df_table[['Platform', 'Author', 'Title', 'Content', 'Category', 'Score', 'Date', 'AI Summary', 'Link']],
                        width='stretch',
                        hide_index=True,
                        column_config={
                            "Platform": st.column_config.TextColumn("Platform", width="medium"),
                            "Author": st.column_config.TextColumn("Author", width="medium"),
                            "Title": st.column_config.TextColumn("Title", width="large"),
                            "Content": st.column_config.TextColumn("Content", width="large"),
                            "Category": st.column_config.TextColumn("Category", width="medium"),
                            "Score": st.column_config.TextColumn("Score", width="small"),
                            "Date": st.column_config.TextColumn("Date", width="small"),
                            "AI Summary": st.column_config.TextColumn("AI Summary", width="large"),
                            "Link": st.column_config.LinkColumn("Link", width="small")
                        }
                    )
                    
                    # Add export options
                    st.subheader("📤 Export Options")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        csv = df_table.to_csv(index=False)
                        st.download_button(
                            label="📥 Download CSV",
                            data=csv,
                            file_name=f"prismind_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv"
                        )
                    
                    with col2:
                        # Create a simple JSON export
                        json_data = df_table.to_dict('records')
                        st.download_button(
                            label="📥 Download JSON",
                            data=json.dumps(json_data, indent=2),
                            file_name=f"prismind_posts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                    
                    with col3:
                        if st.button("🔄 Refresh Table"):
                            st.rerun()
                    
                    # Add insights section
                    st.subheader("💡 Quick Insights")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Top categories
                        if 'Category' in df_table.columns:
                            category_counts = df_table['Category'].value_counts()
                            st.write("**🏆 Top Categories:**")
                            for category, count in category_counts.head(5).items():
                                st.write(f"  • {category}: {count} posts")
                    
                    with col2:
                        # Top authors
                        if 'Author' in df_table.columns:
                            author_counts = df_table['Author'].value_counts()
                            st.write("**👥 Top Authors:**")
                            for author, count in author_counts.head(5).items():
                                st.write(f"  • {author}: {count} posts")
                    
                    # High-value content
                    st.write("**⭐ High-Value Content (Score ≥ 8):**")
                    high_value = df_table[df_table['Score'].str.contains('8|9|10', na=False)]
                    if not high_value.empty:
                        for _, row in high_value.head(3).iterrows():
                            st.write(f"  • **{row['Title']}** by {row['Author']} ({row['Score']})")
                    else:
                        st.write("  • No high-value content found in current view")
                
                else:
                    st.info("📭 No posts found matching your criteria.")
                
                # Quick stats
                st.subheader("📊 Quick Stats")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Posts", total_posts)
                with col2:
                    try:
                        if 'category' in filtered_df.columns:
                            analyzed = len(filtered_df.dropna(subset=['category']))
                        else:
                            analyzed = 0
                        percentage = f"{analyzed/total_posts*100:.1f}%" if total_posts > 0 else "0%"
                        st.metric("AI Analyzed", analyzed, percentage)
                    except Exception:
                        st.metric("AI Analyzed", 0, "0%")
                with col3:
                    try:
                        if 'value_score' in filtered_df.columns:
                            avg_score = filtered_df['value_score'].mean()
                            if pd.isna(avg_score) or avg_score is None:
                                avg_score = 0
                        else:
                            avg_score = 0
                        st.metric("Avg Score", f"{avg_score:.1f}/10" if avg_score > 0 else "N/A")
                    except Exception:
                        st.metric("Avg Score", "N/A")
                with col4:
                    try:
                        if 'platform' in filtered_df.columns:
                            platforms = filtered_df['platform'].nunique()
                        else:
                            platforms = 0
                        st.metric("Platforms", platforms)
                    except Exception:
                        st.metric("Platforms", 0)
                
            else:
                st.info("📭 No posts found. Start collecting from the sidebar!")
                
                # Helpful tips section
                st.subheader("💡 Tips for Better Browsing")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("""
                    **🔍 Search Tips:**
                    - Search by author name
                    - Search by content keywords
                    - Search by post title
                    - Use quotes for exact phrases
                    """)
                
                with col2:
                    st.markdown("""
                    **📊 Filter Tips:**
                    - Filter by platform (Twitter, Reddit)
                    - Filter by AI category
                    - Sort by value score to find best content
                    - Use pagination to browse large collections
                    """)
                
                st.markdown("""
                **🚀 Getting Started:**
                1. Use the sidebar collection buttons to gather bookmarks
                2. Wait for AI analysis to complete
                3. Browse your intelligent content here!
                4. Use search and filters to find specific content
                """)
                
        except Exception as e:
            st.error(f"❌ Could not load posts: {e}")
            st.error("💡 Try refreshing the page or checking your database connection")

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
                    st.success("✅ Database connected!")
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
