#!/usr/bin/env python3
"""
Check categorization system performance
"""

from scripts.database_manager import DatabaseManager
import pandas as pd

def check_categorization():
    """Analyze categorization performance"""
    print("🔍 Analyzing categorization system...")
    print("=" * 50)
    
    # Get database manager
    db = DatabaseManager()
    posts = db.get_all_posts()
    
    print(f"📊 Total posts in database: {len(posts)}")
    
    if posts.empty:
        print("❌ No posts found in database")
        return
    
    # Use the DataFrame directly
    df = posts
    
    print(f"\n📋 Available columns: {list(df.columns)}")
    
    # Check category distribution
    if 'category' in df.columns:
        category_counts = df['category'].value_counts()
        print("\n🏷️ Category distribution:")
        for category, count in category_counts.items():
            print(f"   {category}: {count} posts")
        
        # Check for uncategorized posts
        uncategorized = df[df['category'].isna() | (df['category'] == '') | (df['category'] == 'Unknown')]
        print(f"\n❓ Uncategorized posts: {len(uncategorized)}")
        
        if len(uncategorized) > 0:
            print("   Sample uncategorized posts:")
            for idx, post in uncategorized.head(3).iterrows():
                print(f"   - {post.get('content', 'No content')[:100]}...")
    
    # Check value scoring
    if 'value_score' in df.columns:
        scored_posts = df[df['value_score'].notna()]
        unscored_posts = df[df['value_score'].isna()]
        
        print("\n⭐ Value scoring:")
        print(f"   Scored posts: {len(scored_posts)}")
        print(f"   Unscored posts: {len(unscored_posts)}")
        
        if len(scored_posts) > 0:
            print(f"   Score range: {scored_posts['value_score'].min():.2f} - {scored_posts['value_score'].max():.2f}")
            print(f"   Average score: {scored_posts['value_score'].mean():.2f}")
    
    # Check platform distribution
    if 'platform' in df.columns:
        platform_counts = df['platform'].value_counts()
        print("\n📱 Platform distribution:")
        for platform, count in platform_counts.items():
            print(f"   {platform}: {count} posts")
    
    # Check content analysis
    analysis_fields = ['sentiment', 'concepts', 'tags', 'analysis_summary']
    print("\n🧠 AI Analysis fields:")
    for field in analysis_fields:
        if field in df.columns:
            filled = df[df[field].notna() & (df[field] != '')]
            print(f"   {field}: {len(filled)}/{len(df)} posts analyzed")
        else:
            print(f"   {field}: Not available")
    
    # Check for recent posts
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
        recent_posts = df[df['created_at'].notna()].sort_values('created_at', ascending=False)
        if len(recent_posts) > 0:
            print("\n📅 Recent posts:")
            for idx, post in recent_posts.head(3).iterrows():
                print(f"   {post['created_at'].strftime('%Y-%m-%d %H:%M')} - {post.get('category', 'Unknown')} - {post.get('content', 'No content')[:50]}...")

if __name__ == "__main__":
    check_categorization()
