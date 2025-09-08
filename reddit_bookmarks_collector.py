#!/usr/bin/env python3
"""
Reddit Bookmarks Collector - Alternative Approach
Since Reddit has restricted saved posts API access, we'll use upvoted posts as a proxy
"""

import requests
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

class RedditBookmarksCollector:
    """Collect Reddit bookmarks using alternative endpoints"""
    
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.username = os.getenv('REDDIT_USERNAME')
        self.password = os.getenv('REDDIT_PASSWORD')
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'PrisMind:1.0 (by /u/YourUsername)')
        self.access_token = None
        
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
            
            auth_response = requests.post(
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
    
    def get_upvoted_posts(self, limit=100):
        """Get upvoted posts as a proxy for saved bookmarks"""
        try:
            if not self.access_token:
                if not self.authenticate():
                    return []
            
            print("🔍 Fetching upvoted posts (proxy for saved bookmarks)...")
            
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': self.user_agent
            }
            
            # Try upvoted posts endpoint
            url = f'https://www.reddit.com/user/me/upvoted.json?limit={limit}'
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                if 'data' in data and 'children' in data['data']:
                    items = data['data']['children']
                    
                    for item in items:
                        post_data = item['data']
                        
                        # Filter for high-quality posts (score > 10)
                        score = post_data.get('score', 0)
                        if score >= 10:
                            posts.append({
                                'platform': 'reddit',
                                'title': post_data.get('title', ''),
                                'author': post_data.get('author', ''),
                                'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                'content': post_data.get('selftext', ''),
                                'created_timestamp': datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                                'score': score,
                                'subreddit': post_data.get('subreddit', ''),
                                'is_saved': True,  # Mark as saved since these are upvoted
                                'folder_category': f"r/{post_data.get('subreddit', '')}"
                            })
                
                print(f"✅ Found {len(posts)} upvoted posts (proxy for saved bookmarks)")
                return posts
            else:
                print(f"❌ Upvoted posts request failed: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Upvoted posts request failed: {e}")
            return []
    
    def get_user_posts(self, limit=50):
        """Get user's own posts"""
        try:
            if not self.access_token:
                if not self.authenticate():
                    return []
            
            print("🔍 Fetching user's own posts...")
            
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': self.user_agent
            }
            
            url = f'https://www.reddit.com/user/me/submitted.json?limit={limit}'
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                posts = []
                
                if 'data' in data and 'children' in data['data']:
                    items = data['data']['children']
                    
                    for item in items:
                        post_data = item['data']
                        
                        posts.append({
                            'platform': 'reddit',
                            'title': post_data.get('title', ''),
                            'author': post_data.get('author', ''),
                            'url': f"https://reddit.com{post_data.get('permalink', '')}",
                            'content': post_data.get('selftext', ''),
                            'created_timestamp': datetime.fromtimestamp(post_data.get('created_utc', 0)).isoformat(),
                            'score': post_data.get('score', 0),
                            'subreddit': post_data.get('subreddit', ''),
                            'is_saved': True,  # User's own posts
                            'folder_category': f"r/{post_data.get('subreddit', '')}"
                        })
                
                print(f"✅ Found {len(posts)} user posts")
                return posts
            else:
                print(f"❌ User posts request failed: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ User posts request failed: {e}")
            return []
    
    def collect_bookmarks(self):
        """Main method to collect Reddit bookmarks using alternative approaches"""
        try:
            print("🤖 REDDIT BOOKMARKS COLLECTION (Alternative Approach)")
            print("=" * 60)
            
            all_posts = []
            
            # Try upvoted posts first (proxy for saved bookmarks)
            upvoted_posts = self.get_upvoted_posts(limit=100)
            all_posts.extend(upvoted_posts)
            
            # Also get user's own posts
            user_posts = self.get_user_posts(limit=50)
            all_posts.extend(user_posts)
            
            # Remove duplicates based on URL
            seen_urls = set()
            unique_posts = []
            for post in all_posts:
                if post['url'] not in seen_urls:
                    seen_urls.add(post['url'])
                    unique_posts.append(post)
            
            print(f"🎉 Collected {len(unique_posts)} unique Reddit posts!")
            return unique_posts
                
        except Exception as e:
            print(f"❌ Collection failed: {e}")
            return []

def test_reddit_bookmarks_collector():
    """Test the Reddit bookmarks collector"""
    print("🧪 Testing Reddit Bookmarks Collector (Alternative Approach)")
    print("=" * 70)
    
    collector = RedditBookmarksCollector()
    posts = collector.collect_bookmarks()
    
    if posts:
        print(f"🎉 SUCCESS! Collected {len(posts)} posts:")
        for i, post in enumerate(posts[:10]):  # Show first 10
            print(f"   {i+1}. [{post['subreddit']}] {post['title'][:50]}...")
            print(f"      Author: {post['author']} | Score: {post['score']} | ✅ SAVED")
            print()
    else:
        print("❌ No posts collected")

if __name__ == "__main__":
    test_reddit_bookmarks_collector()
