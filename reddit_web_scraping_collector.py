#!/usr/bin/env python3
"""
Reddit Bookmarks Collector - Web Scraping Approach
Since Reddit API access is restricted, we'll use web scraping as a fallback
"""

import requests
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from bs4 import BeautifulSoup

class RedditWebScrapingCollector:
    """Collect Reddit bookmarks using web scraping"""
    
    def __init__(self):
        load_dotenv()
        self.username = os.getenv('REDDIT_USERNAME')
        self.password = os.getenv('REDDIT_PASSWORD')
        self.session = requests.Session()
        
    def login_to_reddit(self):
        """Login to Reddit using web scraping"""
        try:
            print("🔍 Logging into Reddit via web scraping...")
            
            # Get login page
            login_url = 'https://www.reddit.com/login'
            response = self.session.get(login_url, timeout=15)
            
            if response.status_code != 200:
                print(f"❌ Failed to get login page: {response.status_code}")
                return False
            
            # Parse login form
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find CSRF token
            csrf_token = None
            csrf_input = soup.find('input', {'name': 'csrf_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            # Prepare login data
            login_data = {
                'username': self.username,
                'password': self.password,
                'dest': 'https://www.reddit.com/',
            }
            
            if csrf_token:
                login_data['csrf_token'] = csrf_token
            
            # Submit login
            login_response = self.session.post(
                'https://www.reddit.com/login',
                data=login_data,
                timeout=15
            )
            
            if login_response.status_code == 200:
                # Check if login was successful
                if 'logout' in login_response.text.lower() or self.username in login_response.text:
                    print(f"✅ Successfully logged in as {self.username}")
                    return True
                else:
                    print("❌ Login failed - invalid credentials or captcha")
                    return False
            else:
                print(f"❌ Login request failed: {login_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def get_saved_posts_via_scraping(self):
        """Get saved posts via web scraping"""
        try:
            if not self.login_to_reddit():
                return []
            
            print("🔍 Scraping saved posts...")
            
            # Try to access saved posts page
            saved_url = f'https://www.reddit.com/user/{self.username}/saved'
            response = self.session.get(saved_url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Look for post elements
                posts = []
                
                # Try different selectors for Reddit posts
                post_selectors = [
                    'div[data-testid="post-container"]',
                    'div.Post',
                    'div[data-click-id="body"]',
                    'div.thing'
                ]
                
                for selector in post_selectors:
                    post_elements = soup.select(selector)
                    if post_elements:
                        print(f"✅ Found {len(post_elements)} posts using selector: {selector}")
                        
                        for element in post_elements[:20]:  # Limit to 20 posts
                            try:
                                # Extract post data
                                title_elem = element.find('h3') or element.find('a', {'data-click-id': 'body'})
                                title = title_elem.get_text(strip=True) if title_elem else 'No title'
                                
                                author_elem = element.find('a', {'data-click-id': 'author'})
                                author = author_elem.get_text(strip=True) if author_elem else 'Unknown'
                                
                                # Get post URL
                                link_elem = element.find('a', {'data-click-id': 'body'})
                                post_url = link_elem.get('href') if link_elem else ''
                                if post_url and not post_url.startswith('http'):
                                    post_url = f'https://reddit.com{post_url}'
                                
                                # Get subreddit
                                subreddit_elem = element.find('a', {'data-click-id': 'subreddit'})
                                subreddit = subreddit_elem.get_text(strip=True) if subreddit_elem else 'Unknown'
                                
                                if title and title != 'No title':
                                    posts.append({
                                        'platform': 'reddit',
                                        'title': title,
                                        'author': author,
                                        'url': post_url,
                                        'content': title,  # Use title as content for now
                                        'created_timestamp': datetime.now().isoformat(),
                                        'score': 0,  # Can't easily get score from scraping
                                        'subreddit': subreddit.replace('r/', ''),
                                        'is_saved': True,
                                        'folder_category': subreddit
                                    })
                                    
                            except Exception as e:
                                print(f"⚠️ Error parsing post: {e}")
                                continue
                        
                        break  # Found posts with this selector
                
                print(f"✅ Scraped {len(posts)} saved posts")
                return posts
            else:
                print(f"❌ Failed to access saved posts: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
            return []
    
    def collect_bookmarks(self):
        """Main method to collect Reddit bookmarks using web scraping"""
        try:
            print("🤖 REDDIT BOOKMARKS COLLECTION (Web Scraping)")
            print("=" * 60)
            
            posts = self.get_saved_posts_via_scraping()
            
            if posts:
                print(f"🎉 Collected {len(posts)} saved posts via web scraping!")
                return posts
            else:
                print("📭 No saved posts found via web scraping")
                return []
                
        except Exception as e:
            print(f"❌ Collection failed: {e}")
            return []

def test_reddit_web_scraping():
    """Test the Reddit web scraping collector"""
    print("🧪 Testing Reddit Web Scraping Collector")
    print("=" * 50)
    
    collector = RedditWebScrapingCollector()
    posts = collector.collect_bookmarks()
    
    if posts:
        print(f"🎉 SUCCESS! Collected {len(posts)} posts:")
        for i, post in enumerate(posts[:10]):  # Show first 10
            print(f"   {i+1}. [{post['subreddit']}] {post['title'][:50]}...")
            print(f"      Author: {post['author']} | ✅ SAVED")
            print()
    else:
        print("❌ No posts collected")

if __name__ == "__main__":
    test_reddit_web_scraping()
