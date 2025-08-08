import sqlite3
import json
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import streamlit as st

class DatabaseManager:
    """
    DatabaseManager handles all database operations for the PrisMind application.
    
    This class provides a unified interface for interacting with the SQLite database,
    including operations for posts, user interactions, preferences, and content curation.
    
    Attributes:
        db_path (Path): Path to the SQLite database file
    """
    
    def __init__(self, db_path="data/prismind.db"):
        """
        Initialize the DatabaseManager.
        
        Args:
            db_path (str): Path to the SQLite database file. Defaults to "data/prismind.db".
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self.init_database()
        self.migrate_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Posts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT UNIQUE,
                    platform TEXT,
                    author TEXT,
                    content TEXT,
                    created_at TEXT,
                    url TEXT,
                    value_score REAL,
                    engagement_score REAL,
                    sentiment TEXT,
                    folder_category TEXT,
                    ai_summary TEXT,
                    key_concepts TEXT,
                    is_deleted INTEGER DEFAULT 0,
                    created_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User interactions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT,
                    interaction_type TEXT, -- 'like', 'dislike', 'hide', 'bookmark'
                    user_id TEXT DEFAULT 'default',
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (post_id)
                )
            """)
            
            # User preferences table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT DEFAULT 'default',
                    category TEXT,
                    preference_score REAL, -- -1 to 1 (dislike to like)
                    interaction_count INTEGER DEFAULT 0,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Content curation table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS content_curation (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT,
                    use_case TEXT, -- 'research', 'copywriting', 'learning', 'strategy'
                    status TEXT DEFAULT 'pending', -- 'pending', 'in_progress', 'completed'
                    notes TEXT,
                    priority INTEGER DEFAULT 1, -- 1-5 (low to high)
                    user_id TEXT DEFAULT 'default',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (post_id)
                )
            """)
            
            conn.commit()
    
    def migrate_database(self):
        """Migrate database to add new columns for enhanced analysis"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check existing columns
            cursor.execute("PRAGMA table_info(posts)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            # Add missing columns for enhanced analysis
            new_columns = [
                ('category', 'TEXT'),
                ('subcategory', 'TEXT'),
                ('topic', 'TEXT'),
                ('content_type', 'TEXT'),
                ('complexity_level', 'TEXT'),
                ('author_handle', 'TEXT'),
                ('post_type', 'TEXT'),
                ('media_urls', 'TEXT'),
                ('hashtags', 'TEXT'),
                ('mentions', 'TEXT'),
                ('upvote_ratio', 'REAL'),
                ('num_comments', 'INTEGER'),
                ('is_saved', 'INTEGER DEFAULT 1'),
                ('saved_at', 'TEXT'),
                ('summary', 'TEXT'),
                ('intelligence_analysis', 'TEXT'),
                ('comment_analysis', 'TEXT'),
                ('media_analysis', 'TEXT')
            ]
            
            for column_name, column_type in new_columns:
                if column_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE posts ADD COLUMN {column_name} {column_type}")
                        print(f"✅ Added column: {column_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"⚠️ Could not add column {column_name}: {e}")
            
            conn.commit()
    
    def add_post(self, post_data):
        """Add a new post to the database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO posts 
                (post_id, platform, author, author_handle, content, created_at, url, post_type,
                 media_urls, hashtags, mentions, engagement_score, value_score, 
                 sentiment, folder_category, ai_summary, key_concepts, is_saved, saved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data.get('post_id'),
                post_data.get('platform'),
                post_data.get('author'),
                post_data.get('author_handle'),
                post_data.get('content'),
                post_data.get('created_at'),
                post_data.get('url'),
                post_data.get('post_type', 'post'),
                json.dumps(post_data.get('media_urls', [])),  # Store as JSON
                json.dumps(post_data.get('hashtags', [])),    # Store as JSON
                json.dumps(post_data.get('mentions', [])),    # Store as JSON
                post_data.get('engagement_score'),
                post_data.get('value_score'),
                post_data.get('sentiment'),
                post_data.get('folder_category'),
                post_data.get('ai_summary'),
                json.dumps(post_data.get('key_concepts', [])),
                post_data.get('is_saved', True),
                post_data.get('saved_at')
            ))
            conn.commit()

    # --------------------
    # Simple CRUD API used by tests
    # --------------------
    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        return {k: row[k] for k in row.keys()}

    def insert_post(self, post_data: Dict[str, Any]) -> int:
        """Insert a post and return its internal numeric id."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO posts (
                    post_id, platform, author, content, created_at, url,
                    value_score, engagement_score, sentiment, folder_category,
                    ai_summary, key_concepts, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_data.get('post_id'),
                    post_data.get('platform'),
                    post_data.get('author'),
                    post_data.get('content'),
                    post_data.get('created_at'),
                    post_data.get('url'),
                    post_data.get('value_score'),
                    post_data.get('engagement_score'),
                    post_data.get('sentiment'),
                    post_data.get('folder_category'),
                    post_data.get('ai_summary'),
                    post_data.get('key_concepts'),
                    post_data.get('is_deleted', 0),
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_posts(self, limit: int | None = None) -> List[Dict[str, Any]]:
        """Return non-deleted posts as list of dicts, optionally limited."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            sql = "SELECT * FROM posts WHERE is_deleted = 0 ORDER BY created_timestamp DESC"
            if limit is not None:
                sql += " LIMIT ?"
                rows = conn.execute(sql, (limit,)).fetchall()
            else:
                rows = conn.execute(sql).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_post_by_id(self, row_id: int) -> Dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM posts WHERE id = ?", (row_id,)).fetchone()
            return self._row_to_dict(row) if row else None

    def update_post(self, identifier: int | str, updates: Dict[str, Any]) -> bool:
        """Update fields for a post by internal numeric id or external post_id.

        Returns True when an update statement is executed (even if no rows changed).
        """
        if not updates:
            return True
        set_clauses: list[str] = []
        values: list[Any] = []
        for key, value in updates.items():
            set_clauses.append(f"{key} = ?")
            values.append(value)
        where_sql = "id = ?" if isinstance(identifier, int) else "post_id = ?"
        values.append(identifier)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE posts SET {', '.join(set_clauses)} WHERE {where_sql}", values)
            conn.commit()
        return True
    
    def delete_post(self, identifier):
        """Soft delete a post (mark as deleted).
        Accepts either numeric internal id or string external post_id.
        """
        with sqlite3.connect(self.db_path) as conn:
            if isinstance(identifier, int):
                conn.execute("UPDATE posts SET is_deleted = 1 WHERE id = ?", (identifier,))
            else:
                conn.execute("UPDATE posts SET is_deleted = 1 WHERE post_id = ?", (identifier,))
            conn.commit()

    def search_posts(self, query: str) -> List[Dict[str, Any]]:
        """Search posts by content, author, or AI summary."""
        like = f"%{query}%"
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT * FROM posts
                WHERE is_deleted = 0 AND (
                    content LIKE ? OR author LIKE ? OR ai_summary LIKE ?
                )
                ORDER BY created_timestamp DESC
                """,
                (like, like, like),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_posts_by_category(self, category: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM posts WHERE is_deleted = 0 AND folder_category = ? ORDER BY created_timestamp DESC",
                (category,),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_top_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM posts WHERE is_deleted = 0 ORDER BY value_score DESC, created_timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [self._row_to_dict(r) for r in rows]

    def get_database_stats(self) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            total_posts = cursor.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
            active_posts = cursor.execute("SELECT COUNT(*) FROM posts WHERE is_deleted = 0").fetchone()[0]
            deleted_posts = total_posts - active_posts
            return {
                'total_posts': total_posts,
                'active_posts': active_posts,
                'deleted_posts': deleted_posts,
            }
    
    def get_all_posts(self, include_deleted=False):
        """Get all posts from database"""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT * FROM posts"
            if not include_deleted:
                query += " WHERE is_deleted = 0"
            query += " ORDER BY created_timestamp DESC"
            
            df = pd.read_sql_query(query, conn)
            return df
    
    def record_interaction(self, post_id, interaction_type, user_id='default'):
        """Record a user interaction with a post"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO user_interactions (post_id, interaction_type, user_id)
                VALUES (?, ?, ?)
            """, (post_id, interaction_type, user_id))
            conn.commit()
    
    def get_user_preferences(self, user_id='default'):
        """Get user preferences based on interactions"""
        with sqlite3.connect(self.db_path) as conn:
            # Calculate preferences based on interactions
            query = """
                SELECT 
                    p.folder_category,
                    AVG(CASE 
                        WHEN ui.interaction_type = 'like' THEN 1.0
                        WHEN ui.interaction_type = 'dislike' THEN -1.0
                        ELSE 0.0
                    END) as preference_score,
                    COUNT(ui.id) as interaction_count
                FROM posts p
                LEFT JOIN user_interactions ui ON p.post_id = ui.post_id AND ui.user_id = ?
                WHERE p.is_deleted = 0
                GROUP BY p.folder_category
                HAVING interaction_count > 0
                ORDER BY preference_score DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(user_id,))
            return df
    
    def get_personalized_posts(self, user_id='default', limit=50):
        """Get personalized posts based on user preferences and interactions"""
        with sqlite3.connect(self.db_path) as conn:
            # Get user preferences with enhanced learning
            query = """
                SELECT p.*, 
                       COALESCE(pref.preference_score, 0) as user_preference_score,
                       COALESCE(hidden.hidden_count, 0) as hidden_count,
                       COALESCE(liked.like_count, 0) as like_count,
                       COALESCE(disliked.dislike_count, 0) as dislike_count
                FROM posts p
                LEFT JOIN (
                    SELECT 
                        folder_category,
                        AVG(CASE 
                            WHEN interaction_type = 'like' THEN 1.0
                            WHEN interaction_type = 'dislike' THEN -1.0
                            WHEN interaction_type = 'hide' THEN -2.0  -- Strong negative signal
                            ELSE 0.0
                        END) as preference_score
                    FROM user_interactions ui
                    JOIN posts p ON ui.post_id = p.post_id
                    WHERE ui.user_id = ? AND p.is_deleted = 0
                    GROUP BY p.folder_category
                ) pref ON p.folder_category = pref.folder_category
                LEFT JOIN (
                    SELECT folder_category, COUNT(*) as hidden_count
                    FROM user_interactions ui
                    JOIN posts p ON ui.post_id = p.post_id
                    WHERE ui.user_id = ? AND ui.interaction_type = 'hide'
                    GROUP BY p.folder_category
                ) hidden ON p.folder_category = hidden.folder_category
                LEFT JOIN (
                    SELECT folder_category, COUNT(*) as like_count
                    FROM user_interactions ui
                    JOIN posts p ON ui.post_id = p.post_id
                    WHERE ui.user_id = ? AND ui.interaction_type = 'like'
                    GROUP BY p.folder_category
                ) liked ON p.folder_category = liked.folder_category
                LEFT JOIN (
                    SELECT folder_category, COUNT(*) as dislike_count
                    FROM user_interactions ui
                    JOIN posts p ON ui.post_id = p.post_id
                    WHERE ui.user_id = ? AND ui.interaction_type = 'dislike'
                    GROUP BY p.folder_category
                ) disliked ON p.folder_category = disliked.folder_category
                WHERE p.is_deleted = 0
                ORDER BY (
                    p.value_score * 0.3 + 
                    p.engagement_score * 0.2 + 
                    COALESCE(pref.preference_score, 0) * 0.4 +
                    (COALESCE(liked.like_count, 0) - COALESCE(disliked.dislike_count, 0) - COALESCE(hidden.hidden_count, 0) * 2) * 0.1
                ) DESC
                LIMIT ?
            """
            
            df = pd.read_sql_query(query, conn, params=(user_id, user_id, user_id, user_id, limit))
            return df
    
    def get_user_learning_insights(self, user_id='default'):
        """Get insights about user's learning patterns"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT 
                    p.folder_category,
                    COUNT(CASE WHEN ui.interaction_type = 'like' THEN 1 END) as likes,
                    COUNT(CASE WHEN ui.interaction_type = 'dislike' THEN 1 END) as dislikes,
                    COUNT(CASE WHEN ui.interaction_type = 'hide' THEN 1 END) as hides,
                    COUNT(CASE WHEN ui.interaction_type = 'bookmark' THEN 1 END) as bookmarks,
                    AVG(p.value_score) as avg_value_score,
                    AVG(p.engagement_score) as avg_engagement_score
                FROM posts p
                LEFT JOIN user_interactions ui ON p.post_id = ui.post_id AND ui.user_id = ?
                WHERE p.is_deleted = 0
                GROUP BY p.folder_category
                HAVING (likes + dislikes + hides + bookmarks) > 0
                ORDER BY (likes - dislikes - hides * 2) DESC
            """
            
            df = pd.read_sql_query(query, conn, params=(user_id,))
            return df
    
    def extract_valuable_comments(self, post_id):
        """Extract the most valuable comments from a post"""
        with sqlite3.connect(self.db_path) as conn:
            # This would typically query a comments table
            # For now, we'll simulate comment extraction from the post content
            query = """
                SELECT content, engagement_score, value_score, sentiment
                FROM posts 
                WHERE post_id = ? AND is_deleted = 0
            """
            
            df = pd.read_sql_query(query, conn, params=(post_id,))
            if not df.empty:
                post_data = df.iloc[0]
                
                # Simulate comment extraction by analyzing the content
                comments = []
                content = post_data.get('content', '')
                
                # Split content into potential "comment-like" segments
                if content:
                    segments = content.split('. ')
                    for i, segment in enumerate(segments[:5]):  # Top 5 segments
                        if len(segment) > 20:  # Only meaningful segments
                            score = 0
                            if any(word in segment.lower() for word in ['because', 'however', 'therefore', 'example']):
                                score += 2
                            if len(segment) > 100:
                                score += 1
                            if any(word in segment.lower() for word in ['expert', 'professional', 'specialist']):
                                score += 1
                            
                            if score >= 1:
                                comments.append({
                                    'content': segment,
                                    'author': f'Commenter_{i+1}',
                                    'upvotes': score * 10,
                                    'score': score
                                })
                
                return sorted(comments, key=lambda x: x['score'], reverse=True)
            
            return []
    
    def get_bookmark_insights(self, post_id):
        """Get comprehensive insights for a bookmark"""
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT *, 
                       CASE 
                           WHEN value_score >= 8 THEN 'High Value'
                           WHEN value_score >= 6 THEN 'Medium Value'
                           ELSE 'Low Value'
                       END as value_category,
                       CASE 
                           WHEN engagement_score >= 1000 THEN 'Viral'
                           WHEN engagement_score >= 500 THEN 'Popular'
                           ELSE 'Standard'
                       END as engagement_category
                FROM posts 
                WHERE post_id = ? AND is_deleted = 0
            """
            
            df = pd.read_sql_query(query, conn, params=(post_id,))
            if not df.empty:
                post_data = df.iloc[0]
                
                # Extract valuable comments
                comments = self.extract_valuable_comments(post_id)
                
                # Generate insights
                insights = {
                    'post_data': post_data,
                    'valuable_comments': comments,
                    'key_insights': [],
                    'actionable_items': [],
                    'learning_opportunities': []
                }
                
                # Analyze content for insights
                content = post_data.get('content', '')
                if content:
                    # Look for actionable content
                    if any(word in content.lower() for word in ['how to', 'tutorial', 'guide', 'step by step']):
                        insights['actionable_items'].append('Contains tutorial/guide content')
                    
                    # Look for learning opportunities
                    if any(word in content.lower() for word in ['learn', 'understand', 'concept', 'principle']):
                        insights['learning_opportunities'].append('Contains learning content')
                    
                    # Extract key insights from AI summary
                    ai_summary = post_data.get('ai_summary', '')
                    if ai_summary:
                        insights['key_insights'].append(ai_summary)
                
                return insights
            
            return None
    
    def get_comments_for_post(self, post_id):
        """Get comments for a specific post"""
        # For now, we'll simulate comments by extracting insights from the post content
        with sqlite3.connect(self.db_path) as conn:
            query = """
                SELECT content, engagement_score, value_score, sentiment
                FROM posts 
                WHERE post_id = ? AND is_deleted = 0
            """
            
            df = pd.read_sql_query(query, conn, params=(post_id,))
            if not df.empty:
                post_data = df.iloc[0]
                content = post_data.get('content', '')
                
                # Simulate comments by analyzing content segments
                comments = []
                if content:
                    # Split content into meaningful segments
                    segments = content.split('. ')
                    for i, segment in enumerate(segments[:3]):  # Top 3 segments as "comments"
                        if len(segment) > 30:  # Only meaningful segments
                            score = 0
                            if any(word in segment.lower() for word in ['because', 'however', 'therefore', 'example']):
                                score += 2
                            if len(segment) > 100:
                                score += 1
                            if any(word in segment.lower() for word in ['expert', 'professional', 'specialist']):
                                score += 1
                            
                            if score >= 1:
                                comments.append({
                                    'content': segment,
                                    'author': f'Commenter_{i+1}',
                                    'upvotes': score * 15,
                                    'score': score
                                })
                
                return sorted(comments, key=lambda x: x['score'], reverse=True)
            
            return []
    
    def update_post_analysis(self, post_id: str, analysis_data: Dict[str, Any]):
        """Update a post with intelligent analysis data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Prepare comment analysis data
                comment_analysis = analysis_data.get('comment_analysis')
                if comment_analysis and isinstance(comment_analysis, dict):
                    comment_analysis = json.dumps(comment_analysis, ensure_ascii=False)
                
                # Prepare media analysis data
                media_analysis = analysis_data.get('media_analysis')
                if media_analysis and isinstance(media_analysis, dict):
                    media_analysis = json.dumps(media_analysis, ensure_ascii=False)
                
                # Prepare key concepts (convert list to JSON string)
                key_concepts = analysis_data.get('key_concepts')
                if key_concepts and isinstance(key_concepts, list):
                    key_concepts = json.dumps(key_concepts, ensure_ascii=False)
                
                # Prepare intelligence analysis (convert dict to JSON string)
                intelligence_analysis = analysis_data.get('intelligence_analysis')
                if intelligence_analysis and isinstance(intelligence_analysis, dict):
                    intelligence_analysis = json.dumps(intelligence_analysis, ensure_ascii=False)
                
                # Update the post with new analysis
                cursor.execute("""
                    UPDATE posts 
                    SET category = ?, topic = ?, key_concepts = ?, summary = ?, 
                        sentiment = ?, value_score = ?, comment_analysis = ?, media_analysis = ?, intelligence_analysis = ?
                    WHERE post_id = ?
                """, (
                    analysis_data.get('category'),
                    analysis_data.get('topic'),
                    key_concepts,
                    analysis_data.get('summary'),
                    analysis_data.get('sentiment'),
                    analysis_data.get('value_score'),
                    comment_analysis,
                    media_analysis,
                    intelligence_analysis,
                    post_id
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating post analysis: {e}")
            return False
    
    def update_post_content(self, post_id: str, new_content: str):
        """Update a post's content (e.g., to add comments)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE posts 
                    SET content = ?
                    WHERE post_id = ?
                """, (new_content, post_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating post content: {e}")
            return False
    
    def update_post_smart_fields(self, post_id: str, **kwargs):
        """Update any post fields with AI analysis results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                update_fields = []
                update_values = []
                
                # Handle all possible AI analysis fields
                field_mappings = {
                    'category': 'category',
                    'value_score': 'value_score',
                    'sentiment': 'sentiment',
                    'ai_summary': 'ai_summary',
                    'key_concepts': 'key_concepts',
                    'smart_tags': 'smart_tags',
                    'intelligence_analysis': 'intelligence_analysis',
                    'actionable_insights': 'actionable_insights',
                    'smart_title': 'smart_title',
                    'summary': 'summary',
                    'summary_preview': 'summary_preview',
                    'full_summary': 'full_summary',
                    'main_topic': 'main_topic',
                    'value_proposition': 'value_proposition',
                    'summary_key_points': 'summary_key_points',
                    'summary_tags': 'summary_tags',
                    'summary_confidence': 'summary_confidence',
                    'use_cases': 'use_cases'
                }
                
                for key, value in kwargs.items():
                    if key in field_mappings and value is not None:
                        db_field = field_mappings[key]
                        update_fields.append(f"{db_field} = ?")
                        update_values.append(value)
                
                if update_fields:
                    update_values.append(post_id)
                    query = f"UPDATE posts SET {', '.join(update_fields)} WHERE post_id = ?"
                    cursor.execute(query, update_values)
                    conn.commit()
                    print(f"✅ Updated post {post_id} with {len(update_fields)} fields")
                    return True
                
                return False
                
        except Exception as e:
            print(f"Error updating smart fields: {e}")
            return False
    
    def add_to_curation(self, post_id: str, use_case: str, notes: str = "", priority: int = 1, user_id: str = 'default'):
        """Add a post to the curation queue"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO content_curation (post_id, use_case, notes, priority, user_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (post_id, use_case, notes, priority, user_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error adding to curation: {e}")
            return False
    
    def get_curation_queue(self, use_case: str = None, status: str = 'pending', user_id: str = 'default'):
        """Get curation queue with optional filtering"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = """
                    SELECT c.*, p.author, p.content, p.value_score, p.smart_tags, p.smart_title
                    FROM content_curation c
                    JOIN posts p ON c.post_id = p.post_id
                    WHERE c.user_id = ?
                """
                params = [user_id]
                
                if use_case:
                    query += " AND c.use_case = ?"
                    params.append(use_case)
                
                if status:
                    query += " AND c.status = ?"
                    params.append(status)
                
                query += " ORDER BY c.priority DESC, c.created_at DESC"
                
                df = pd.read_sql_query(query, conn, params=params)
                return df
                
        except Exception as e:
            print(f"Error getting curation queue: {e}")
            return pd.DataFrame()
    
    def update_curation_status(self, curation_id: int, status: str, notes: str = None):
        """Update curation status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if notes:
                    cursor.execute("""
                        UPDATE content_curation 
                        SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, notes, curation_id))
                else:
                    cursor.execute("""
                        UPDATE content_curation 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (status, curation_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating curation status: {e}")
            return False

# Initialize database manager
@st.cache_resource
def get_db_manager():
    return DatabaseManager()

# Streamlit session state for user interactions
if 'user_interactions' not in st.session_state:
    st.session_state.user_interactions = {}