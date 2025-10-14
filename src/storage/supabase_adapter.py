#!/usr/bin/env python3
"""
Supabase adapter for primary storage operations.
"""

import os
import asyncio
from typing import Any, Dict, List

from src.supabase_manager import SupabaseManager
from src.services.supabase.post_inserter import PostInserter


class SupabaseAdapter:
    def __init__(self) -> None:
        self.client = SupabaseManager().client
        # Create a simple duplicate checker wrapper
        from src.utils.duplicate_detector import DuplicateDetector
        
        class DuplicateCheckerWrapper:
            def __init__(self, detector):
                self.detector = detector
            
            def check_duplicate_post(self, content, author, platform, url=None):
                # Convert to the format expected by DuplicateDetector
                item = {
                    'content': content,
                    'author': author,
                    'platform': platform,
                    'url': url
                }
                return self.detector.is_duplicate(item)
        
        duplicate_checker = DuplicateCheckerWrapper(DuplicateDetector(db_manager=None, supabase_manager=None))
        self.post_inserter = PostInserter(self.client, duplicate_checker)
        
        # Initialize auto-analyzer if enabled
        self.auto_analyze = os.getenv('AUTO_ANALYZE_POSTS', 'true').lower() in ('true', '1', 'yes')
        self._analyzer = None

    def save_post(self, post: Dict[str, Any]) -> bool:
        try:
            # Auto-analyze post if enabled and not already analyzed
            if self.auto_analyze and not post.get('analyzed_at'):
                post = self._run_analysis(post)
            
            # Use PostInserter to properly map data to Supabase schema
            result = self.post_inserter.insert_post(post)
            return bool(result)
        except Exception:
            return False
    
    def _run_analysis(self, post: Dict[str, Any]) -> Dict[str, Any]:
        """Run AI analysis on post (async wrapper)"""
        try:
            if self._analyzer is None:
                from src.services.auto_analyzer import AutoAnalyzer
                self._analyzer = AutoAnalyzer()
            
            # Run async analysis in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            enriched = loop.run_until_complete(self._analyzer.analyze_post(post))
            loop.close()
            
            return enriched
        except Exception as e:
            print(f"⚠️ Auto-analysis failed: {e}")
            return post

    def get_posts(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            result = self.client.table("posts").select("*").order("created_at", desc=True).limit(limit).execute()
            return getattr(result, "data", []) or []
        except Exception:
            return []

    def save_github_trending_repo(self, repo_data: Dict[str, Any]) -> bool:
        try:
            result = self.client.table("github_trending").upsert(repo_data, on_conflict="period,full_name").execute()
            return bool(getattr(result, "data", None))
        except Exception:
            return False

    def save_telegram_message(self, message_data: Dict[str, Any]) -> bool:
        try:
            result = self.client.table("telegram_messages").insert(message_data).execute()
            return bool(getattr(result, "data", None))
        except Exception:
            return False

    def get_github_trending_repos(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            result = self.client.table("github_trending").select("*").order("collected_at", desc=True).limit(limit).execute()
            return getattr(result, "data", []) or []
        except Exception:
            return []

    def get_telegram_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            result = self.client.table("telegram_messages").select("*").order("date", desc=True).limit(limit).execute()
            return getattr(result, "data", []) or []
        except Exception:
            return []


