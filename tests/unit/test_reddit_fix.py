#!/usr/bin/env python3
"""
Fixed Reddit extractor that uses working endpoints
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def get_reddit_token():
    """Get Reddit access token using working endpoint"""
    try:
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        user_agent = os.getenv('REDDIT_USER_AGENT')
        
        # Use working endpoint
        auth_url = 'https://www.reddit.com/api/v1/access_token'
        auth_data = {'grant_type': 'client_credentials'}
        
        auth_response = requests.post(
            auth_url,
            data=auth_data,
            auth=(client_id, client_secret),
            headers={'User-Agent': user_agent},
            timeout=10
        )
        
        if auth_response.status_code == 200:
            token_data = auth_response.json()
            return token_data['access_token']
        else:
            print(f'❌ Token request failed: {auth_response.status_code}')
            return None
            
    except Exception as e:
        print(f'❌ Token request failed: {e}')
        return None

def get_reddit_saved_posts():
    """Get saved posts using working Reddit API"""
    try:
        token = get_reddit_token()
        if not token:
            return []
        
        user_agent = os.getenv('REDDIT_USER_AGENT')
        
        # Use working endpoint (without www)
        api_url = 'https://reddit.com/api/v1/me/saved'
        headers = {
            'Authorization': f'bearer {token}',
            'User-Agent': user_agent
        }
        
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            posts = []
            
            for item in data.get('data', {}).get('children', []):
                post_data = item['data']
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
            
            print(f'✅ Found {len(posts)} Reddit saved posts!')
            return posts
        else:
            print(f'❌ API call failed: {response.status_code}')
            return []
            
    except Exception as e:
        print(f'❌ Reddit API call failed: {e}')
        return []

def test_reddit_fix():
    """Test the Reddit fix"""
    print('🔧 Testing Reddit fix...')
    
    load_dotenv()
    
    posts = get_reddit_saved_posts()
    
    if posts:
        print(f'✅ Success! Found {len(posts)} saved posts:')
        for i, post in enumerate(posts[:5]):  # Show first 5
            print(f'   {i+1}. {post["title"][:50]}...')
    else:
        print('❌ No posts found')

if __name__ == "__main__":
    test_reddit_fix()
