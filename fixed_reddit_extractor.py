#!/usr/bin/env python3
"""
Fixed Reddit extractor that bypasses DNS issues
"""

import requests
import os
import json
from datetime import datetime
from dotenv import load_dotenv

class FixedRedditExtractor:
    """Reddit extractor that bypasses DNS issues with oauth.reddit.com"""
    
    def __init__(self):
        load_dotenv()
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.username = os.getenv('REDDIT_USERNAME')
        self.password = os.getenv('REDDIT_PASSWORD')
        self.user_agent = os.getenv('REDDIT_USER_AGENT')
        self.access_token = None
        
    def get_access_token(self):
        """Get access token using working endpoint"""
        try:
            print("🔍 Getting Reddit access token...")
            
            # Use working endpoint (www.reddit.com works)
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
                print(f"✅ Reddit token obtained: {self.access_token[:20]}...")
                return True
            else:
                print(f"❌ Token request failed: {auth_response.status_code}")
                print(f"Response: {auth_response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Token request failed: {e}")
            return False
    
    def get_saved_posts(self):
        """Get saved posts using working endpoints"""
        try:
            if not self.access_token:
                if not self.get_access_token():
                    return []
            
            print("🔍 Fetching Reddit saved posts...")
            
            # Try different endpoints that work
            endpoints = [
                'https://reddit.com/api/v1/me/saved',
                'https://www.reddit.com/api/v1/me/saved',
                'https://reddit.com/user/me/saved.json',
                'https://www.reddit.com/user/me/saved.json'
            ]
            
            headers = {
                'Authorization': f'bearer {self.access_token}',
                'User-Agent': self.user_agent
            }
            
            for endpoint in endpoints:
                try:
                    print(f"🔍 Trying endpoint: {endpoint}")
                    response = requests.get(endpoint, headers=headers, timeout=15)
                    
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
                                    'subreddit': post_data.get('subreddit', '')
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

def test_fixed_reddit():
    """Test the fixed Reddit extractor"""
    print("🧪 Testing Fixed Reddit Extractor")
    print("=" * 50)
    
    extractor = FixedRedditExtractor()
    posts = extractor.get_saved_posts()
    
    if posts:
        print(f"🎉 SUCCESS! Found {len(posts)} saved posts:")
        for i, post in enumerate(posts[:5]):  # Show first 5
            print(f"   {i+1}. {post['title'][:60]}...")
            print(f"      Author: {post['author']} | Score: {post['score']}")
            print()
    else:
        print("❌ No posts found")

if __name__ == "__main__":
    test_fixed_reddit()
