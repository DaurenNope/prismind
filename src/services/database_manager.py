"""
Database management for PrisMind
Handles different database backends and provides a unified interface
"""
import os
import sqlite3
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from supabase import create_client, Client as SupabaseClient


class DatabaseManagerBase:
    """Base class for database managers"""
    
    def get_all_posts(self, include_deleted: bool = False) -> pd.DataFrame:
        """Get all posts from the database"""
        raise NotImplementedError
    
    def get_posts(self, limit: int = 100) -> pd.DataFrame:
        """Get a limited number of posts"""
        raise NotImplementedError
    
    def add_post(self, post_data: Dict[str, Any]) -> bool:
        """Add a new post to the database"""
        raise NotImplementedError


class SupabaseManager(DatabaseManagerBase):
    """Supabase database manager"""
    
    def __init__(self, client: SupabaseClient):
        self.client = client
        self.table_name = 'posts'
    
    def get_all_posts(self, include_deleted: bool = False) -> pd.DataFrame:
        try:
            query = self.client.table(self.table_name).select('*')
            response = query.execute()
            df = pd.DataFrame(response.data)
            
            if not include_deleted and 'deleted' in df.columns:
                df = df[~df['deleted']]
                
            if not df.empty and 'id' in df.columns:
                df = df.rename(columns={'id': 'post_id'})
                
            return df
        except Exception as e:
            print(f"Error fetching posts from Supabase: {e}")
            return pd.DataFrame()
    
    def get_posts(self, limit: int = 100) -> pd.DataFrame:
        try:
            response = self.client.table(self.table_name)\
                .select('*')\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            return pd.DataFrame(response.data)
        except Exception as e:
            print(f"Error fetching posts: {e}")
            return pd.DataFrame()
    
    def add_post(self, post_data: Dict[str, Any]) -> bool:
        try:
            self.client.table(self.table_name).insert(post_data).execute()
            return True
        except Exception as e:
            print(f"Error adding post: {e}")
            return False


class SQLiteManager(DatabaseManagerBase):
    """SQLite database manager"""
    
    def __init__(self, db_path: str = "prismind.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables and columns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create a table with the new schema
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                content TEXT,
                created_at TEXT,
                metadata TEXT,
                processed BOOLEAN DEFAULT 0,
                deleted BOOLEAN DEFAULT 0,
                post_id TEXT UNIQUE,
                url TEXT,
                author TEXT,
                author_handle TEXT,
                post_type TEXT,
                media_urls TEXT,
                hashtags TEXT,
                mentions TEXT,
                engagement TEXT,
                is_saved BOOLEAN DEFAULT 1,
                saved_at TEXT,
                folder_category TEXT,
                subreddit TEXT,
                title TEXT,
                category TEXT,
                value_score REAL,
                sentiment TEXT,
                ai_summary TEXT,
                key_concepts TEXT,
                smart_tags TEXT,
                intelligence_analysis TEXT,
                actionable_insights TEXT
            )
            ''')
            
                    
                    # Copy data from old table to new table
                    cursor.execute('''
                    INSERT INTO posts_new (
                        id, platform, content, created_at, metadata, processed, deleted,
                        post_id, url, author, author_handle, post_type, media_urls, hashtags, mentions, engagement, is_saved, saved_at,
                        folder_category, subreddit, title, category, value_score, sentiment, ai_summary, key_concepts, smart_tags, intelligence_analysis, actionable_insights
                    )
                    SELECT 
                        id, platform, content, created_at, metadata, processed, deleted,
                        post_id, url, author, author_handle, post_type, NULL, NULL, NULL, NULL, NULL, NULL,
                        NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL
                    FROM posts_old
                    ''')
                    
                    # Drop the old table
                    cursor.execute("DROP TABLE posts_old;")
            
            # Rename new table to posts
            cursor.execute("DROP TABLE IF EXISTS posts;")
            cursor.execute("ALTER TABLE posts_new RENAME TO posts;")
            
            # Create indexes for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_url ON posts(url)')
            
            conn.commit()
            print("✅ Database initialized with all required columns and indexes")
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            import traceback
            traceback.print_exc()
    
    def get_all_posts(self, include_deleted: bool = False) -> pd.DataFrame:
        try:
            query = "SELECT * FROM posts"
            if not include_deleted:
                query += " WHERE deleted = 0"
                
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn)
            conn.close()
            return df
        except Exception as e:
            print(f"Error fetching posts from SQLite: {e}")
            return pd.DataFrame()
    
    def get_posts(self, limit: int = 100) -> pd.DataFrame:
        try:
            query = """
            SELECT * FROM posts 
            WHERE deleted = 0 
            ORDER BY created_at DESC 
            LIMIT ?
            """
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query(query, conn, params=(limit,))
            conn.close()
            return df
        except Exception as e:
            print(f"Error fetching posts: {e}")
            return pd.DataFrame()
    
    def add_post(self, post_data: Dict[str, Any]) -> bool:
        """
        Add a new post to the database with improved duplicate detection.
        
        Args:
            post_data: Dictionary containing post data including 'post_id', 'platform', 'content', etc.
            
        Returns:
            bool: True if post was added, False if it was a duplicate or an error occurred
        """
        if not post_data:
            print("⚠️ No post data provided")
            return False
            
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get post_id from post_data, metadata, or 'id' field (for Reddit)
            post_id = (post_data.get('post_id') or 
                     (post_data.get('metadata') or {}).get('tweet_id') or
                     post_data.get('id'))
            
            # For Reddit, ensure we have a string ID
            if post_id and hasattr(post_id, 'id'):
                post_id = str(post_id.id)
            
            # Check if post already exists by post_id if available
            if post_id:
                cursor.execute(
                    "SELECT id FROM posts WHERE post_id = ?",
                    (str(post_id),)
                )
                if cursor.fetchone() is not None:
                    print(f"⚠️ Post with ID {post_id} already exists in database")
                    return False
            
            # Prepare the post data for insertion
            created_at = post_data.get('created_at')
            if isinstance(created_at, (str, int, float)):
                try:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    else:
                        created_at = datetime.fromtimestamp(created_at)
                except (ValueError, TypeError):
                    created_at = datetime.utcnow()
            elif not isinstance(created_at, datetime):
                created_at = datetime.utcnow()
            
            # Prepare metadata
            metadata = post_data.get('metadata', {})
            if not isinstance(metadata, dict):
                metadata = {}
            
            # Add post_id to metadata if not already present
            if post_id and 'tweet_id' not in metadata:
                metadata['tweet_id'] = post_id
            
            # Prepare complex fields for JSON serialization
            media_urls = post_data.get('media_urls', [])
            if not isinstance(media_urls, (list, str)):
                media_urls = []
            
            hashtags = post_data.get('hashtags', [])
            if not isinstance(hashtags, (list, str)):
                hashtags = []
            
            mentions = post_data.get('mentions', [])
            if not isinstance(mentions, (list, str)):
                mentions = []
            
            engagement = post_data.get('engagement', {})
            if not isinstance(engagement, dict):
                engagement = {}
            
            # Handle saved_at timestamp
            saved_at = post_data.get('saved_at')
            if isinstance(saved_at, (str, int, float)):
                try:
                    if isinstance(saved_at, str):
                        saved_at = datetime.fromisoformat(saved_at.replace('Z', '+00:00'))
                    else:
                        saved_at = datetime.fromtimestamp(saved_at)
                except (ValueError, TypeError):
                    saved_at = datetime.utcnow()
            elif not isinstance(saved_at, datetime):
                saved_at = datetime.utcnow()
            
            # Insert the new post with all fields
            cursor.execute("""
            INSERT INTO posts (
                platform, content, created_at, metadata, post_id, url, author, author_handle,
                post_type, media_urls, hashtags, mentions, engagement, is_saved, saved_at,
                folder_category, subreddit, title, category, value_score, sentiment,
                ai_summary, key_concepts, smart_tags, intelligence_analysis, actionable_insights
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """, (
                post_data.get('platform'),
                post_data.get('content'),
                created_at.isoformat(),
                json.dumps(metadata, ensure_ascii=False),
                str(post_id) if post_id else None,
                post_data.get('url'),
                post_data.get('author'),
                post_data.get('author_handle'),
                post_data.get('post_type', 'post'),
                json.dumps(media_urls, ensure_ascii=False) if media_urls else None,
                json.dumps(hashtags, ensure_ascii=False) if hashtags else None,
                json.dumps(mentions, ensure_ascii=False) if mentions else None,
                json.dumps(engagement, ensure_ascii=False) if engagement else None,
                int(bool(post_data.get('is_saved', True))),
                saved_at.isoformat(),
                post_data.get('folder_category'),
                post_data.get('subreddit'),
                post_data.get('title'),
                post_data.get('category'),
                float(post_data['value_score']) if 'value_score' in post_data and post_data['value_score'] is not None else None,
                post_data.get('sentiment'),
                post_data.get('ai_summary'),
                post_data.get('key_concepts'),
                post_data.get('smart_tags'),
                post_data.get('intelligence_analysis'),
                post_data.get('actionable_insights')
            ))
            
            conn.commit()
            print(f"✅ Added new post: {post_id or 'no-id'}")
            return True
            
        except Exception as e:
            print(f"❌ Error adding post: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if conn:
                conn.close()


def get_database_manager() -> DatabaseManagerBase:
    """Factory function to get the appropriate database manager"""
    # Try Supabase first if configured
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    
    if supabase_url and supabase_key:
        try:
            supabase = create_client(supabase_url, supabase_key)
            return SupabaseManager(supabase)
        except Exception as e:
            print(f"Failed to initialize Supabase, falling back to SQLite: {e}")
    
    # Fall back to SQLite
    return SQLiteManager()
