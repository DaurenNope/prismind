#!/usr/bin/env python3
"""
Reddit OAuth2 Setup Script
This will help you get Reddit authentication working properly.
"""

import praw
import requests
import urllib.parse
import webbrowser
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def setup_reddit_oauth():
    """Setup Reddit OAuth2 authentication"""
    
    reddit_client_id = os.getenv('REDDIT_CLIENT_ID')
    reddit_client_secret = os.getenv('REDDIT_CLIENT_SECRET')
    reddit_user_agent = os.getenv('REDDIT_USER_AGENT', 'bookmarker/1.0 by /u/44zxc')
    
    print("🔧 Reddit OAuth2 Setup")
    print("=" * 50)
    
    # Step 1: Generate OAuth2 URL
    oauth_url = (
        'https://www.reddit.com/api/v1/authorize?'
        f'client_id={reddit_client_id}&'
        'response_type=code&'
        'state=bookmarker_auth&'
        'redirect_uri=http://localhost:8080&'
        'duration=permanent&'
        'scope=identity,read,save,history'
    )
    
    print(f"1. Click this URL to authorize the app:")
    print(f"   {oauth_url}")
    print()
    print("2. Log in to Reddit and click 'Allow'")
    print("3. You'll be redirected to localhost:8080 with a code")
    print("4. Copy the code from the URL (after 'code=')")
    print()
    
    # Try to open the URL automatically
    try:
        webbrowser.open(oauth_url)
        print("✅ Opened browser automatically")
    except:
        print("❌ Could not open browser automatically")
        print("   Please copy and paste the URL above")
    
    print()
    print("5. Paste the authorization code here:")
    auth_code = input("Authorization code: ").strip()
    
    if not auth_code:
        print("❌ No authorization code provided")
        return None
    
    # Step 2: Exchange code for access token
    print("\n🔄 Exchanging code for access token...")
    
    token_url = 'https://www.reddit.com/api/v1/access_token'
    
    data = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': 'http://localhost:8080'
    }
    
    auth = (reddit_client_id, reddit_client_secret)
    headers = {'User-Agent': reddit_user_agent}
    
    try:
        response = requests.post(token_url, data=data, auth=auth, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            
            print("✅ Successfully got access token!")
            print(f"   Access token: {access_token[:20]}...")
            print(f"   Refresh token: {refresh_token[:20]}...")
            
            # Step 3: Test the access token
            print("\n🧪 Testing access token...")
            
            reddit = praw.Reddit(
                client_id=reddit_client_id,
                client_secret=reddit_client_secret,
                user_agent=reddit_user_agent,
                access_token=access_token,
                refresh_token=refresh_token
            )
            
            user = reddit.user.me()
            print(f"✅ Successfully authenticated as: {user.name}")
            
            # Test saved posts
            saved_posts = list(reddit.user.me().saved(limit=5))
            print(f"✅ Found {len(saved_posts)} saved posts!")
            
            if saved_posts:
                print("\n📋 Sample saved posts:")
                for i, post in enumerate(saved_posts[:3], 1):
                    if hasattr(post, 'title'):
                        print(f"   {i}. {post.title[:60]}...")
                    else:
                        print(f"   {i}. Comment by {post.author}")
            
            # Save tokens to .env file
            print("\n💾 Saving tokens to .env file...")
            
            # Read current .env file
            env_content = ""
            if os.path.exists('.env'):
                with open('.env', 'r') as f:
                    env_content = f.read()
            
            # Add or update tokens
            lines = env_content.split('\n')
            updated_lines = []
            token_added = False
            
            for line in lines:
                if line.startswith('REDDIT_ACCESS_TOKEN='):
                    updated_lines.append(f'REDDIT_ACCESS_TOKEN={access_token}')
                    token_added = True
                elif line.startswith('REDDIT_REFRESH_TOKEN='):
                    updated_lines.append(f'REDDIT_REFRESH_TOKEN={refresh_token}')
                else:
                    updated_lines.append(line)
            
            if not token_added:
                updated_lines.append(f'REDDIT_ACCESS_TOKEN={access_token}')
                updated_lines.append(f'REDDIT_REFRESH_TOKEN={refresh_token}')
            
            # Write back to .env file
            with open('.env', 'w') as f:
                f.write('\n'.join(updated_lines))
            
            print("✅ Tokens saved to .env file")
            print("\n🎉 Reddit OAuth2 setup complete!")
            print("   You can now use Reddit authentication in your app")
            
            return {
                'access_token': access_token,
                'refresh_token': refresh_token,
                'reddit': reddit
            }
            
        else:
            print(f"❌ Failed to get access token: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error during token exchange: {e}")
        return None

if __name__ == "__main__":
    setup_reddit_oauth()
