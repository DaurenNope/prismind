#!/usr/bin/env python3
"""
Automatic Reddit saved bookmarks collector using web scraping
"""

import requests
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

class AutomaticRedditBookmarksCollector:
    """Automatically collect Reddit saved bookmarks"""
    
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.username = os.getenv('REDDIT_USERNAME')
        self.password = os.getenv('REDDIT_PASSWORD')
        self.user_agent = os.getenv('REDDIT_USER_AGENT')
        self.access_token = None
        self.session = requests.Session()
        
    def authenticate(self):
        """Authenticate with Reddit"""
        try:
            print("🔍 Authenticating with Reddit...")
            
            auth_url = 'https://www.reddit.com/api/v1/access_token'
            auth_data = {
                'grant_type': 'password',
                'username': self.username,
                'password': self.password
            }
            
            auth_response = self.session.post(
                auth_url,
                data=auth_data,
                auth=(self.client_id, self.client_secret),
                headers={'User-Agent': self.user_agent},
                timeout=15
            )
            
            if auth_response.status_code == 200:
                token_data = auth_response.json()
                self.access_token = token_data['access_token']
                print(f"✅ Reddit authentication successful: {self.access_token[:20]}...")
                return True
            else:
                print(f"❌ Reddit authentication failed: {auth_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Reddit authentication error: {e}")
            return False
    
    def get_saved_posts_via_web(self):
        """Get saved posts via web scraping"""
        try:
            if not self.access_token:
                if not self.authenticate():
                    return []
            
            print("🔍 Fetching saved posts via web scraping...")
            
            # Try to get saved posts using web scraping approach
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': self.user_agent,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            # Try different endpoints
            endpoints = [
                'https://www.reddit.com/api/v1/me/saved',
                'https://reddit.com/api/v1/me/saved',
                'https://www.reddit.com/user/me/saved.json',
                'https://reddit.com/user/me/saved.json'
            ]
            
            for endpoint in endpoints:
                try:
                    print(f"🔍 Trying endpoint: {endpoint}")
                    response = self.session.get(endpoint, headers=headers, timeout=15)
                    
                    print(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            posts = []
                            
                            # Handle different response formats
                            if 'data' in data and 'children' in data['data']:
                                items = data['data']['children']
                            elif isinstance(data, list):
                                items = data
                            else:
                                print(f"❌ Unexpected response format: {list(data.keys())}")
                                continue
                            
                            for item in items:
                                if isinstance(item, dict) and 'data' in item:
                                    post_data = item['data']
                                elif isinstance(item, dict):
                                    post_data = item
                                else:
                                    continue
                                
                                posts.append({
                                    'platform': 'reddit',
                                    'title': post_data.get('title', ''),
                                    'author': post_data.get('author', ''),
                                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                    'content': post_data.get('selftext', ''),
                                    'created_timestamp': datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                                    'score': post_data.get('score', 0),
                                    'subreddit': post_data.get('subreddit', ''),
                                    'is_saved': True
                                })
                            
                            print(f"✅ Found {len(posts)} saved posts using {endpoint}")
                            return posts
                            
                        except json.JSONDecodeError as e:
                            print(f"❌ JSON decode error: {e}")
                            print(f"Response content: {response.text[:200]}")
                            continue
                    else:
                        print(f"❌ Endpoint failed: {response.status_code}")
                        print(f"Response: {response.text[:100]}")
                        continue
                        
                except Exception as e:
                    print(f"❌ Endpoint error: {e}")
                    continue
            
            print("❌ All endpoints failed")
            return []
            
        except Exception as e:
            print(f"❌ Saved posts request failed: {e}")
            return []
    
    def get_saved_posts_fallback(self):
        """Fallback: Get posts from subreddits you're interested in"""
        try:
            print("🔍 Fallback: Getting posts from relevant subreddits...")
            
            # Subreddits that might contain content you're interested in
            subreddits = [
                'programming', 'technology', 'python', 'webdev', 'MachineLearning',
                'startups', 'entrepreneur', 'productivity', 'learnprogramming',
                'cscareerquestions', 'datascience', 'compsci', 'coding'
            ]
            
            all_posts = []
            
            for subreddit in subreddits:
                try:
                    print(f"🔍 Fetching from r/{subreddit}...")
                    
                    url = f'https://www.reddit.com/r/{subreddit}/hot.json?limit=5'
                    headers = {'User-Agent': self.user_agent}
                    
                    response = self.session.get(url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        posts = data.get('data', {}).get('children', [])
                        
                        for post in posts:
                            post_data = post['data']
                            score = post_data.get('score', 0)
                            
                            if score >= 20:  # Only high-quality posts
                                all_posts.append({
                                    'platform': 'reddit',
                                    'title': post_data.get('title', ''),
                                    'author': post_data.get('author', ''),
                                    'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                    'content': post_data.get('selftext', ''),
                                    'created_timestamp': datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                                    'score': score,
                                    'subreddit': subreddit,
                                    'is_saved': False  # Not actually saved
                                })
                        
                        print(f"✅ Found {len(posts)} posts from r/{subreddit}")
                        
                except Exception as e:
                    print(f"❌ Error fetching r/{subreddit}: {e}")
                    continue
            
            # Sort by score and return top posts
            all_posts.sort(key=lambda x: x['score'], reverse=True)
            top_posts = all_posts[:30]  # Top 30 posts
            
            print(f"🎉 Fallback: Collected {len(top_posts)} high-quality posts!")
            return top_posts
            
        except Exception as e:
            print(f"❌ Fallback collection failed: {e}")
            return []
    
    def collect_bookmarks(self):
        """Main method to collect Reddit bookmarks"""
        try:
            print("🤖 AUTOMATIC REDDIT BOOKMARKS COLLECTION")
            print("=" * 50)
            
            # Try to get actual saved posts first
            saved_posts = self.get_saved_posts_via_web()
            
            if saved_posts:
                print(f"✅ Successfully collected {len(saved_posts)} saved bookmarks!")
                return saved_posts
            else:
                print("⚠️ Could not access saved posts, using fallback method...")
                return self.get_saved_posts_fallback()
                
        except Exception as e:
            print(f"❌ Collection failed: {e}")
            return []

def test_automatic_reddit_collection():
    """Test the automatic Reddit collection"""
    print("🧪 Testing Automatic Reddit Bookmarks Collection")
    print("=" * 60)
    
    collector = AutomaticRedditBookmarksCollector()
    posts = collector.collect_bookmarks()
    
    if posts:
        print(f"🎉 SUCCESS! Collected {len(posts)} posts:")
        for i, post in enumerate(posts[:10]):  # Show first 10
            saved_status = "✅ SAVED" if post.get('is_saved') else "📊 POPULAR"
            print(f"   {i+1}. [{post['subreddit']}] {post['title'][:50]}...")
            print(f"      Author: {post['author']} | Score: {post['score']} | {saved_status}")
            print()
    else:
        print("❌ No posts collected")

if __name__ == "__main__":
    test_automatic_reddit_collection()
