#!/usr/bin/env python3
"""
Working Reddit collection using public API + web scraping
"""

import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

class WorkingRedditExtractor:
    """Reddit extractor that actually works"""
    
    def __init__(self):
        load_dotenv()
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'PrisMind:1.0 (by /u/YourUsername)')
        
    def get_reddit_posts_from_subreddits(self):
        """Get posts from subreddits you're interested in"""
        try:
            print("🔍 Collecting Reddit posts from popular subreddits...")
            
            # Subreddits that typically have good content
            subreddits = [
                'programming', 'technology', 'python', 'webdev', 'MachineLearning',
                'artificial', 'startups', 'entrepreneur', 'productivity', 'learnprogramming',
                'cscareerquestions', 'datascience', 'compsci', 'coding', 'javascript'
            ]
            
            all_posts = []
            
            for subreddit in subreddits:
                try:
                    print(f"🔍 Fetching from r/{subreddit}...")
                    
                    # Use public Reddit API
                    url = f'https://www.reddit.com/r/{subreddit}/hot.json?limit=10'
                    headers = {'User-Agent': self.user_agent}
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get('data', {}).get('children', [])
                        
                        for post in posts:
                            post_data = post['data']
                            
                            # Filter for high-quality posts
                            score = post_data.get('score', 0)
                            if score >= 10:  # Only posts with decent engagement
                                all_posts.append({
                                    'platform': 'reddit',
                                    'title': post_data.get('title', ''),
                                    'author': post_data.get('author', ''),
                                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                    'content': post_data.get('selftext', ''),
                                    'created_timestamp': datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                                    'score': score,
                                    'subreddit': subreddit,
                                    'num_comments': post_data.get('num_comments', 0)
                                })
                        
                        print(f"✅ Found {len(posts)} posts from r/{subreddit}")
                        
                    else:
                        print(f"❌ Failed to fetch r/{subreddit}: {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ Error fetching r/{subreddit}: {e}")
                    continue
            
            # Sort by score and return top posts
            all_posts.sort(key=lambda x: x['score'], reverse=True)
            top_posts = all_posts[:50]  # Top 50 posts
            
            print(f"🎉 Collected {len(top_posts)} high-quality Reddit posts!")
            return top_posts
            
        except Exception as e:
            print(f"❌ Reddit collection failed: {e}")
            return []
    
    def get_reddit_saved_posts_alternative(self):
        """Alternative approach for saved posts using web scraping"""
        try:
            print("🔍 Attempting alternative saved posts collection...")
            
            # This would require browser automation or web scraping
            # For now, return empty list
            print("⚠️ Saved posts collection requires browser automation")
            print("💡 Recommendation: Use the subreddit-based collection above")
            return []
            
        except Exception as e:
            print(f"❌ Alternative saved posts failed: {e}")
            return []

def test_working_reddit():
    """Test the working Reddit extractor"""
    print("🧪 Testing Working Reddit Extractor")
    print("=" * 50)
    
    extractor = WorkingRedditExtractor()
    posts = extractor.get_reddit_posts_from_subreddits()
    
    if posts:
        print(f"🎉 SUCCESS! Found {len(posts)} high-quality posts:")
        for i, post in enumerate(posts[:10]):  # Show first 10
            print(f"   {i+1}. [{post['subreddit']}] {post['title'][:60]}...")
            print(f"      Author: {post['author']} | Score: {post['score']} | Comments: {post['num_comments']}")
            print()
    else:
        print("❌ No posts found")

if __name__ == "__main__":
    test_working_reddit()
