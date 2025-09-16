#!/usr/bin/env python3
"""
Test script to verify the entire PrisMind collection and analysis pipeline
"""

import sys
import os
import json
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def test_collection():
    """Test the collection process"""
    print("🧪 Testing Collection Process...")
    
    try:
        from src.scripts.cookie_collectors import collect_twitter_bookmarks
        from src.scripts.database_manager import DatabaseManager
        
        # Initialize database
        db_manager = DatabaseManager()
        print("✅ Database initialized")
        
        # Test Twitter collection
        print("🐦 Collecting Twitter bookmarks...")
        twitter_count = collect_twitter_bookmarks(db_manager)
        print(f"✅ Twitter collection complete: {twitter_count} posts")
        
        return True
    except Exception as e:
        print(f"❌ Collection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_analysis():
    """Test the analysis process"""
    print("\n🧠 Testing Analysis Process...")
    
    try:
        from core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
        from core.extraction.social_extractor_base import SocialPost
        
        # Initialize analyzer
        analyzer = IntelligentContentAnalyzer()
        print("✅ Analyzer initialized")
        
        # Create a mock post with all required parameters
        mock_post = SocialPost(
            post_id='test123',
            platform='twitter',
            author='testuser',
            content='The latest advancements in artificial intelligence are revolutionizing how we approach problem-solving. Machine learning models can now process vast amounts of data to identify patterns that humans might miss.',
            created_at='2023-01-01T00:00:00Z',
            url='https://twitter.com/testuser/status/test123',
            media_urls=[],
            author_handle='testuser',
            post_type='tweet'
        )
        
        # Analyze the mock post
        print("🔍 Analyzing mock post...")
        result = analyzer.analyze_bookmark(mock_post)
        print("✅ Analysis complete")
        print(f"Analysis result keys: {list(result.keys())}")
        
        return True
    except Exception as e:
        print(f"❌ Analysis test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database():
    """Test database operations"""
    print("\n💾 Testing Database Operations...")
    
    try:
        from scripts.database_manager import DatabaseManager
        import sqlite3
        
        # Initialize database
        db_manager = DatabaseManager()
        
        # Get post count using direct SQL since the method doesn't exist
        with sqlite3.connect('data/prismind.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM posts")
            count = cursor.fetchone()[0]
        print(f"✅ Database contains {count} posts")
        
        # Get recent posts
        with sqlite3.connect('data/prismind.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT post_id, platform, created_at FROM posts ORDER BY created_at DESC LIMIT 5")
            recent_posts = cursor.fetchall()
        print(f"✅ Retrieved {len(recent_posts)} recent posts")
        
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Starting PrisMind Pipeline Test")
    print("=" * 50)
    
    tests = [
        test_database,
        test_collection,
        test_analysis
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📋 Test Results Summary:")
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test.__name__}")
    
    overall = all(results)
    print(f"\n🎯 Overall Result: {'✅ ALL TESTS PASSED' if overall else '❌ SOME TESTS FAILED'}")
    
    return 0 if overall else 1

if __name__ == "__main__":
    sys.exit(main())