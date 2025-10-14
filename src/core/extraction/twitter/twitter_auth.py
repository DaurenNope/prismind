"""
Twitter authentication module for Playwright-based extractor
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import Browser, Page

logger = logging.getLogger(__name__)


class TwitterAuth:
    """Handles Twitter authentication using cookies and login"""
    
    def __init__(self, username: str, password: str = None, cookie_file: str = None):
        self.username = username
        self.password = password
        self.cookie_file = cookie_file or f"config/twitter_cookies_{username}.json"
    
    def _load_cookies(self) -> Optional[List[Dict]]:
        """Load cookies from file if it exists"""
        try:
            cookie_path = Path(self.cookie_file)
            if cookie_path.exists():
                with open(cookie_path, 'r') as f:
                    cookies = json.load(f)
                    print(f"✅ Loaded {len(cookies)} cookies from {self.cookie_file}")
                    return cookies
            else:
                print(f"📁 No cookie file found at {self.cookie_file}")
                return None
        except Exception as e:
            print(f"⚠️ Error loading cookies: {e}")
            return None
    
    def _save_cookies(self, cookies: List[Dict]):
        """Save cookies to file"""
        try:
            cookie_path = Path(self.cookie_file)
            cookie_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cookie_path, 'w') as f:
                json.dump(cookies, f, indent=2)
            print(f"✅ Saved {len(cookies)} cookies to {self.cookie_file}")
        except Exception as e:
            print(f"⚠️ Could not save cookies: {e}")
    
    async def _try_cookie_authentication(self, page: Page) -> bool:
        """Try to authenticate using existing cookies"""
        try:
            cookies = self._load_cookies()
            if not cookies:
                return False
            
            # Add cookies to the page
            await page.context.add_cookies(cookies)
            print(f"🍪 Added {len(cookies)} cookies to browser context")
            
            # Navigate to X.com home to test if cookies work
            await page.goto('https://x.com/home', wait_until='domcontentloaded', timeout=15000)
            await page.wait_for_timeout(3000)
            
            # Check if we're logged in by looking for compose button or profile elements
            try:
                # Look for compose button (indicates logged in)
                compose_button = await page.query_selector('[data-testid="SideNav_NewTweet_Button"]')
                if compose_button:
                    print("✅ Cookie authentication successful - found compose button")
                    return True
                
                # Alternative check: look for profile elements
                profile_elements = await page.query_selector_all('[data-testid="AppTabBar_Profile_Link"]')
                if profile_elements:
                    print("✅ Cookie authentication successful - found profile elements")
                    return True
                
                # Check if we're redirected to login page
                current_url = page.url
                if 'login' in current_url or 'i/flow' in current_url:
                    print("❌ Cookies invalid - redirected to login page")
                    return False
                
                print("⚠️ Cookie authentication unclear - proceeding with login")
                return False
                
            except Exception as e:
                print(f"⚠️ Error checking authentication status: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Cookie authentication failed: {e}")
            return False
    
    async def authenticate_with_password(self, page: Page, max_retries: int = 3) -> bool:
        """Authenticate using username and password"""
        if not self.password:
            print("❌ No password provided for authentication")
            return False
        
        for attempt in range(max_retries):
            try:
                print(f"🔐 Attempting password authentication (attempt {attempt + 1}/{max_retries})...")
                
                # Navigate to login page
                await page.goto('https://x.com/login', wait_until='domcontentloaded', timeout=20000)
                await page.wait_for_timeout(3000)
                
                # Step 1: Enter username
                username_input = await page.wait_for_selector('input[autocomplete="username"]', timeout=10000)
                await username_input.fill(self.username)
                await page.wait_for_timeout(1000)
                
                # Click "Next" button
                next_button = await page.wait_for_selector('[role="button"]:has-text("Next")', timeout=5000)
                await next_button.click()
                await page.wait_for_timeout(2000)
                
                # Step 2: Enter password
                password_input = await page.wait_for_selector('input[name="password"]', timeout=10000)
                await password_input.fill(self.password)
                await page.wait_for_timeout(1000)
                
                # Click "Log in" button
                login_button = await page.wait_for_selector('[data-testid="LoginForm_Login_Button"]', timeout=5000)
                await login_button.click()
                await page.wait_for_timeout(5000)
                
                # Check if login was successful
                current_url = page.url
                if 'home' in current_url or 'i/bookmarks' in current_url:
                    print("✅ Password authentication successful")
                    
                    # Save cookies for future use
                    cookies = await page.context.cookies()
                    self._save_cookies(cookies)
                    
                    return True
                else:
                    print(f"⚠️ Login may have failed - current URL: {current_url}")
                    if attempt < max_retries - 1:
                        await page.wait_for_timeout(2000)
                        continue
                    else:
                        return False
                        
            except Exception as e:
                print(f"❌ Authentication attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await page.wait_for_timeout(2000)
                    continue
                else:
                    return False
        
        return False
    
    async def authenticate(self, page: Page, max_retries: int = 3) -> bool:
        """Main authentication method - tries cookies first, then password"""
        # Try cookie authentication first
        if await self._try_cookie_authentication(page):
            return True
        
        # Fall back to password authentication
        if self.password:
            print("🔐 Falling back to password authentication...")
            return await self.authenticate_with_password(page, max_retries)
        else:
            print("❌ No authentication method available (no cookies or password)")
            return False





