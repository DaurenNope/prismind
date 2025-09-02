#!/usr/bin/env python3
"""
Scrape State Manager
Tracks scraping progress and save points to avoid rescraping the same content
"""

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ScrapeStateManager:
    def __init__(self, db_path=None):
        if db_path is None:
            var_dir = Path("var")
            var_dir.mkdir(exist_ok=True)
            db_path = str(var_dir / "scrape_state.db")
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the state database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create state table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scrape_state (
                platform TEXT PRIMARY KEY,
                last_scraped_at TIMESTAMP,
                last_post_id TEXT,
                last_post_url TEXT,
                total_posts_scraped INTEGER DEFAULT 0,
                last_scrape_success BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create post tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_posts (
                post_id TEXT PRIMARY KEY,
                platform TEXT,
                url TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT,
                author TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_last_scrape_info(self, platform):
        """Get last scrape information for a platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT last_scraped_at, last_post_id, last_post_url, total_posts_scraped, last_scrape_success
            FROM scrape_state 
            WHERE platform = ?
        ''', (platform,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'last_scraped_at': result[0],
                'last_post_id': result[1],
                'last_post_url': result[2],
                'total_posts_scraped': result[3],
                'last_scrape_success': bool(result[4])
            }
        return None
    
    def update_scrape_state(self, platform, last_post_id=None, last_post_url=None, posts_scraped=0, success=True):
        """Update scrape state for a platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO scrape_state 
            (platform, last_scraped_at, last_post_id, last_post_url, total_posts_scraped, last_scrape_success, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (platform, now, last_post_id, last_post_url, posts_scraped, success, now))
        
        conn.commit()
        conn.close()
    
    def is_post_already_scraped(self, post_id, platform):
        """Check if a post has already been scraped"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 1 FROM scraped_posts 
            WHERE post_id = ? AND platform = ?
        ''', (post_id, platform))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None
    
    def mark_post_scraped(self, post_id, platform, url=None, title=None, author=None):
        """Mark a post as scraped"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO scraped_posts 
            (post_id, platform, url, title, author, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (post_id, platform, url, title, author, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_scraped_posts_count(self, platform):
        """Get count of scraped posts for a platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM scraped_posts 
            WHERE platform = ?
        ''', (platform,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else 0
    
    def get_scraping_stats(self):
        """Get overall scraping statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get platform stats
        cursor.execute('''
            SELECT platform, last_scraped_at, total_posts_scraped, last_scrape_success
            FROM scrape_state
            ORDER BY last_scraped_at DESC
        ''')
        
        platform_stats = cursor.fetchall()
        
        # Get total scraped posts
        cursor.execute('SELECT COUNT(*) FROM scraped_posts')
        total_posts = cursor.fetchone()[0]
        
        # Get posts by platform
        cursor.execute('''
            SELECT platform, COUNT(*) 
            FROM scraped_posts 
            GROUP BY platform
        ''')
        
        posts_by_platform = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'platform_stats': [
                {
                    'platform': row[0],
                    'last_scraped_at': row[1],
                    'total_posts_scraped': row[2],
                    'last_scrape_success': bool(row[3])
                }
                for row in platform_stats
            ],
            'total_posts': total_posts,
            'posts_by_platform': posts_by_platform
        }
    
    def reset_platform_state(self, platform):
        """Reset scraping state for a platform"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM scrape_state WHERE platform = ?', (platform,))
        cursor.execute('DELETE FROM scraped_posts WHERE platform = ?', (platform,))
        
        conn.commit()
        conn.close()
        
        print(f"🔄 Reset scraping state for {platform}")
    
    def cleanup_old_records(self, days=30):
        """Clean up old scraped post records"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            DELETE FROM scraped_posts 
            WHERE scraped_at < ?
        ''', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"🧹 Cleaned up {deleted_count} old scraped post records")
        return deleted_count

# Global instance
state_manager = ScrapeStateManager()

if __name__ == "__main__":
    # Test the state manager
    print("🧪 Testing Scrape State Manager")
    print("=" * 40)
    
    # Test stats
    stats = state_manager.get_scraping_stats()
    print(f"📊 Total scraped posts: {stats['total_posts']}")
    print(f"📊 Posts by platform: {stats['posts_by_platform']}")
    
    for platform_stat in stats['platform_stats']:
        print(f"📊 {platform_stat['platform']}: {platform_stat['total_posts_scraped']} posts, last scraped: {platform_stat['last_scraped_at']}")
