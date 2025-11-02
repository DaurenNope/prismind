#!/usr/bin/env python3
"""
Database Analysis Operations for PrisMind
Handles analysis and rewrite operations
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from datetime import datetime


class DatabaseAnalysis:
    """Handles database analysis and rewrite operations"""
    
    def __init__(self, db_path: str = "prismind.db"):
        self.db_path = db_path
    
    def update_post_analysis(self, post_id: str, analysis: dict) -> bool:
        """Update post with analysis results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Extract analysis data
                quality_score = analysis.get('quality_score', 0)
                value_score = analysis.get('value_score', 0)
                key_concepts = self._serialize_json(analysis.get('key_concepts', []))
                tags = self._serialize_json(analysis.get('suggested_tags', []))
                sentiment_analysis = self._serialize_json(analysis.get('sentiment_analysis', {}))
                insights = analysis.get('insights', [])
                action_items = analysis.get('action_items', [])
                
                # Create insights summary
                insights_summary = self._create_insights_summary(insights, action_items)
                
                # Update post
                cursor.execute('''
                    UPDATE posts SET 
                        quality_score = ?,
                        value_score = ?,
                        key_concepts = ?,
                        tags = ?,
                        sentiment_analysis = ?,
                        analysis_timestamp = ?,
                        ai_service_used = ?,
                        is_rewrite_candidate = ?,
                        updated_timestamp = ?
                    WHERE post_id = ?
                ''', (
                    quality_score,
                    value_score,
                    key_concepts,
                    tags,
                    sentiment_analysis,
                    datetime.now().isoformat(),
                    analysis.get('ai_service_used', 'unknown'),
                    analysis.get('is_rewrite_candidate', False),
                    datetime.now().isoformat(),
                    post_id
                ))
                
                conn.commit()
                print(f"✅ Updated analysis for post {post_id}")
                return True
                
        except Exception as e:
            print(f"❌ Error updating post analysis: {e}")
            return False
    
    def update_rewrite_status(self, post_id: str, status: str, rewritten_content: str = None, rewrite_notes: str = None) -> bool:
        """Update rewrite status for a post"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE posts SET 
                        rewrite_status = ?,
                        rewritten_content = ?,
                        rewrite_notes = ?,
                        updated_timestamp = ?
                    WHERE post_id = ?
                ''', (
                    status,
                    rewritten_content,
                    rewrite_notes,
                    datetime.now().isoformat(),
                    post_id
                ))
                
                conn.commit()
                print(f"✅ Updated rewrite status for post {post_id} to {status}")
                return True
                
        except Exception as e:
            print(f"❌ Error updating rewrite status: {e}")
            return False
    
    def get_rewrite_candidates(self, limit: int = 50) -> List[Dict]:
        """Get posts that are candidates for rewriting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM posts 
                    WHERE is_rewrite_candidate = TRUE 
                    AND rewrite_status IN ('none', 'pending')
                    ORDER BY quality_score ASC, created_at DESC
                    LIMIT ?
                """
                
                cursor.execute(query, (limit,))
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"❌ Error getting rewrite candidates: {e}")
            return []
    
    def get_high_quality_posts(self, min_quality: float = 7.0, limit: int = 50) -> List[Dict]:
        """Get high quality posts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM posts 
                    WHERE quality_score >= ? 
                    AND rewrite_status != 'deleted'
                    ORDER BY quality_score DESC, created_at DESC
                    LIMIT ?
                """
                
                cursor.execute(query, (min_quality, limit))
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"❌ Error getting high quality posts: {e}")
            return []
    
    def get_low_quality_posts(self, max_quality: float = 5.0, limit: int = 50) -> List[Dict]:
        """Get low quality posts for improvement"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM posts 
                    WHERE quality_score <= ? 
                    AND rewrite_status != 'deleted'
                    ORDER BY quality_score ASC, created_at DESC
                    LIMIT ?
                """
                
                cursor.execute(query, (max_quality, limit))
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"❌ Error getting low quality posts: {e}")
            return []
    
    def get_unanalyzed_posts(self, limit: int = 100, platforms: Optional[List[str]] = None) -> List[Dict]:
        """Get posts that haven't been analyzed yet"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM posts 
                    WHERE analysis_timestamp IS NULL 
                    AND rewrite_status != 'deleted'
                """
                params: List[Any] = []

                if platforms:
                    placeholders = ','.join(['?'] * len(platforms))
                    query += f" AND platform IN ({placeholders})"
                    params.extend(platforms)

                query += " ORDER BY created_at DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"❌ Error getting unanalyzed posts: {e}")
            return []
    
    def get_posts_by_score_range(self, min_score: float, max_score: float, limit: int = 100) -> List[Dict]:
        """Get posts within a score range"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = """
                    SELECT * FROM posts 
                    WHERE quality_score >= ? AND quality_score <= ?
                    AND rewrite_status != 'deleted'
                    ORDER BY quality_score DESC
                    LIMIT ?
                """
                
                cursor.execute(query, (min_score, max_score, limit))
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            print(f"❌ Error getting posts by score range: {e}")
            return []
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total analyzed posts
                cursor.execute("SELECT COUNT(*) FROM posts WHERE analysis_timestamp IS NOT NULL")
                analyzed_count = cursor.fetchone()[0]
                
                # Total unanalyzed posts
                cursor.execute("SELECT COUNT(*) FROM posts WHERE analysis_timestamp IS NULL AND rewrite_status != 'deleted'")
                unanalyzed_count = cursor.fetchone()[0]
                
                # Rewrite candidates
                cursor.execute("SELECT COUNT(*) FROM posts WHERE is_rewrite_candidate = TRUE")
                rewrite_candidates = cursor.fetchone()[0]
                
                # Quality distribution
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN quality_score >= 7 THEN 1 END) as high_quality,
                        COUNT(CASE WHEN quality_score BETWEEN 5 AND 6.9 THEN 1 END) as medium_quality,
                        COUNT(CASE WHEN quality_score < 5 THEN 1 END) as low_quality
                    FROM posts 
                    WHERE analysis_timestamp IS NOT NULL AND rewrite_status != 'deleted'
                """)
                quality_dist = cursor.fetchone()
                
                return {
                    'analyzed_posts': analyzed_count,
                    'unanalyzed_posts': unanalyzed_count,
                    'rewrite_candidates': rewrite_candidates,
                    'quality_distribution': {
                        'high_quality': quality_dist[0] or 0,
                        'medium_quality': quality_dist[1] or 0,
                        'low_quality': quality_dist[2] or 0
                    }
                }
                
        except Exception as e:
            print(f"❌ Error getting analysis stats: {e}")
            return {}
    
    def _serialize_json(self, obj: Any) -> str:
        """Safely serialize JSON objects"""
        try:
            return json.dumps(obj) if obj is not None else 'null'
        except Exception:
            return 'null'
    
    def _create_insights_summary(self, insights: List[str], action_items: List[str]) -> str:
        """Create a summary of insights and action items"""
        summary_parts = []
        
        if insights:
            summary_parts.append(f"Key insights: {', '.join(insights[:3])}")
        
        if action_items:
            summary_parts.append(f"Action items: {', '.join(action_items[:3])}")
        
        return ". ".join(summary_parts) if summary_parts else "Analysis completed"
