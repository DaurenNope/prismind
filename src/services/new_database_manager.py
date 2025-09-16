"""
Database management for PrisMind
Handles different database backends and provides a unified interface
"""
import os
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union

class DatabaseManagerBase:
    """Base class for database managers"""
    
    def get_all_posts(self, include_deleted: bool = False) -> List[Dict]:
        """Get all posts from the database"""
        raise NotImplementedError
        
    def get_posts(self, limit: int = 100) -> List[Dict]:
        """Get a limited number of posts"""
        raise NotImplementedError
        
    def add_post(self, post_data: Dict[str, Any]) -> bool:
        """Add a new post to the database"""
        raise NotImplementedError


class SQLiteManager(DatabaseManagerBase):
    """SQLite database manager"""
    
    def __init__(self, db_path: str = "prismind.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the database with required tables and columns"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='posts';
            """)
            
            if not cursor.fetchone():
                # Table doesn't exist, create it with all columns
                cursor.execute('''
                CREATE TABLE posts (
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
                print("✅ Created new posts table with all required columns")
            else:
                # Table exists, check for missing columns and add them
                cursor.execute("PRAGMA table_info(posts)")
                existing_columns = {row[1] for row in cursor.fetchall()}
                
                # Define all expected columns and their SQL types
                expected_columns = {
                    'platform': 'TEXT NOT NULL',
                    'content': 'TEXT',
                    'created_at': 'TEXT',
                    'metadata': 'TEXT',
                    'processed': 'BOOLEAN DEFAULT 0',
                    'deleted': 'BOOLEAN DEFAULT 0',
                    'post_id': 'TEXT UNIQUE',
                    'url': 'TEXT',
                    'author': 'TEXT',
                    'author_handle': 'TEXT',
                    'post_type': 'TEXT',
                    'media_urls': 'TEXT',
                    'hashtags': 'TEXT',
                    'mentions': 'TEXT',
                    'engagement': 'TEXT',
                    'is_saved': 'BOOLEAN DEFAULT 1',
                    'saved_at': 'TEXT',
                    'folder_category': 'TEXT',
                    'subreddit': 'TEXT',
                    'title': 'TEXT',
                    'category': 'TEXT',
                    'value_score': 'REAL',
                    'sentiment': 'TEXT',
                    'ai_summary': 'TEXT',
                    'key_concepts': 'TEXT',
                    'smart_tags': 'TEXT',
                    'intelligence_analysis': 'TEXT',
                    'actionable_insights': 'TEXT'
                }
                
                # Add any missing columns
                for column, column_type in expected_columns.items():
                    if column not in existing_columns:
                        cursor.execute(f"ALTER TABLE posts ADD COLUMN {column} {column_type}")
                
                print("✅ Verified and updated posts table schema")
            
            # Create indexes for faster lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_author ON posts(author)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_subreddit ON posts(subreddit)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_posts_url ON posts(url)')
            
            conn.commit()
            print("✅ Database initialized with all required columns and indexes")
    
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
            post_id = post_data.get('post_id') or post_data.get('id')
            
            # For Reddit, ensure we have a string ID
            if post_id and hasattr(post_id, 'id'):
                post_id = str(post_id.id)
            elif post_id is not None:
                post_id = str(post_id)
                
            print(f"🔍 Processing post with ID: {post_id}")
            
            # Check if post already exists by post_id if available
            if post_id:
                cursor.execute(
                    "SELECT id FROM posts WHERE post_id = ?",
                    (post_id,)
                )
                if cursor.fetchone() is not None:
                    print(f"⚠️ Post with ID {post_id} already exists in database")
                    return False
            
            # Prepare the post data for insertion
            created_at = post_data.get('created_at')
            if isinstance(created_at, (str)):
                try:
                    # Try parsing ISO format
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    try:
                        # Try parsing as timestamp
                        created_at = datetime.fromtimestamp(float(created_at))
                    except (ValueError, TypeError):
                        created_at = datetime.utcnow()
            elif isinstance(created_at, (int, float)):
                try:
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
            if post_id and 'post_id' not in metadata:
                metadata['post_id'] = post_id
            
            # Prepare complex fields for JSON serialization
            def safe_json_serialize(obj):
                if obj is None:
                    return None
                try:
                    return json.dumps(obj, ensure_ascii=False, default=str)
                except (TypeError, ValueError) as e:
                    print(f"⚠️ Error serializing to JSON: {e}")
                    return json.dumps({"error": "Could not serialize data"}, ensure_ascii=False)
            
            # Handle media_urls - ensure it's a list of strings
            media_urls = post_data.get('media_urls', [])
            if isinstance(media_urls, str):
                media_urls = [media_urls] if media_urls else []
            elif not isinstance(media_urls, list):
                media_urls = []
                
            # Ensure all items in media_urls are strings
            media_urls = [str(url) for url in media_urls if url is not None]
            
            # Handle other list fields
            list_fields = ['hashtags', 'mentions']
            for field in list_fields:
                if field in post_data and not isinstance(post_data[field], list):
                    post_data[field] = [post_data[field]] if post_data[field] is not None else []
            
            # Prepare engagement data
            engagement = post_data.get('engagement', {})
            if not isinstance(engagement, dict):
                engagement = {}
                
            # Ensure all string fields are properly encoded
            string_fields = ['platform', 'content', 'url', 'author', 'author_handle', 
                           'post_type', 'subreddit', 'title', 'category', 'sentiment',
                           'ai_summary', 'key_concepts', 'smart_tags', 'intelligence_analysis',
                           'actionable_insights', 'folder_category']
            
            for field in string_fields:
                if field in post_data and post_data[field] is not None:
                    post_data[field] = str(post_data[field])
                
            print(f"📝 Preparing to insert post: {post_data.get('title', 'No title')}")
            print(f"   Platform: {post_data.get('platform')}, Post ID: {post_id}")
            
            # Prepare all fields for insertion
            insert_data = {
                'post_id': post_id,
                'platform': post_data.get('platform', 'unknown'),
                'content': post_data.get('content', ''),
                'created_at': created_at.isoformat(),
                'url': post_data.get('url', ''),
                'author': post_data.get('author', ''),
                'author_handle': post_data.get('author_handle', ''),
                'post_type': post_data.get('post_type', 'post'),
                'subreddit': post_data.get('subreddit', ''),
                'title': post_data.get('title', ''),
                'folder_category': post_data.get('folder_category', ''),
                'is_saved': 1 if post_data.get('is_saved', True) else 0,
                'saved_at': datetime.utcnow().isoformat(),
                'processed': 0,
                'deleted': 0,
                
                # JSON serialized fields
                'metadata': safe_json_serialize(metadata),
                'media_urls': safe_json_serialize(media_urls),
                'hashtags': safe_json_serialize(post_data.get('hashtags', [])),
                'mentions': safe_json_serialize(post_data.get('mentions', [])),
                'engagement': safe_json_serialize(engagement),
                
                # Optional fields with defaults
                'category': post_data.get('category', ''),
                'value_score': float(post_data.get('value_score', 0.0)) if post_data.get('value_score') is not None else None,
                'sentiment': post_data.get('sentiment', ''),
                'ai_summary': post_data.get('ai_summary', ''),
                'key_concepts': post_data.get('key_concepts', ''),
                'smart_tags': post_data.get('smart_tags', ''),
                'intelligence_analysis': post_data.get('intelligence_analysis', ''),
                'actionable_insights': post_data.get('actionable_insights', '')
            }
            
            # Build the SQL query
            columns = ', '.join(insert_data.keys())
            placeholders = ', '.join(['?'] * len(insert_data))
            values = tuple(insert_data.values())
            
            try:
                # Insert the post
                cursor.execute(
                    f"""
                    INSERT INTO posts ({columns})
                    VALUES ({placeholders})
                    """,
                    values
                )
                conn.commit()
                print(f"✅ Successfully inserted post: {post_id}")
                return True
                
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed: posts.post_id" in str(e):
                    print(f"⚠️ Post with ID {post_id} already exists (integrity error)")
                else:
                    print(f"❌ Database integrity error: {e}")
                return False
                
            except sqlite3.Error as e:
                print(f"❌ Database error: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Unexpected error in add_post: {e}")
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if conn:
                conn.close()
    
    def get_all_posts(self, include_deleted: bool = False) -> List[Dict]:
        """Get all posts from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM posts"
                params = ()
                
                if not include_deleted:
                    query += " WHERE deleted = 0"
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                # Convert rows to dictionaries
                posts = []
                for row in rows:
                    post = dict(row)
                    # Parse JSON fields
                    for field in ['metadata', 'media_urls', 'hashtags', 'mentions', 'engagement']:
                        if post.get(field) and isinstance(post[field], str):
                            try:
                                post[field] = json.loads(post[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    posts.append(post)
                
                return posts
                
        except Exception as e:
            print(f"❌ Error retrieving posts: {e}")
            return []
    
    def get_posts(self, limit: int = 100) -> List[Dict]:
        """Get a limited number of posts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM posts WHERE deleted = 0 ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
                
                rows = cursor.fetchall()
                
                # Convert rows to dictionaries
                posts = []
                for row in rows:
                    post = dict(row)
                    # Parse JSON fields
                    for field in ['metadata', 'media_urls', 'hashtags', 'mentions', 'engagement']:
                        if post.get(field) and isinstance(post[field], str):
                            try:
                                post[field] = json.loads(post[field])
                            except (json.JSONDecodeError, TypeError):
                                pass
                    posts.append(post)
                
                return posts
                
        except Exception as e:
            print(f"❌ Error retrieving posts: {e}")
            return []


def get_database_manager() -> DatabaseManagerBase:
    """Factory function to get the appropriate database manager"""
    # For now, always use SQLite
    return SQLiteManager()


if __name__ == "__main__":
    # Test the database manager
    db = SQLiteManager("test_prismind.db")
    
    # Test adding a post
    test_post = {
        "platform": "reddit",
        "content": "This is a test post",
        "post_id": "test123",
        "url": "https://reddit.com/r/test/comments/test123/",
        "author": "testuser",
        "title": "Test Post",
        "subreddit": "test",
        "media_urls": ["https://example.com/image.jpg"],
        "created_at": datetime.utcnow().isoformat(),
        "is_saved": True,
        "saved_at": datetime.utcnow().isoformat()
    }
    
    # Add the test post
    success = db.add_post(test_post)
    print(f"Added test post: {success}")
    
    # Retrieve all posts
    posts = db.get_all_posts()
    print(f"Retrieved {len(posts)} posts")
    for i, post in enumerate(posts, 1):
        print(f"\nPost {i}:")
        for key, value in post.items():
            print(f"  {key}: {value}")
