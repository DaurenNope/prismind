#!/usr/bin/env python3
"""
Scrape State Manager
Tracks scraping progress and save points to avoid rescraping the same content
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from src.database.scrape_state import ScrapeStateDatabase

# Load environment variables
load_dotenv()


class ScrapeStateManager:
    """Manages scraping state and progress tracking"""

    def __init__(self, db_path: str = None, main_db_path: str = None):
        if db_path is None:
            var_dir = Path("var")
            var_dir.mkdir(exist_ok=True)
            db_path = str(var_dir / "scrape_state.db")

        self.db = ScrapeStateDatabase(db_path)
        self.main_db_path = main_db_path or "prismind.db"
        self.logger = self._setup_logger()

    def _setup_logger(self):
        """Setup logger for state manager"""
        import logging

        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def get_last_scrape_info(self, platform: str) -> Optional[Dict[str, Any]]:
        """Get last scrape information for a platform"""
        return self.db.get_last_scrape_info(platform)

    def update_scrape_state(
        self,
        platform: str,
        last_post_id: str = None,
        last_post_url: str = None,
        posts_scraped: int = 0,
        success: bool = True,
        after_parameter: str = None,
    ):
        """Update scrape state for a platform with improved error handling"""
        try:
            # Normalize post ID before updating state
            normalized_id = self.normalize_post_id(last_post_id, platform) if last_post_id else None
            
            self.db.update_scrape_state(
                platform,
                normalized_id,
                last_post_url,
                posts_scraped,
                success,
                after_parameter,
            )
            
            status = "✅ SUCCESS" if success else "❌ FAILED"
            self.logger.info(f"{status} Updated {platform} state: {posts_scraped} posts, last_id: {normalized_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to update scrape state for {platform}: {e}")
            # Don't raise exception - collection should continue even if state tracking fails

    def is_post_scraped(self, post_id: str, platform: str) -> bool:
        """Check if a post has been scraped"""
        return self.db.is_post_scraped(post_id, platform)

    def is_post_already_scraped(self, post_id: str, platform: str) -> bool:
        """Alias for is_post_scraped for backward compatibility"""
        return self.is_post_scraped(post_id, platform)

    def mark_post_scraped(
        self,
        post_id: str,
        platform: str,
        url: str = None,
        title: str = None,
        author: str = None,
    ):
        """Mark a post as scraped with improved error handling"""
        try:
            # Normalize post ID before marking
            normalized_id = self.normalize_post_id(post_id, platform)
            self.db.mark_post_scraped(normalized_id, platform, url, title, author)
            self.logger.debug(f"✅ Marked post {normalized_id} as scraped for {platform}")
        except Exception as e:
            self.logger.error(f"❌ Failed to mark post {post_id} as scraped: {e}")
            # Don't raise exception - collection should continue even if state tracking fails

    def get_scraped_posts_count(self, platform: str) -> int:
        """Get count of scraped posts for a platform"""
        return self.db.get_scraped_posts_count(platform)

    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get overall scraping statistics"""
        return self.db.get_scraping_stats()

    def reset_platform_state(self, platform: str):
        """Reset state for a specific platform"""
        self.db.reset_platform_state(platform)

    def update_last_scrape_info(self, platform: str, scrape_info: Dict[str, Any]):
        """Update last scrape information"""
        self.db.update_last_scrape_info(platform, scrape_info)

    def get_after_parameter(self, platform: str) -> Optional[str]:
        """Get the after parameter for a platform"""
        return self.db.get_after_parameter(platform)

    def cleanup_old_records(self, days: int = 30) -> int:
        """Clean up old records"""
        return self.db.cleanup_old_records(days)

    def get_last_collected_post_id(self, platform: str) -> Optional[str]:
        """Get the last collected post ID for a platform"""
        info = self.get_last_scrape_info(platform)
        if info and info.get("last_post_id"):
            return self.normalize_post_id(info["last_post_id"], platform)
        return None

    def normalize_post_id(self, post_id: str, platform: str) -> str:
        """Normalize post ID for consistent comparison across databases"""
        if not post_id:
            return ""

        post_id = str(post_id).strip()

        # Remove platform prefix if present (e.g., "twitter_123" -> "123")
        if post_id.startswith(f"{platform}_"):
            post_id = post_id[len(platform) + 1 :]

        # Handle Reddit fullnames (e.g., "t3_xyz" -> "xyz")
        if platform == "reddit" and post_id.startswith("t3_"):
            post_id = post_id[3:]

        return post_id

    def sync_state_from_main_db(self, force: bool = False):
        """Sync state database from main posts database with improved error handling"""
        import sqlite3
        
        try:
            # Check if we need to sync (silent check)
            if not force:
                stats = self.get_scraping_stats()
                if stats.get("total_posts", 0) > 0:
                    self.logger.debug("🔄 State already synced, skipping (use force=True to override)")
                    return  # Already synced, skip silently
            
            self.logger.info("🔄 Syncing state from main database...")
            
            # Check if main database exists
            if not Path(self.main_db_path).exists():
                self.logger.warning(f"⚠️ Main database not found at {self.main_db_path}")
                return
            
            # Connect to main database
            main_conn = sqlite3.connect(self.main_db_path)
            main_cursor = main_conn.cursor()
            
            # Get all posts from main database
            main_cursor.execute("""
                SELECT post_id, platform, url, title, author, created_at
                FROM posts
                WHERE post_id IS NOT NULL AND post_id != ''
                ORDER BY created_at ASC
            """)
            
            posts = main_cursor.fetchall()
            main_conn.close()
            
            if not posts:
                self.logger.info("📭 No posts found in main database to sync")
                return
            
            # Track posts by platform for state updates
            platform_posts = {}
            
            # Mark each post as scraped
            synced_count = 0
            failed_count = 0
            for post_id, platform, url, title, author, created_at in posts:
                try:
                    # Normalize the post ID
                    normalized_id = self.normalize_post_id(post_id, platform)
                    
                    # Mark post as scraped
                    self.mark_post_scraped(
                        post_id=normalized_id,
                        platform=platform,
                        url=url,
                        title=title,
                        author=author,
                    )
                    
                    # Track for platform state update
                    if platform not in platform_posts:
                        platform_posts[platform] = []
                    platform_posts[platform].append((normalized_id, url, created_at))
                    
                    synced_count += 1
                except Exception as e:
                    failed_count += 1
                    self.logger.debug(f"⚠️ Failed to sync post {post_id}: {e}")
                    continue  # Skip failed posts silently
            
            # Update platform states with the most recent post from each
            for platform, posts_list in platform_posts.items():
                # Sort by created_at descending to get the most recent
                posts_list.sort(key=lambda x: x[2] if x[2] else "", reverse=True)
                last_post_id, last_post_url, _ = posts_list[0]
                
                self.update_scrape_state(
                    platform=platform,
                    last_post_id=last_post_id,
                    last_post_url=last_post_url,
                    posts_scraped=len(posts_list),
                    success=True,
                )
            
            self.logger.info(f"✅ State sync completed: {synced_count} synced, {failed_count} failed")
            
        except Exception as e:
            self.logger.error(f"❌ State sync failed: {e}")
            # Sync failure is not critical - collection will continue

    def validate_state(self, platform: str) -> Dict[str, Any]:
        """Validate state for a platform and return status"""
        info = self.get_last_scrape_info(platform)
        scraped_count = self.get_scraped_posts_count(platform)

        validation = {
            "platform": platform,
            "has_state": info is not None,
            "last_post_id": info.get("last_post_id") if info else None,
            "last_post_url": info.get("last_post_url") if info else None,
            "posts_scraped_count": scraped_count,
            "last_scrape_time": info.get("last_scrape_time") if info else None,
            "last_success": info.get("success") if info else None,
        }

        # Check for issues
        issues = []
        if not info:
            issues.append("No state record found")
        elif not info.get("last_post_id"):
            issues.append("No last_post_id set")

        if scraped_count == 0:
            issues.append("No posts marked as scraped")

        validation["issues"] = issues
        validation["is_valid"] = len(issues) == 0

        return validation


# Global instance
state_manager = ScrapeStateManager()
