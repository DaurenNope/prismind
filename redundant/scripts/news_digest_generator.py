#!/usr/bin/env python3
"""
News Digest Generator for Prismind
Converts AI-analyzed posts into readable news articles
"""

import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('.')

from scripts.supabase_manager import SupabaseManager

class NewsDigestGenerator:
    def __init__(self):
        self.db = SupabaseManager()
        
    def get_recent_posts(self, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent posts from the database"""
        try:
            posts = self.db.get_posts(limit=limit)
            
            # Filter by recent posts (last N days)
            recent_posts = []
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for post in posts:
                created_at = post.get('created_at')
                if created_at:
                    try:
                        if isinstance(created_at, str):
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if created_at >= cutoff_date:
                            recent_posts.append(post)
                    except:
                        # If date parsing fails, include the post
                        recent_posts.append(post)
                else:
                    # If no date, include the post
                    recent_posts.append(post)
            
            return recent_posts
        except Exception as e:
            print(f"❌ Error getting recent posts: {e}")
            return []
    
    def get_top_posts(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get top posts by value score"""
        try:
            posts = self.db.get_posts(limit=limit)
            
            # Sort by value_score (highest first)
            sorted_posts = sorted(
                posts, 
                key=lambda x: x.get('value_score', 0) or 0, 
                reverse=True
            )
            
            return sorted_posts[:limit]
        except Exception as e:
            print(f"❌ Error getting top posts: {e}")
            return []
    
    def get_posts_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get posts by category"""
        try:
            posts = self.db.get_posts(limit=limit)
            
            # Filter by category
            category_posts = [
                post for post in posts 
                if post.get('category', '').lower() == category.lower()
            ]
            
            return category_posts[:limit]
        except Exception as e:
            print(f"❌ Error getting posts by category: {e}")
            return []
    
    def format_post_as_news(self, post: Dict[str, Any]) -> str:
        """Format a single post as a clean, readable snippet"""
        title = post.get('title', 'No title')
        content = post.get('content', 'No content')
        ai_summary = post.get('ai_summary', '')
        category = post.get('category', 'General')
        value_score = post.get('value_score', 0)
        platform = post.get('platform', 'Unknown')
        author = post.get('author', 'Unknown')
        url = post.get('url', '')
        
        # Use AI summary if available, otherwise use content
        summary = ai_summary if ai_summary else content[:100] + "..." if len(content) > 100 else content
        
        # Create clean, minimal format with better spacing
        if value_score >= 8:
            emoji = "🔥"
        elif value_score >= 6:
            emoji = "💡"
        else:
            emoji = "📝"
        
        post_format = f"{emoji} **{title}**\n\n{summary}\n\n👤 {author} | {category} | ⭐ {value_score}/10\n🔗 [Read more]({url})"
        
        return post_format.strip()
    
    def generate_daily_digest(self) -> str:
        """Generate a clean daily news digest with better summaries"""
        print("📰 Generating daily news digest...")
        
        # Get recent posts from last 24 hours
        recent_posts = self.get_recent_posts(days=1, limit=10)
        
        if not recent_posts:
            return "🤖 No new content today. I'll keep an eye out for fresh stuff! 📝"
        
        # Sort by value score and take top 5
        top_posts = sorted(recent_posts, key=lambda x: x.get('value_score', 0) or 0, reverse=True)[:5]
        
        # Generate clean digest with better summaries
        digest = f"📰 **Daily Digest** - {datetime.now().strftime('%B %d')}\n\n"
        digest += f"📊 Found {len(recent_posts)} new posts today\n\n"
        
        for i, post in enumerate(top_posts, 1):
            title = post.get('title', 'No title')
            value_score = post.get('value_score', 0)
            category = post.get('category', 'General')
            ai_summary = post.get('ai_summary', '')
            content = post.get('content', '')
            
            # Create better summary
            if ai_summary:
                summary = ai_summary[:80] + "..." if len(ai_summary) > 80 else ai_summary
            else:
                summary = content[:80] + "..." if len(content) > 80 else content
            
            if value_score >= 8:
                emoji = "🔥"
            elif value_score >= 6:
                emoji = "💡"
            else:
                emoji = "📝"
            
            digest += f"{emoji} **{i}.** {title}\n"
            digest += f"   {summary}\n"
            digest += f"   {category} | ⭐ {value_score}/10\n\n"
        
        return digest.strip()
    
    def generate_weekly_digest(self) -> str:
        """Generate a weekly news digest"""
        print("📰 Generating weekly news digest...")
        
        # Get recent posts from last 7 days
        recent_posts = self.get_recent_posts(days=7, limit=30)
        
        if not recent_posts:
            return "🤖 Quiet week! No new content found. I'll keep monitoring for fresh stuff. 📝"
        
        # Get top posts by value score
        top_posts = sorted(recent_posts, key=lambda x: x.get('value_score', 0) or 0, reverse=True)[:8]
        

        
        # Generate conversational digest
        digest = f"🤖 **Weekly AI Assistant Report** - Week of {datetime.now().strftime('%B %d')}\n\n"
        digest += f"Analyzed {len(recent_posts)} posts this week. Here are the highlights:\n\n"
        
        for i, post in enumerate(top_posts, 1):
            title = post.get('title', 'No title')
            value_score = post.get('value_score', 0)
            category = post.get('category', 'General')
            url = post.get('url', '')
            
            # Add ranking and brief info
            digest += f"**{i}.** {title}\n"
            digest += f"   ⭐ {value_score}/10 | {category}\n"
            digest += f"   🔗 [Read more]({url})\n\n"
        
        return digest
    
    def generate_category_digest(self, category: str) -> str:
        """Generate a conversational digest for a specific category"""
        print(f"📰 Generating {category} digest...")
        
        posts = self.get_posts_by_category(category, limit=10)
        
        if not posts:
            return f"🤖 No {category} content found yet. I'll let you know when I find something interesting! 📝"
        
        # Sort by value score and take top 5
        top_posts = sorted(posts, key=lambda x: x.get('value_score', 0) or 0, reverse=True)[:5]
        
        # Create category-specific intros
        category_intros = {
            'technology': "Here's what's hot in tech right now:",
            'ai': "Latest AI developments that caught my attention:",
            'business': "Business insights worth sharing:",
            'cryptocurrency': "Crypto world updates:",
            'general': f"Some interesting {category} content:"
        }
        
        intro = category_intros.get(category.lower(), f"Here's what I found in {category}:")
        
        digest = f"🤖 **{category.title()} Update**\n\n{intro}\n\n"
        
        for post in top_posts:
            digest += self.format_post_as_news(post)
        
        return digest

def main():
    """Test the news digest generator"""
    generator = NewsDigestGenerator()
    
    print("🧪 Testing News Digest Generator")
    print("=" * 50)
    
    # Test daily digest
    print("\n📰 Daily Digest:")
    print("-" * 30)
    daily_digest = generator.generate_daily_digest()
    print(daily_digest[:500] + "..." if len(daily_digest) > 500 else daily_digest)
    
    # Test weekly digest
    print("\n📰 Weekly Digest:")
    print("-" * 30)
    weekly_digest = generator.generate_weekly_digest()
    print(weekly_digest[:500] + "..." if len(weekly_digest) > 500 else weekly_digest)
    
    # Test category digest
    print("\n📰 Technology Digest:")
    print("-" * 30)
    tech_digest = generator.generate_category_digest("Technology")
    print(tech_digest[:500] + "..." if len(tech_digest) > 500 else tech_digest)

if __name__ == "__main__":
    main()
