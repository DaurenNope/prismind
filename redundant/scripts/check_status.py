#!/usr/bin/env python3
"""
Comprehensive Status Checker for Prismind
Shows database status, AI analysis progress, and potential issues
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('.')

from scripts.supabase_manager import SupabaseManager

def check_database_status():
    """Check comprehensive database status"""
    print("🔍 PRISMIND STATUS CHECK")
    print("=" * 50)
    
    try:
        db = SupabaseManager()
        posts = db.get_posts(limit=1000)
        
        print(f"📊 Total posts in database: {len(posts)}")
        
        # Check for duplicates
        content_groups = {}
        duplicates = 0
        duplicate_posts = []
        
        for post in posts:
            content = post.get('content', '').strip()
            if content:
                if content not in content_groups:
                    content_groups[content] = [post]
                else:
                    content_groups[content].append(post)
                    duplicates += 1
                    if len(duplicate_posts) < 5:  # Show first 5 duplicates
                        duplicate_posts.append(post)
        
        print(f"🔍 Duplicate posts: {duplicates}")
        if duplicates > 0:
            print("   ⚠️  Duplicates found! Consider running clean_duplicates.py")
            for i, post in enumerate(duplicate_posts):
                print(f"     {i+1}. ID: {post.get('id')} - {post.get('title', 'No title')[:50]}...")
        
        # Check AI analysis status
        ai_analyzed = 0
        no_ai_posts = []
        
        for post in posts:
            has_ai = (
                (post.get('ai_summary') and str(post.get('ai_summary')).strip() and str(post.get('ai_summary')) != 'None') or
                (post.get('summary') and str(post.get('summary')).strip() and str(post.get('summary')) != 'None') or
                (post.get('category') and post.get('value_score') and post.get('value_score') > 0)
            )
            if has_ai:
                ai_analyzed += 1
            else:
                if len(no_ai_posts) < 5:  # Show first 5 posts without AI
                    no_ai_posts.append(post)
        
        print(f"🤖 Posts with AI analysis: {ai_analyzed}")
        print(f"❌ Posts without AI analysis: {len(posts) - ai_analyzed}")
        print(f"📈 AI coverage: {ai_analyzed/len(posts)*100:.1f}%")
        
        if len(posts) - ai_analyzed > 0:
            print("   ⚠️  Some posts need AI analysis! Consider running reanalyze_simple.py")
            for i, post in enumerate(no_ai_posts):
                print(f"     {i+1}. ID: {post.get('id')} - {post.get('title', 'No title')[:50]}...")
        
        # Check by platform
        platforms = {}
        for post in posts:
            platform = post.get('platform', 'unknown')
            if platform not in platforms:
                platforms[platform] = {'total': 0, 'analyzed': 0, 'recent': 0}
            platforms[platform]['total'] += 1
            
            has_ai = (
                (post.get('ai_summary') and str(post.get('ai_summary')).strip() and str(post.get('ai_summary')) != 'None') or
                (post.get('summary') and str(post.get('summary')).strip() and str(post.get('summary')) != 'None') or
                (post.get('category') and post.get('value_score') and post.get('value_score') > 0)
            )
            if has_ai:
                platforms[platform]['analyzed'] += 1
            
            # Check for recent posts (last 7 days)
            created_at = post.get('created_at')
            if created_at:
                try:
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    if (datetime.now() - created_at).days <= 7:
                        platforms[platform]['recent'] += 1
                except Exception:
                    pass
        
        print("\n📱 By Platform:")
        for platform, stats in platforms.items():
            coverage = stats['analyzed']/stats['total']*100 if stats['total'] > 0 else 0
            print(f"  {platform}: {stats['analyzed']}/{stats['total']} ({coverage:.1f}%) - Recent: {stats['recent']}")
        
        # Check for potential issues
        print("\n🔧 POTENTIAL ISSUES:")
        issues = []
        
        if duplicates > 0:
            issues.append(f"❌ {duplicates} duplicate posts found")
        
        if len(posts) - ai_analyzed > 0:
            issues.append(f"❌ {len(posts) - ai_analyzed} posts need AI analysis")
        
        # Check for posts with missing critical fields
        missing_fields = 0
        for post in posts:
            if not post.get('content') or not post.get('title'):
                missing_fields += 1
        
        if missing_fields > 0:
            issues.append(f"❌ {missing_fields} posts missing critical fields")
        
        if not issues:
            print("✅ No issues detected!")
        else:
            for issue in issues:
                print(f"  {issue}")
        
        # Recommendations
        print("\n💡 RECOMMENDATIONS:")
        if duplicates > 0:
            print("  🧹 Run: python3 clean_duplicates.py")
        if len(posts) - ai_analyzed > 0:
            print("  🤖 Run: python3 reanalyze_simple.py")
        print("  📊 Run: python3 collect_multi_platform.py (for new content)")
        print("  🚀 Run: streamlit run app.py (to view dashboard)")
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

def check_environment():
    """Check environment setup"""
    print("\n🔧 ENVIRONMENT CHECK:")
    print("=" * 30)
    
    # Check required environment variables
    required_vars = [
        'SUPABASE_URL', 'SUPABASE_KEY', 'MISTRAL_API_KEY', 
        'GOOGLE_GEMINI_API_KEY', 'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
    else:
        print("✅ All required environment variables found")
    
    # Check if .env file exists
    if os.path.exists('.env'):
        print("✅ .env file found")
    else:
        print("❌ .env file not found")

if __name__ == "__main__":
    check_database_status()
    check_environment()
