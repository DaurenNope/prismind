#!/usr/bin/env python3
"""
Analyze a few sample posts to demonstrate the analysis process.
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_sample_posts():
    # Import after path setup
    from src.services.database import DatabaseManager
    from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
    from src.core.extraction.social_extractor_base import SocialPost
    from datetime import datetime

    # Initialize database and analyzer
    db = DatabaseManager('data/prismind.db')
    analyzer = IntelligentContentAnalyzer()

    # Get 3 unanalyzed posts
    posts = db.get_all_posts(include_deleted=False)
    unanalyzed = posts[(posts['ai_summary'].isna()) | (posts['ai_summary'] == '')].head(3)

    print('\n=== Analyzing 3 Posts ===\n')

    for _, post in unanalyzed.iterrows():
        print(f'\n--- Analyzing Post {post["id"]} ---')
        print(f'Platform: {post["platform"]}')
        content_preview = post["content"][:200] + '...' if isinstance(post.get('content'), str) and post['content'] else 'No content'
        print(f'Content: {content_preview}')
        
        try:
            # Create SocialPost object
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
                media_urls=post.get('media_urls', []),
                hashtags=post.get('hashtags', []),
                mentions=post.get('mentions', []),
                engagement=post.get('engagement', {}),
                is_saved=bool(post.get('is_saved', True)),
                saved_at=post.get('saved_at'),
                folder_category=post.get('folder_category'),
                id=str(post.get('id', '')),
                post_id=str(post.get('post_id', ''))
            )
            
            # Analyze the post
            print('\nAnalysis Results:')
            analysis = analyzer.analyze_bookmark(social_post, include_comments=False)
            
            # Print key analysis results
            print(f'Summary: {analysis.get("summary", "No summary")}')
            print(f'Value Score: {analysis.get("value_score", "N/A")}')
            print(f'Key Concepts: {analysis.get("key_concepts", [])}')
            print(f'Time Sensitive: {analysis.get("is_time_sensitive", False)}')
            print(f'Reason: {analysis.get("time_sensitivity_reason", "")}')
            
        except Exception as e:
            print(f'Error analyzing post: {str(e)}')
            import traceback
            traceback.print_exc()

    print('\n=== Analysis Complete ===')

if __name__ == "__main__":
    analyze_sample_posts()
