"""
PrisMind Learning System - User Feedback and Pattern Analysis
"""
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


class FeedbackSystem:
    """(Legacy) Local feedback system. Disabled by default via ENABLE_LOCAL_FEEDBACK flag."""
    
    def __init__(self, db_path="data/prismind.db"):
        self.db_path = Path(db_path)
        self.init_feedback_tables()
    
    def init_feedback_tables(self):
        """Initialize feedback and learning tables"""
        with sqlite3.connect(self.db_path) as conn:
            # User feedback table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT,
                    feedback_type TEXT, -- 'gold', 'good', 'poor', 'irrelevant'
                    rating INTEGER, -- 1-5 scale
                    user_notes TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (post_id) REFERENCES posts (post_id)
                )
            """)
            
            # Lightweight user events table (used by tests for interactions)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id TEXT,
                    event_type TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Learning patterns table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT, -- 'author_preference', 'topic_preference', 'content_type_preference'
                    pattern_key TEXT, -- author_name, topic, content_type
                    preference_score REAL, -- -1 to 1 scale
                    confidence_level REAL, -- 0 to 1
                    sample_size INTEGER,
                    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Add feedback columns to posts table if not exists
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(posts)")
            existing_columns = [column[1] for column in cursor.fetchall()]
            
            feedback_columns = [
                ('user_rating', 'INTEGER'), # 1-5 rating
                ('is_gold', 'INTEGER DEFAULT 0'), # Gold status
                ('user_feedback', 'TEXT'), # User notes
                ('feedback_timestamp', 'DATETIME')
            ]
            
            for column_name, column_type in feedback_columns:
                if column_name not in existing_columns:
                    try:
                        cursor.execute(f"ALTER TABLE posts ADD COLUMN {column_name} {column_type}")
                        print(f"✅ Added feedback column: {column_name}")
                    except sqlite3.OperationalError as e:
                        if "duplicate column name" not in str(e):
                            print(f"⚠️ Could not add column {column_name}: {e}")
            
            conn.commit()
    
    def record_feedback(self, post_id: str, feedback_type: str, rating: Optional[int] = None, notes: str = ""):
        """Record user feedback for a post (always records locally for tests)."""
        with sqlite3.connect(self.db_path) as conn:
            # Add to feedback table
            conn.execute("""
                INSERT INTO user_feedback (post_id, feedback_type, rating, user_notes)
                VALUES (?, ?, ?, ?)
            """, (post_id, feedback_type, rating, notes))
            
            # Update posts table
            is_gold = 1 if feedback_type == 'gold' else 0
            try:
                conn.execute(
                    """
                    UPDATE posts 
                    SET user_rating = ?, is_gold = ?, user_feedback = ?, feedback_timestamp = CURRENT_TIMESTAMP
                    WHERE post_id = ?
                    """,
                    (rating, is_gold, notes, post_id),
                )
            except sqlite3.OperationalError:
                # Posts table may not exist in minimal test DBs; ignore
                pass
            
            conn.commit()
        
        # Update learning patterns
        self._update_learning_patterns_for_post(post_id, feedback_type, rating)

    def add_feedback(self, post_id: str, feedback_type: str, rating: Optional[int] = None, user_notes: str = ""):
        """Compatibility alias for tests – returns True even when disabled."""
        self.record_feedback(post_id, feedback_type, rating, user_notes)
        return True
    
    def get_feedback_for_post(self, post_id: str) -> List[Dict[str, Any]]:
        """Return feedback rows for a given post as list of dicts."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT post_id, feedback_type, rating, user_notes, timestamp FROM user_feedback WHERE post_id = ? ORDER BY timestamp ASC",
                (post_id,),
            ).fetchall()
            return [{k: row[k] for k in row.keys()} for row in rows]

    def get_feedback_stats(self) -> Dict[str, Any]:
        """Return basic feedback statistics expected by tests."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            total = conn.execute("SELECT COUNT(*) AS c FROM user_feedback").fetchone()[0]
            by_type_rows = conn.execute(
                "SELECT feedback_type, COUNT(*) AS c FROM user_feedback GROUP BY feedback_type"
            ).fetchall()
            feedback_by_type = {row[0]: row[1] for row in by_type_rows}
        return {
            'total_feedback': total,
            'feedback_by_type': feedback_by_type,
        }

    def update_learning_patterns(self) -> bool:
        """Update learning patterns (no-op when disabled)."""
        import os
        if os.getenv('ENABLE_LOCAL_FEEDBACK', '0') != '1':
            return True
        with sqlite3.connect(self.db_path) as conn:
            # Aggregate simple preferences by feedback type as a baseline signal
            rows = conn.execute(
                "SELECT feedback_type, COUNT(*) AS c FROM user_feedback GROUP BY feedback_type"
            ).fetchall()
            for feedback_type, count in rows:
                # Map feedback_type to a score similar to _calculate_preference_score
                score_map = {'gold': 1.0, 'good': 0.6, 'poor': -0.4, 'irrelevant': -0.8}
                score = score_map.get(feedback_type, 0.0)
                conn.execute(
                    """
                    INSERT INTO learning_patterns (pattern_type, pattern_key, preference_score, confidence_level, sample_size)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    ('overall_feedback', feedback_type, score, min(0.95, count * 0.1), count),
                )
            conn.commit()
        return True

    def _update_learning_patterns_for_post(self, post_id: str, feedback_type: str, rating: Optional[int]):
        """Internal helper to update patterns for a single feedback event using available post metadata when present."""
        with sqlite3.connect(self.db_path) as conn:
            try:
                # Try to derive metadata from posts table if it exists; otherwise skip fine-grained patterns
                post_data = pd.read_sql_query(
                    "SELECT author, category, content_type, smart_tags, topic FROM posts WHERE post_id = ?",
                    conn,
                    params=(post_id,),
                )
            except Exception:
                post_data = pd.DataFrame()
            if not post_data.empty:
                post = post_data.iloc[0]
                preference_score = self._calculate_preference_score(feedback_type, rating)
                if post.get('author'):
                    self._update_pattern(conn, 'author_preference', post['author'], preference_score)
                if post.get('topic'):
                    self._update_pattern(conn, 'topic_preference', post['topic'], preference_score)
                if post.get('content_type'):
                    self._update_pattern(conn, 'content_type_preference', post['content_type'], preference_score)
                if post.get('smart_tags'):
                    try:
                        tags = json.loads(post['smart_tags']) if isinstance(post['smart_tags'], str) else post['smart_tags']
                        for tag in tags:
                            self._update_pattern(conn, 'tag_preference', tag, preference_score)
                    except Exception:
                        pass

    def get_content_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Return a simple list of recommended content; empty list if posts table unavailable."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(
                    "SELECT post_id, author, content, value_score FROM posts WHERE is_deleted = 0 ORDER BY value_score DESC LIMIT ?",
                    conn,
                    params=(limit,),
                )
                return df.to_dict('records')
        except Exception:
            return []

    def record_interaction(self, post_id: str, interaction_type: str) -> bool:
        """Record a simple user interaction event."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO user_events (post_id, event_type) VALUES (?, ?)",
                (post_id, interaction_type),
            )
            conn.commit()
        return True

    # Backwards-compatible single-post updater (new name)
    def update_learning_patterns_for_post(self, post_id: str, feedback_type: str, rating: Optional[int]) -> bool:
        self._update_learning_patterns_for_post(post_id, feedback_type, rating)
        return True
    
    def _calculate_preference_score(self, feedback_type: str, rating: Optional[int]) -> float:
        """Convert feedback to preference score (-1 to 1)"""
        if feedback_type == 'gold':
            return 1.0
        elif feedback_type == 'good':
            return 0.6
        elif feedback_type == 'poor':
            return -0.4
        elif feedback_type == 'irrelevant':
            return -0.8
        elif rating:
            # Convert 1-5 rating to -1 to 1 scale
            return (rating - 3) / 2
        else:
            return 0.0
    
    def _update_pattern(self, conn, pattern_type: str, pattern_key: str, new_score: float):
        """Update learning pattern with exponential moving average"""
        # Get existing pattern
        existing = conn.execute("""
            SELECT preference_score, sample_size FROM learning_patterns
            WHERE pattern_type = ? AND pattern_key = ?
        """, (pattern_type, pattern_key)).fetchone()
        
        if existing:
            old_score, sample_size = existing
            # Exponential moving average with higher weight for recent feedback
            alpha = 0.3  # Learning rate
            new_preference_score = alpha * new_score + (1 - alpha) * old_score
            new_sample_size = sample_size + 1
            confidence = min(0.95, sample_size * 0.1)  # Higher confidence with more samples
            
            conn.execute("""
                UPDATE learning_patterns 
                SET preference_score = ?, confidence_level = ?, sample_size = ?, last_updated = CURRENT_TIMESTAMP
                WHERE pattern_type = ? AND pattern_key = ?
            """, (new_preference_score, confidence, new_sample_size, pattern_type, pattern_key))
        else:
            # New pattern
            conn.execute("""
                INSERT INTO learning_patterns (pattern_type, pattern_key, preference_score, confidence_level, sample_size)
                VALUES (?, ?, ?, ?, ?)
            """, (pattern_type, pattern_key, new_score, 0.1, 1))
        
        conn.commit()
    
    def get_user_preferences(self) -> Dict[str, Dict[str, float]]:
        """Get learned user preferences"""
        with sqlite3.connect(self.db_path) as conn:
            patterns_df = pd.read_sql_query("""
                SELECT pattern_type, pattern_key, preference_score, confidence_level, sample_size
                FROM learning_patterns
                WHERE confidence_level > 0.2
                ORDER BY preference_score DESC
            """, conn)
        
        preferences = defaultdict(dict)
        for _, row in patterns_df.iterrows():
            preferences[row['pattern_type']][row['pattern_key']] = {
                'score': row['preference_score'],
                'confidence': row['confidence_level'],
                'sample_size': row['sample_size']
            }
        
        return dict(preferences)
    
    def get_recommended_score_adjustment(self, post_data: Dict) -> float:
        """Calculate score adjustment based on learned preferences"""
        preferences = self.get_user_preferences()
        adjustment = 0.0
        
        # Author preference
        author = post_data.get('author')
        if author in preferences.get('author_preference', {}):
            pref = preferences['author_preference'][author]
            adjustment += pref['score'] * pref['confidence'] * 0.4
        
        # Topic preference
        topic = post_data.get('topic')
        if topic in preferences.get('topic_preference', {}):
            pref = preferences['topic_preference'][topic]
            adjustment += pref['score'] * pref['confidence'] * 0.3
        
        # Content type preference
        content_type = post_data.get('content_type')
        if content_type in preferences.get('content_type_preference', {}):
            pref = preferences['content_type_preference'][content_type]
            adjustment += pref['score'] * pref['confidence'] * 0.2
        
        # Tag preferences
        try:
            tags = json.loads(post_data.get('smart_tags', '[]'))
            tag_adjustments = []
            for tag in tags:
                if tag in preferences.get('tag_preference', {}):
                    pref = preferences['tag_preference'][tag]
                    tag_adjustments.append(pref['score'] * pref['confidence'])
            
            if tag_adjustments:
                adjustment += np.mean(tag_adjustments) * 0.1
        except:
            pass
        
        # Clamp adjustment to reasonable range
        return max(-2.0, min(2.0, adjustment))
    
    def get_gold_posts(self) -> pd.DataFrame:
        """Get all posts marked as gold"""
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query("""
                SELECT * FROM posts 
                WHERE is_gold = 1 AND is_deleted = 0
                ORDER BY feedback_timestamp DESC
            """, conn)
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """Get feedback statistics (robust to missing posts table)."""
        with sqlite3.connect(self.db_path) as conn:
            stats: Dict[str, Any] = {}

            # Overall feedback counts
            feedback_counts = pd.read_sql_query(
                """
                SELECT feedback_type, COUNT(*) as count
                FROM user_feedback
                GROUP BY feedback_type
                """,
                conn,
            )
            stats['feedback_counts'] = dict(
                zip(feedback_counts['feedback_type'], feedback_counts['count'])
            )
            # Also expose feedback_by_type to match tests
            stats['feedback_by_type'] = dict(stats['feedback_counts'])
            stats['total_feedback'] = int(feedback_counts['count'].sum()) if not feedback_counts.empty else 0

            # Gold posts count (optional)
            try:
                gold_count = conn.execute(
                    "SELECT COUNT(*) FROM posts WHERE is_gold = 1 AND is_deleted = 0"
                ).fetchone()[0]
                stats['gold_posts'] = int(gold_count)
            except sqlite3.OperationalError:
                stats['gold_posts'] = 0

            # Top preferred authors/topics (optional)
            def safe_query(sql: str):
                try:
                    return pd.read_sql_query(sql, conn)
                except Exception:
                    return pd.DataFrame()

            top_authors = safe_query(
                """
                SELECT pattern_key as author, preference_score, sample_size
                FROM learning_patterns
                WHERE pattern_type = 'author_preference' AND confidence_level > 0.3
                ORDER BY preference_score DESC
                LIMIT 10
                """
            )
            stats['top_authors'] = top_authors.to_dict('records') if not top_authors.empty else []

            top_topics = safe_query(
                """
                SELECT pattern_key as topic, preference_score, sample_size
                FROM learning_patterns
                WHERE pattern_type = 'topic_preference' AND confidence_level > 0.3
                ORDER BY preference_score DESC
                LIMIT 10
                """
            )
            stats['top_topics'] = top_topics.to_dict('records') if not top_topics.empty else []

            return stats
    
    def create_smart_collections(self) -> Dict[str, List[Dict]]:
        """Create smart collections based on learned patterns"""
        with sqlite3.connect(self.db_path) as conn:
            collections = {}
            
            # Gold Collection
            gold_posts = pd.read_sql_query("""
                SELECT post_id, author, smart_title, content_type, value_score
                FROM posts WHERE is_gold = 1 AND is_deleted = 0
                ORDER BY feedback_timestamp DESC
            """, conn)
            collections['🥇 Gold Collection'] = gold_posts.to_dict('records')
            
            # Top Tools Collection
            tools_posts = pd.read_sql_query("""
                SELECT post_id, author, smart_title, content_type, value_score
                FROM posts 
                WHERE content_type LIKE '%Tool%' AND is_deleted = 0 AND value_score > 6
                ORDER BY value_score DESC
                LIMIT 20
            """, conn)
            collections['🛠️ Top Tools'] = tools_posts.to_dict('records')
            
            # Learning Resources Collection
            learning_posts = pd.read_sql_query("""
                SELECT post_id, author, smart_title, content_type, value_score
                FROM posts 
                WHERE (content_type LIKE '%Tutorial%' OR content_type LIKE '%Guide%') 
                AND is_deleted = 0 AND value_score > 6
                ORDER BY value_score DESC
                LIMIT 20
            """, conn)
            collections['📚 Learning Resources'] = learning_posts.to_dict('records')
            
            # Favorite Authors Collection
            preferences = self.get_user_preferences()
            if 'author_preference' in preferences:
                top_author = max(preferences['author_preference'].items(), key=lambda x: x[1]['score'])
                if top_author[1]['score'] > 0.5:
                    author_posts = pd.read_sql_query("""
                        SELECT post_id, author, smart_title, content_type, value_score
                        FROM posts 
                        WHERE author = ? AND is_deleted = 0
                        ORDER BY value_score DESC
                        LIMIT 15
                    """, conn, params=(top_author[0],))
                    collections[f'👤 {top_author[0]} Collection'] = author_posts.to_dict('records')
            
            return collections