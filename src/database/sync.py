#!/usr/bin/env python3
"""
Database Sync Module

Handles synchronization between SQLite and Supabase, including retry logic and status reporting.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class DatabaseSync:
    """Handles database synchronization operations"""

    def __init__(self, supabase=None, sqlite=None, post_inserter=None, normalize_post_data_fn=None):
        self._supabase = supabase
        self._sqlite = sqlite
        self._post_inserter = post_inserter
        self._normalize_post_data = normalize_post_data_fn

    def retry_failed_syncs(self, limit: int = 100) -> Dict[str, Any]:
        """
        Retry syncing unsynced posts from SQLite to Supabase.
        Returns statistics about the retry operation.
        """
        results = {
            'attempted': 0,
            'succeeded': 0,
            'failed': 0,
            'errors': []
        }
        
        if not self._sqlite:
            logger.warning("Cannot retry syncs: SQLite not configured")
            return results
        
        if not self._supabase:
            logger.warning("Cannot retry syncs: Supabase not configured")
            return results
        
        try:
            # Get unsynced posts from SQLite
            unsynced_posts = self._sqlite.get_unsynced_posts(limit=limit)
            results['attempted'] = len(unsynced_posts)
            
            logger.info(f"Retrying sync for {len(unsynced_posts)} posts")
            
            for post in unsynced_posts:
                post_id = post.get('post_id')
                if not post_id:
                    continue
                
                try:
                    # Normalize the post data
                    normalized_post = post
                    if self._normalize_post_data:
                        normalized_post = self._normalize_post_data(post)
                    
                    # Try to sync to Supabase
                    if self._post_inserter:
                        result = self._post_inserter.insert_post(normalized_post)
                        if result:
                            # Mark as synced
                            self._sqlite.mark_synced_to_supabase(post_id, synced=True)
                            results['succeeded'] += 1
                            logger.debug(f"✅ Retry sync succeeded for post {post_id}")
                        else:
                            # Mark as failed (error will be updated on next failure)
                            results['failed'] += 1
                            logger.debug(f"⚠️ Retry sync failed for post {post_id}")
                    else:
                        results['failed'] += 1
                        self._sqlite.mark_synced_to_supabase(post_id, synced=False, error="Post inserter not available")
                        
                except Exception as e:
                    error_msg = str(e)
                    results['failed'] += 1
                    results['errors'].append(f"Post {post_id}: {error_msg}")
                    self._sqlite.mark_synced_to_supabase(post_id, synced=False, error=error_msg)
                    logger.warning(f"Retry sync error for post {post_id}: {e}")
            
            logger.info(f"Retry sync completed: {results['succeeded']} succeeded, {results['failed']} failed")
            
        except Exception as e:
            logger.error(f"Retry sync operation failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
        
        return results
    
    def get_sync_status_report(self) -> Dict[str, Any]:
        """Get detailed sync status report for visibility"""
        if not self._sqlite:
            return {
                'error': 'SQLite not configured',
                'total': 0,
                'synced': 0,
                'unsynced': 0,
                'failed': 0,
                'sync_percentage': 0.0
            }
        
        try:
            status = self._sqlite.get_sync_status()
            
            # Get sample of unsynced posts
            unsynced_samples = self._sqlite.get_unsynced_posts(limit=10)
            unsynced_samples_info = [
                {
                    'post_id': p.get('post_id'),
                    'platform': p.get('platform'),
                    'created_at': p.get('created_at'),
                    'sync_error': p.get('sync_error')
                }
                for p in unsynced_samples
            ]
            
            return {
                **status,
                'unsynced_samples': unsynced_samples_info,
                'generated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting sync status report: {e}")
            return {
                'error': str(e),
                'total': 0,
                'synced': 0,
                'unsynced': 0,
                'failed': 0,
                'sync_percentage': 0.0
            }

