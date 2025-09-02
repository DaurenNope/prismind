#!/usr/bin/env python3
"""
Update curation table to only include posts that need manual review
"""

import sqlite3
import pandas as pd
from pathlib import Path
from multi_table_manager import MultiTableManager
import hashlib
from typing import Dict, List, Any, Optional

class CurationTableUpdater:
    def __init__(self):
        self.db_path = Path("data/prismind.db")
        self.supabase_db = MultiTableManager()
        
    def get_uncertain_bookmarks(self) -> pd.DataFrame:
        """Get bookmarks that were categorized as uncertain"""
        with sqlite3.connect(self.db_path) as conn:
            # Get posts that are bookmarked (not deleted)
            query = """
            SELECT p.*, cc.use_case, cc.status as curation_status, cc.notes as curation_notes
            FROM posts p
            LEFT JOIN content_curation cc ON p.post_id = cc.post_id
            WHERE p.is_deleted = 0
            ORDER BY p.created_timestamp DESC
            """
            return pd.read_sql_query(query, conn)
    
    def analyze_content(self, content: str, title: str = "", author: str = "") -> Dict[str, Any]:
        """Analyze content to determine category and quality"""
        full_text = f"{title} {content}".lower()
        
        # Programming indicators
        programming_keywords = [
            'code', 'programming', 'javascript', 'python', 'react', 'vue', 'angular',
            'framework', 'library', 'api', 'database', 'sql', 'git', 'docker',
            'tutorial', 'how to', 'implementation', 'function', 'class', 'component',
            'algorithm', 'data structure', 'optimization', 'performance', 'debug',
            'testing', 'unit test', 'integration', 'deployment', 'ci/cd'
        ]
        
        # Research indicators
        research_keywords = [
            'study', 'research', 'analysis', 'data', 'statistics', 'survey',
            'report', 'findings', 'evidence', 'scientific', 'peer-reviewed',
            'journal', 'paper', 'thesis', 'investigation', 'examination',
            'fact-check', 'verify', 'validate', 'credibility', 'source'
        ]
        
        # Copywriting indicators
        copywriting_keywords = [
            'social media', 'marketing', 'copywriting', 'content creation',
            'brand', 'engagement', 'viral', 'trending', 'influencer',
            'post', 'tweet', 'thread', 'story', 'reel', 'video',
            'caption', 'hashtag', 'call to action', 'cta', 'conversion'
        ]
        
        # Count keyword matches
        programming_score = sum(1 for keyword in programming_keywords if keyword in full_text)
        research_score = sum(1 for keyword in research_keywords if keyword in full_text)
        copywriting_score = sum(1 for keyword in copywriting_keywords if keyword in full_text)
        
        # Determine category based on highest score
        scores = {
            'programming': programming_score,
            'research': research_score,
            'copywriting': copywriting_score
        }
        
        max_score = max(scores.values())
        category = max(scores, key=scores.get) if max_score > 0 else 'uncertain'
        
        return {
            'category': category,
            'programming_score': programming_score,
            'research_score': research_score,
            'copywriting_score': copywriting_score,
            'confidence': max_score / (sum(scores.values()) + 1)  # Confidence in categorization
        }
    
    def update_curation_table(self):
        """Update curation table to only include uncertain posts"""
        print("🔍 Analyzing bookmarks for curation table...")
        
        # Get all bookmarks
        bookmarks_df = self.get_uncertain_bookmarks()
        
        if bookmarks_df.empty:
            print("❌ No bookmarks found in database")
            return
        
        print(f"📊 Found {len(bookmarks_df)} bookmarks to analyze")
        
        # Track uncertain posts
        uncertain_posts = []
        
        # Analyze each bookmark
        for idx, row in bookmarks_df.iterrows():
            post_id = row['post_id']
            content = row.get('content', '')
            title = row.get('ai_summary', '') or row.get('content', '')[:100]
            author = row.get('author', '')
            
            # Analyze the content
            analysis = self.analyze_content(content, title, author)
            
            # If uncertain, add to curation table
            if analysis['category'] == 'uncertain':
                uncertain_posts.append({
                    'post_id': post_id,
                    'content': content,
                    'title': title,
                    'author': author,
                    'analysis': analysis
                })
        
        print(f"📋 Found {len(uncertain_posts)} uncertain posts for curation")
        
        # Clear existing curation table
        self.clear_curation_table()
        
        # Add uncertain posts to curation table
        self.add_uncertain_posts_to_curation(uncertain_posts)
        
        print(f"✅ Updated curation table with {len(uncertain_posts)} posts needing manual review")
    
    def clear_curation_table(self):
        """Clear the existing curation table"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM content_curation")
            conn.commit()
            print("🗑️  Cleared existing curation table")
    
    def add_uncertain_posts_to_curation(self, uncertain_posts: List[Dict]):
        """Add uncertain posts to the curation table"""
        with sqlite3.connect(self.db_path) as conn:
            for post in uncertain_posts:
                # Determine suggested use case based on analysis
                analysis = post['analysis']
                scores = {
                    'programming': analysis['programming_score'],
                    'research': analysis['research_score'],
                    'copywriting': analysis['copywriting_score']
                }
                
                # Get the highest scoring category as suggestion
                suggested_use_case = max(scores, key=scores.get) if max(scores.values()) > 0 else 'general'
                
                # Create notes with analysis
                notes = f"Auto-analysis: Programming score: {analysis['programming_score']}, Research score: {analysis['research_score']}, Copywriting score: {analysis['copywriting_score']}, Confidence: {analysis['confidence']:.2f}"
                
                # Insert into curation table
                conn.execute("""
                    INSERT INTO content_curation 
                    (post_id, use_case, status, notes, priority, user_id) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    post['post_id'],
                    suggested_use_case,
                    'pending',
                    notes,
                    1,  # Default priority
                    'default'
                ))
            
            conn.commit()
            print(f"📝 Added {len(uncertain_posts)} posts to curation table")

if __name__ == "__main__":
    updater = CurationTableUpdater()
    updater.update_curation_table() 