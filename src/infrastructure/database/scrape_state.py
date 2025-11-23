#!/usr/bin/env python3
"""
Scrape State Database Operations
Handles database operations for tracking scraping progress
"""

import sqlite3
from typing import Any, Dict, Optional


class ScrapeStateDatabase:
    """Handles database operations for scrape state management"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the state database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scrape_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                last_post_id TEXT,
                last_post_url TEXT,
                posts_scraped INTEGER DEFAULT 0,
                last_scrape_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1,
                after_parameter TEXT,
                UNIQUE(platform)
            )
        ''')
        
        # Create scraped posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                url TEXT,
                title TEXT,
                author TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, platform)
            )
        ''')
        
        # Create indexes for better performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_platform ON scrape_state(platform)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_post_id ON scraped_posts(post_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_platform_posts ON scraped_posts(platform)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_at ON scraped_posts(scraped_at)')
        
        conn.commit()
        # Ensure schema migrations for existing databases
        self._ensure_schema(conn)
        conn.close()

    def _ensure_schema(self, conn: sqlite3.Connection):
        """Ensure required columns exist (handles existing DBs)."""
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(scrape_state)")
        existing_cols = {row[1] for row in cursor.fetchall()}

        # Add missing posts_scraped column if not present
        if 'posts_scraped' not in existing_cols:
            cursor.execute("ALTER TABLE scrape_state ADD COLUMN posts_scraped INTEGER DEFAULT 0")
        # Add missing last_scrape_time column
        if 'last_scrape_time' not in existing_cols:
            cursor.execute("ALTER TABLE scrape_state ADD COLUMN last_scrape_time TIMESTAMP")
            cursor.execute("UPDATE scrape_state SET last_scrape_time = CURRENT_TIMESTAMP WHERE last_scrape_time IS NULL")
        # Add missing success column
        if 'success' not in existing_cols:
            cursor.execute("ALTER TABLE scrape_state ADD COLUMN success BOOLEAN DEFAULT 1")
        # Add missing after_parameter column
        if 'after_parameter' not in existing_cols:
            cursor.execute("ALTER TABLE scrape_state ADD COLUMN after_parameter TEXT")
        conn.commit()
    
    def get_last_scrape_info(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get last scrape information for a platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT last_post_id, last_post_url, posts_scraped, last_scrape_time, success, after_parameter
            FROM scrape_state 
            WHERE platform = ?
        ''', (platform,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'last_post_id': result[0],
                'last_post_url': result[1],
                'posts_scraped': result[2],
                'last_scrape_time': result[3],
                'success': bool(result[4]),
                'after_parameter': result[5]
            }
        return None
    
    def update_scrape_state(self, platform: str, last_post_id: str = None, 
                          last_post_url: str = None, posts_scraped: int = 0, 
                          success: bool = True, after_parameter: str = None):
        """Update scrape state for a platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO scrape_state 
            (platform, last_post_id, last_post_url, posts_scraped, last_scrape_time, success, after_parameter)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
        ''', (platform, last_post_id, last_post_url, posts_scraped, success, after_parameter))
        
        conn.commit()
        conn.close()
    
    def is_post_scraped(self, post_id: str, platform: str) -> bool:
        """Check if a post has been scraped"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM scraped_posts 
            WHERE post_id = ? AND platform = ?
        ''', (post_id, platform))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    def mark_post_scraped(self, post_id: str, platform: str, url: str = None, 
                         title: str = None, author: str = None):
        """Mark a post as scraped"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO scraped_posts 
            (post_id, platform, url, title, author, scraped_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (post_id, platform, url, title, author))
        
        conn.commit()
        conn.close()
    
    def get_scraped_posts_count(self, platform: str) -> int:
        """Get count of scraped posts for a platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM scraped_posts 
            WHERE platform = ?
        ''', (platform,))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    
    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get overall scraping statistics"""
        conn = sqlite3.connect(self.db_path)
        # Ensure schema is up to date before running queries
        self._ensure_schema(conn)
        cursor = conn.cursor()
        
        # Aggregate scraped post counts by platform
        cursor.execute('''
            SELECT platform, COUNT(*)
            FROM scraped_posts
            GROUP BY platform
        ''')
        scraped_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Get platform metadata
        cursor.execute('''
            SELECT platform, posts_scraped, last_scrape_time, success
            FROM scrape_state
        ''')

        platform_stats = []
        seen_platforms = set()
        for row in cursor.fetchall():
            platform = row[0]
            platform_stats.append({
                'platform': platform,
                'total_posts_scraped': scraped_counts.get(platform, row[1] or 0),
                'last_scraped_at': row[2],
                'last_scrape_success': bool(row[3])
            })
            seen_platforms.add(platform)

        # Include platforms that have scraped posts but no state metadata yet
        for platform, count in scraped_counts.items():
            if platform in seen_platforms:
                continue
            platform_stats.append({
                'platform': platform,
                'total_posts_scraped': count,
                'last_scraped_at': None,
                'last_scrape_success': True
            })
        
        # Get total scraped posts
        cursor.execute('SELECT COUNT(*) FROM scraped_posts')
        total_scraped = cursor.fetchone()[0]
        
        # Get recent activity
        cursor.execute('''
            SELECT COUNT(*) FROM scraped_posts 
            WHERE scraped_at > datetime('now', '-24 hours')
        ''')
        recent_activity = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_posts': total_scraped,
            'platform_stats': platform_stats,
            'recent_activity_24h': recent_activity
        }
    
    def reset_platform_state(self, platform: str):
        """Reset state for a specific platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete platform state
        cursor.execute('DELETE FROM scrape_state WHERE platform = ?', (platform,))
        
        # Delete scraped posts for platform
        cursor.execute('DELETE FROM scraped_posts WHERE platform = ?', (platform,))
        
        conn.commit()
        conn.close()
    
    def update_last_scrape_info(self, platform: str, scrape_info: Dict[str, Any]):
        """Update last scrape information"""
        self.update_scrape_state(
            platform=platform,
            last_post_id=scrape_info.get('last_post_id'),
            last_post_url=scrape_info.get('last_post_url'),
            posts_scraped=scrape_info.get('posts_scraped', 0),
            success=scrape_info.get('success', True),
            after_parameter=scrape_info.get('after_parameter')
        )
    
    def get_after_parameter(self, platform: str) -> Optional[str]:
        """Get the after parameter for a platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT after_parameter FROM scrape_state 
            WHERE platform = ?
        ''', (platform,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def cleanup_old_records(self, days: int = 30):
        """Clean up old records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Delete old scraped posts
        cursor.execute('''
            DELETE FROM scraped_posts 
            WHERE scraped_at < datetime('now', '-{} days')
        '''.format(days))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count
