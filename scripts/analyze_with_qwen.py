#!/usr/bin/env python3
"""
Analyze posts using the existing Qwen integration.
This script will:
1. Load unanalyzed posts from the database
2. Use the existing IntelligentContentAnalyzer
3. Update posts with analysis results
"""
import os
import sys
import json
import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/analyze_posts.log')
    ]
)
logger = logging.getLogger(__name__)

# Import after path setup
from src.services.database import DatabaseManager
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer

def get_unanalyzed_posts(db: DatabaseManager, limit: int = 10) -> List[Dict]:
    """Get posts that haven't been analyzed yet"""
    try:
        # Get all posts and filter in memory
        all_posts = db.get_all_posts(include_deleted=False)
        
        # Filter posts that need analysis
        unanalyzed = all_posts[
            (all_posts['ai_summary'].isna()) | 
            (all_posts['ai_summary'] == '')
        ]
        
        # Convert to list of dicts and limit results
        return unanalyzed.head(limit).to_dict('records')
        
    except Exception as e:
        logger.error(f"Error fetching unanalyzed posts: {str(e)}")
        return []

def analyze_post(analyzer: IntelligentContentAnalyzer, post: Dict) -> Dict:
    """Analyze a single post using the existing analyzer"""
    try:
        from src.core.extraction.social_extractor_base import SocialPost
        
        # Create a SocialPost object with required fields
        created_at = post.get('created_at')
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                created_at = datetime.utcnow()
        
        social_post = SocialPost(
            platform=post.get('platform', 'unknown'),
            author=post.get('author', ''),
            author_handle=post.get('author_handle', ''),
            content=post.get('content', ''),
            created_at=created_at,
            url=post.get('url', ''),
            post_type=post.get('post_type', 'post'),
            media_urls=json.loads(post.get('media_urls', '[]')) if post.get('media_urls') else [],
            hashtags=json.loads(post.get('hashtags', '[]')) if post.get('hashtags') else [],
            mentions=json.loads(post.get('mentions', '[]')) if post.get('mentions') else [],
            engagement=json.loads(post.get('engagement', '{}')) if post.get('engagement') else {},
            is_saved=bool(post.get('is_saved', True)),
            saved_at=datetime.fromisoformat(post['saved_at'].replace('Z', '+00:00')) if post.get('saved_at') else None,
            folder_category=post.get('folder_category'),
            id=str(post.get('id', '')),
            post_id=str(post.get('post_id', ''))
        )
        
        # Get sentiment
        sentiment = analyzer.sentiment_analyzer.polarity_scores(social_post.content)
        
        # Get AI analysis
        analysis = analyzer.analyze_bookmark(
            post=social_post,
            include_comments=False,
            include_media=bool(social_post.media_urls)
        )
        
        # Map analysis to database schema
        return {
            'ai_summary': analysis.get('summary', post.get('summary', '')),
            'sentiment': json.dumps(sentiment),
            'key_concepts': ', '.join(analysis.get('key_concepts', [])),
            'value_score': analysis.get('value_score', 0.5) * 10,  # Scale 0-1 to 0-10
            'category': analysis.get('category', post.get('category', '')),
            'subcategory': post.get('subcategory', ''),
            'topic': analysis.get('topic', post.get('topic', '')),
            'content_type': analysis.get('content_type', post.get('content_type', '')),
            'intelligence_analysis': json.dumps({
                'time_sensitive': analysis.get('is_time_sensitive', False),
                'time_sensitivity_reason': analysis.get('time_sensitivity_reason', ''),
                'target_platforms': analysis.get('target_platforms', []),
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'insights': analysis.get('insights', [])
            })
        }
        
    except Exception as e:
        logger.error(f"Error analyzing post {post.get('id')}: {str(e)}")
        return {}

def update_post_analysis(db: DatabaseManager, post_id: int, analysis: Dict) -> bool:
    """Update a post with analysis results"""
    if not analysis:
        return False
        
    try:
        # Get the existing post
        posts = db.get_all_posts(include_deleted=True)
        post = posts[posts['post_id'] == str(post_id)].iloc[0].to_dict()
        
        # Update with analysis
        post.update(analysis)
        
        # Convert any non-serializable values
        for key, value in post.items():
            if isinstance(value, (list, dict)):
                post[key] = json.dumps(value)
            elif pd.isna(value):
                post[key] = None
        
        # Update the post
        result = db.add_post(post)
        return result
        
    except Exception as e:
        logger.error(f"Error updating post {post_id}: {str(e)}")
        return False

def main():
    # Initialize database
    db_path = project_root / 'data' / 'prismind.db'
    db = DatabaseManager(str(db_path))
    
    # Initialize analyzer
    analyzer = IntelligentContentAnalyzer()
    
    # Process posts in batches
    batch_size = 10
    while True:
        posts = get_unanalyzed_posts(db, limit=batch_size)
        if not posts:
            logger.info("No more posts to analyze")
            break
            
        logger.info(f"Analyzing {len(posts)} posts...")
        
        for post in posts:
            logger.info(f"Analyzing post {post['id']}: {post.get('title', '')[:50]}...")
            analysis = analyze_post(analyzer, post)
            if analysis:
                success = update_post_analysis(db, post['id'], analysis)
                if success:
                    logger.info(f"✅ Updated post {post['id']}")
                else:
                    logger.error(f"❌ Failed to update post {post['id']}")
            
        logger.info("Batch complete. Checking for more posts...")

if __name__ == "__main__":
    main()
