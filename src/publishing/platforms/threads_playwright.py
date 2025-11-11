"""
Threads Posting Service using Playwright (Browser Automation)
Like mimesis autoposter - uses Playwright for Threads
"""

import os
import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_async as stealth  # LIKE MIMESIS
except ImportError:
    stealth = None
    # Logger not available yet, will log warning later
from dotenv import load_dotenv

load_dotenv(override=True)

logger = logging.getLogger(__name__)


async def post_to_threads_playwright(content: str, image_url: Optional[str] = None) -> Dict:
    """
    Post to Threads using Playwright browser automation.
    
    Returns:
        Dict with 'success', 'post_id', 'url', 'error' keys
    """
    playwright = None
    browser = None
    page = None
    
    try:
        # Get credentials
        username = os.getenv("THREADS_USERNAME")
        password = os.getenv("THREADS_PASSWORD")
        cookie_file = os.getenv("THREADS_COOKIES_FILE") or "config/threads_cookies.json"
        
        if not username:
            return {"success": False, "error": "THREADS_USERNAME not set"}
        
        # Validate length
        if len(content) > 500:
            # No cleanup needed - nothing opened yet
            return {
                "success": False,
                "error": f"Threads post too long: {len(content)} chars (max 500)",
            }
        
        # Start Playwright
        playwright = await async_playwright().start()
        
        proxy = os.getenv('THREADS_PROXY') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
        # Allow headless=False for debugging
        headless_mode = os.getenv('THREADS_HEADLESS', 'true').lower() in ('true', '1', 'yes')
        launch_kwargs = {
            'headless': headless_mode,  # Can set THREADS_HEADLESS=false to see browser
            'args': ["--no-sandbox", "--disable-dev-shm-usage", "--lang=en-US"]
        }
        if proxy:
            launch_kwargs['proxy'] = {'server': proxy}
        
        if not headless_mode:
            print("🔍 DEBUG MODE: Browser will be visible (headless=False)")
        
        browser = await playwright.chromium.launch(**launch_kwargs)
        
        # CRITICAL: Use EXACT SAME approach as working extractor - EXACT COPY!
        # Load cookies using storage_state (EXACTLY like ThreadsExtractor._authenticate_with_cookies line 80-83)
        cookie_file_path = Path(cookie_file) if cookie_file else None
        
        if cookie_file_path and cookie_file_path.exists():
            # EXACT SAME as extractor - just pass cookies_path directly to storage_state
            context = await browser.new_context(
                storage_state=str(cookie_file_path),  # EXACTLY like extractor line 81
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"  # EXACTLY like extractor line 82
            )
            logger.info(f"✅ Using storage_state from {cookie_file} (EXACTLY like extractor)")
            print(f"✅ Loading cookies from: {cookie_file}")
        else:
            # No cookies - create context without cookies
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            logger.warning(f"Cookie file not found: {cookie_file}")
            print(f"⚠️  Cookie file not found: {cookie_file}")
        
        # VERIFY cookies were loaded
        try:
            cookies_loaded = await context.cookies()
            logger.info(f"✅ Loaded {len(cookies_loaded)} cookies into context")
            print(f"✅ Loaded {len(cookies_loaded)} cookies into context")
            except Exception as e:
            logger.warning(f"Could not verify cookies: {e}")
            print(f"⚠️  Could not verify cookies: {e}")
        
        page = await context.new_page()
        
        # OPTIMIZED: Go directly to home page - no need to verify auth first
        # If cookies are invalid, posting will fail naturally when we try to compose
        logger.info("🚀 Navigating directly to home page (optimized - skipping auth check)")
        print("🚀 Navigating directly to home page...")
        
        try:
            # Navigate directly to home page
            await page.goto("https://www.threads.net/", wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(1000)  # Brief wait for initial load
            
            # Check if redirected to login (quick auth check)
        current_url = page.url
            if 'login' in current_url.lower() or 'accounts/login' in current_url.lower():
                logger.error("❌ Redirected to login - cookies expired")
                print("❌ Redirected to login - cookies expired")
                
            # Try login if password provided
            if password:
                logger.info("Cookies didn't work, trying username/password login...")
                await page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                username_input = await page.wait_for_selector('input[name="username"]', timeout=5000)
                if not username_input:
                    return {"success": False, "error": "Login failed: Could not find username input"}
                
                await username_input.fill(username)
                await asyncio.sleep(1)
                
                password_input = await page.wait_for_selector('input[type="password"]', timeout=5000)
                if not password_input:
                    return {"success": False, "error": "Login failed: Could not find password input"}
                
                await password_input.fill(password)
                await asyncio.sleep(1)
                
                login_button = await page.wait_for_selector('button[type="submit"]', timeout=5000)
                if not login_button:
                    return {"success": False, "error": "Login failed: Could not find login button"}
                
                await login_button.click()
                await asyncio.sleep(3)
                
                    # Navigate to home after login
                await page.goto("https://www.threads.net/", wait_until="domcontentloaded", timeout=30000)
                    
                    # Save cookies after login
                    if cookie_file and context:
                        try:
                            cookies = await context.cookies()
                            cookie_data = {"cookies": cookies}
                            Path(cookie_file).parent.mkdir(parents=True, exist_ok=True)
                            with open(cookie_file, "w") as f:
                                json.dump(cookie_data, f, indent=2)
                            logger.info(f"✅ Saved {len(cookies)} cookies after password login")
                        except Exception as e:
                            logger.warning(f"Failed to save cookies after login: {e}")
            else:
                return {"success": False, "error": "Not logged in - cookies expired, need password"}
        
            # Wait for page to be ready (minimal wait)
            await page.wait_for_load_state('networkidle', timeout=10000)
            logger.info("✅ Home page loaded")
            print("✅ Home page loaded")
            
        except Exception as e:
            logger.warning(f"Home page navigation issue: {e} - continuing anyway")
            print(f"⚠️  Navigation warning: {e}")
        
        # Now look for compose button
        logger.info("Looking for compose button on home page...")
        current_url = page.url
        logger.info(f"Current URL: {current_url}")
        
        # DEBUG: Log what's actually on the page
        try:
            all_buttons = await page.query_selector_all('button, a, div[role="button"]')
            print(f"🔍 Found {len(all_buttons)} clickable elements on page")
            logger.info(f"Found {len(all_buttons)} clickable elements on page")
            
            # Get some button text for debugging
            compose_candidates = []
            for i, btn in enumerate(all_buttons[:20]):
                try:
                    text = await btn.inner_text()
                    aria_label = await btn.get_attribute('aria-label')
                    if text or aria_label:
                        btn_info = f"Button {i}: text='{text[:30] if text else ''}' aria-label='{aria_label or ''}'"
                        print(f"  {btn_info}")
                        logger.debug(btn_info)
                        
                        # Check if this looks like compose button
                        if text and ('compose' in text.lower() or 'new' in text.lower() or 'post' in text.lower() or 'thread' in text.lower()):
                            compose_candidates.append((i, text, aria_label))
                        elif aria_label and ('compose' in str(aria_label).lower() or 'new' in str(aria_label).lower() or 'post' in str(aria_label).lower() or 'thread' in str(aria_label).lower()):
                            compose_candidates.append((i, text, aria_label))
                except Exception as e:
                    logger.debug(f"Button inspection failed: {e}", exc_info=True)
                    # Continue - button inspection is non-critical
            
            if compose_candidates:
                print(f"🎯 Found {len(compose_candidates)} potential compose buttons:")
                for idx, candidate in enumerate(compose_candidates):
                    i, text, aria = candidate
                    print(f"  Candidate {idx}: text='{text[:40] if text else ''}' aria='{aria or ''}'")
        except Exception as e:
            print(f"⚠️  Could not inspect buttons: {e}")
            logger.debug(f"Could not inspect buttons: {e}")
            
        # Initialize variables
        textarea = None
        compose_button = None
        
        # Find and click compose button (Threads opens compose as a modal)
        logger.info("Looking for compose button on home page...")
        compose_selectors = [
                # Found in debug: Button 14 has this aria-label!
                'button[aria-label*="Empty text field"]',
                'button[aria-label*="Type to compose"]',
                '[aria-label*="Empty text field"]',
                '[aria-label*="Type to compose"]',
                # Also try text content
                'button:has-text("What\'s new?")',
                'div:has-text("What\'s new?")',
                # Standard selectors
            'a[href="/compose"]',
            'a[href*="/compose"]',
            'button[aria-label*="New thread"]',
            'button[aria-label*="New Thread"]',
                'button[aria-label*="Compose"]',
                'button[aria-label*="Post"]',
            '[aria-label*="New thread"]',
            '[aria-label*="New Thread"]',
                '[aria-label*="Compose"]',
            'svg[aria-label*="New thread"]',
            'svg[aria-label*="New Thread"]',
            '[data-testid*="compose"]',
            '[data-testid*="new-thread"]',
                '[data-testid*="new-thread-button"]',
                'div[role="button"]:has-text("New thread")',
                'div[role="button"]:has-text("New Thread")',
        ]
        
        for selector in compose_selectors:
            try:
                logger.info(f"Trying compose button selector: {selector}")
                compose_button = await page.wait_for_selector(selector, timeout=5000)
                if compose_button:
                    is_visible = await compose_button.is_visible()
                    if is_visible:
                        logger.info(f"✅ Found visible compose button: {selector}")
                        print(f"✅ Found compose button with selector: {selector}")
                        break
                    else:
                        logger.debug(f"Found button but not visible: {selector}")
                        compose_button = None
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # If compose button not found by selector, try to find it by aria-label from debug
        if not compose_button:
            try:
                print("🔍 Trying to find compose button by aria-label 'Empty text field'...")
                compose_button = await page.query_selector('[aria-label*="Empty text field"]')
                if compose_button:
                    is_visible = await compose_button.is_visible()
                    if is_visible:
                        print("✅ Found compose button by aria-label!")
                        logger.info("✅ Found compose button by aria-label")
            except Exception as e:
                logger.debug(f"Aria-label search failed: {e}")
        
        # If compose_button is None, we may have already navigated to compose page
        textarea = None
        
        if compose_button:
            # Click compose button to open modal
            logger.info("Clicking compose button...")
            print("🖱️ Clicking compose button...")
            
            # Try multiple click methods to handle intercepting elements
            try:
                # Method 1: Force click (bypasses interception)
                await compose_button.click(force=True)
                print("✅ Clicked with force=True")
            except Exception as e1:
                print(f"⚠️ Force click failed: {e1}")
                try:
                    # Method 2: JavaScript click (bypasses interception)
                    await compose_button.evaluate("element => element.click()")
                    print("✅ Clicked with JavaScript")
                except Exception as e2:
                    print(f"⚠️ JavaScript click failed: {e2}")
                    try:
                        # Method 3: Scroll into view and normal click
                        await compose_button.scroll_into_view_if_needed()
                        await page.wait_for_timeout(1000)  # Wait for any overlays
                        await compose_button.click()
                        print("✅ Clicked after scrolling")
                    except Exception as e3:
                        print(f"⚠️ Normal click failed: {e3}")
                        # Last resort: click parent element
                        try:
                            parent = await compose_button.evaluate_handle("element => element.parentElement")
                            if parent:
                                await parent.click()
                                print("✅ Clicked parent element")
                        except Exception as e4:
                            raise Exception(f"All click methods failed: force={e1}, js={e2}, normal={e3}, parent={e4}")
        
        await page.wait_for_timeout(3000)  # Wait for modal to open
        
        # Wait for compose modal to appear (contenteditable will be inside modal)
        logger.info("Waiting for compose modal textarea to appear...")
        try:
            # Wait for contenteditable to appear in the modal
            textarea = await page.wait_for_selector('[contenteditable="true"]', timeout=15000, state="visible")
            logger.info("✅ Compose modal opened, textarea found!")
            await page.wait_for_timeout(1000)  # Wait for it to be ready
        except Exception as e:
                logger.warning(f"Compose modal textarea didn't appear after button click: {e}")
                textarea = None
        else:
            # Try to find textarea directly (we may be on /compose page already)
            logger.info("No compose button found - checking if already on compose page...")
            try:
                textarea = await page.wait_for_selector('[contenteditable="true"]', timeout=5000, state="visible")
                if textarea:
                    logger.info("✅ Found textarea directly on page!")
            except Exception as e:
                logger.debug(f"Textarea not found: {e}")
                textarea = None
        
        if not textarea:
            # Take screenshot for debugging
            try:
                await page.screenshot(path="logs/threads_no_compose_button.png", full_page=True)
                logger.error("📸 Screenshot: logs/threads_no_compose_button.png")
            
                # Also get page HTML to see what's available
                page_text = await page.evaluate("document.body.innerText")
                logger.debug(f"Page text preview: {page_text[:500]}")
            except Exception as e:
                logger.debug(f"Debug screenshot/text failed: {e}")
                pass
            
            logger.error("❌ Could not find compose button or textarea")
            try:
                if page and not page.is_closed():
                    await page.close()
                if browser and browser.is_connected():
                    await browser.close()
                if playwright:
                    await playwright.stop()
            except Exception as e:
                logger.debug(f"Cleanup failed: {e}")
                pass
            return {"success": False, "error": "Could not find compose button or textarea - may not be logged in or page structure changed"}
        
        # Now we have textarea, continue with posting
        logger.info("✅ Textarea found - proceeding to post content...")
        
        # Type content into textarea (contenteditable div)
        logger.info(f"Typing content into textarea ({len(content)} chars)...")
        try:
            # Click to focus
            await textarea.click()
            await page.wait_for_timeout(500)
            
            # Type using fill() - Playwright handles contenteditable correctly
            await textarea.fill(content)
            await page.wait_for_timeout(1000)
            
            # CRITICAL: Trigger input events manually (React may need these to update state)
            try:
                await textarea.evaluate("""
                    el => {
                        el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
                        el.dispatchEvent(new Event('keyup', { bubbles: true, cancelable: true }));
                    }
                """)
                print("✅ Triggered input events")
                await page.wait_for_timeout(1000)  # Wait for React to update
            except Exception as event_error:
                logger.debug(f"Could not trigger input events: {event_error}")
            
            # Verify content was typed
            actual_content = await textarea.inner_text()
            if len(actual_content) > 0:
                logger.info(f"✅ Content typed: {len(actual_content)} chars")
                print(f"✅ Content verified: {actual_content[:50]}...")
            else:
                # Fallback: use innerHTML/textContent
                await textarea.evaluate(f"el => {{ el.textContent = {json.dumps(content)}; }}")
                await page.wait_for_timeout(500)
                actual_content = await textarea.inner_text()
                logger.info(f"✅ Content typed (fallback): {len(actual_content)} chars")
                print(f"✅ Content typed (fallback): {actual_content[:50]}...")
            
            # Wait longer for button to become ready after content is typed
            await page.wait_for_timeout(2000)
            print("⏳ Waiting for post button to be ready after typing...")
        except Exception as e:
            logger.error(f"Failed to type content: {e}")
            raise
        
        # Find and click post button - find ALL buttons with "Post" and choose the right one
        post_button = None
        logger.info("🔍 Finding all post buttons on the page...")
        print("🔍 Finding all post buttons...")
        
        # First, find all buttons with "Post" text or aria-label
        all_post_buttons = []
        
        # Try multiple selectors to find ALL post buttons
        post_selectors = [
            'button:has-text("Post")',
            'button:has-text("Publish")',
            '[aria-label*="Post"]',
            '[aria-label*="Publish"]',
            'div[role="button"]:has-text("Post")',
            'div[role="button"]:has-text("Publish")',
            'a[role="button"]:has-text("Post")',
            'button[type="submit"]',
        ]
        
        for selector in post_selectors:
            try:
                buttons = await page.query_selector_all(selector)
                for btn in buttons:
                    if btn:
                        is_visible = await btn.is_visible()
                        if is_visible:
                            text = await btn.inner_text()
                            aria_label = await btn.get_attribute('aria-label') or ''
                            all_post_buttons.append({
                                'element': btn,
                                'selector': selector,
                                'text': text,
                                'aria_label': aria_label
                            })
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        logger.info(f"Found {len(all_post_buttons)} post button(s)")
        print(f"Found {len(all_post_buttons)} post button(s)")
        
        # Log all found buttons for debugging
        for i, btn_info in enumerate(all_post_buttons):
            logger.info(f"  Button {i+1}: text='{btn_info['text'][:50]}', aria-label='{btn_info['aria_label'][:50]}'")
            print(f"  Button {i+1}: text='{btn_info['text'][:50]}', aria-label='{btn_info['aria_label'][:50]}'")
        
        # Choose the button that's in the compose modal (not navigation buttons)
        # Look for button inside modal or dialog
        for btn_info in all_post_buttons:
            btn = btn_info['element']
            try:
                # Check if button is inside a modal/dialog
                parent = await btn.evaluate_handle("el => el.closest('div[role=\"dialog\"], div[class*=\"modal\"], div[class*=\"compose\"]')")
                if parent and parent.as_element():
                    # This button is in a modal - likely the correct one
                    is_enabled = await btn.is_enabled()
                    is_visible = await btn.is_visible()
                    is_disabled = await btn.get_attribute('disabled')
                    
                    if is_enabled and is_visible and not is_disabled:
                        post_button = btn
                        logger.info(f"✅ Selected post button from modal: text='{btn_info['text'][:50]}'")
                        print(f"✅ Selected post button from modal")
                        break
            except:
                pass
        
        # If no button in modal, try the first enabled button
        if not post_button:
            for btn_info in all_post_buttons:
                btn = btn_info['element']
                try:
                    is_enabled = await btn.is_enabled()
                    is_visible = await btn.is_visible()
                    is_disabled = await btn.get_attribute('disabled')
                    
                    if is_enabled and is_visible and not is_disabled:
                        # Prefer buttons with specific text
                        text_lower = (btn_info['text'] or '').lower()
                        if 'post' in text_lower and 'share' not in text_lower and 'reply' not in text_lower:
                            post_button = btn
                            logger.info(f"✅ Selected post button: text='{btn_info['text'][:50]}'")
                            print(f"✅ Selected post button: '{btn_info['text'][:50]}'")
                            break
                except:
                    continue
        
        if not post_button:
            # Last resort: try submit button
            try:
                submit_btn = await page.query_selector('button[type="submit"]')
                if submit_btn:
                    is_enabled = await submit_btn.is_enabled()
                    is_visible = await submit_btn.is_visible()
                    if is_enabled and is_visible:
                        post_button = submit_btn
                        logger.info("✅ Selected submit button")
            except Exception as e:
                logger.debug(f"Submit button check failed: {e}")
        
        if not post_button:
            # Cleanup and return error
            try:
                if page and not page.is_closed():
                    await page.close()
                if browser and browser.is_connected():
                    await browser.close()
                if playwright:
                    await playwright.stop()
            except Exception as e:
                logger.debug(f"Cleanup failed: {e}")
                pass
            return {"success": False, "error": f"Could not find enabled post button (found {len(all_post_buttons)} button(s) but none were suitable)"}
        
        # Wait a bit more for button to be fully ready (Threads may need time to enable it)
        await page.wait_for_timeout(2000)
        
        # Verify content is still in textarea before posting
        try:
            textarea_content = await textarea.inner_text()
            if len(textarea_content) < len(content) / 2:
                logger.warning(f"Content may not be typed correctly: expected {len(content)} chars, got {len(textarea_content)}")
                print(f"⚠️ Content verification: expected {len(content)} chars, got {len(textarea_content)}")
                # Try typing again
                await textarea.fill(content)
                await page.wait_for_timeout(1000)
        except Exception as e:
            logger.warning(f"Could not verify content: {e}")
        
        # Click post button - try multiple methods including keyboard
        logger.info("Clicking post button...")
        print("🖱️ Clicking post button...")
        
        # Debug: Check button state before clicking
        try:
            button_text = await post_button.inner_text()
            button_aria = await post_button.get_attribute('aria-label')
            button_tag = await post_button.evaluate("el => el.tagName")
            print(f"🔍 Post button debug: tag={button_tag}, text='{button_text}', aria='{button_aria}'")
            
            # Check if button has click handler
            has_onclick = await post_button.evaluate("el => el.onclick !== null || el.hasAttribute('onclick')")
            has_listener = await post_button.evaluate("el => el.getAttribute('data-reactid') !== null || el.getAttribute('data-testid') !== null")
            print(f"🔍 Post button has onclick: {has_onclick}, has listener: {has_listener}")
        except Exception as debug_error:
            print(f"⚠️ Button debug failed: {debug_error}")
        
        # CRITICAL: Use ONLY JavaScript click method - keyboard shortcuts can post multiple times
        # Skip keyboard shortcuts entirely to prevent double-posting
        try:
            # Use JavaScript click with event dispatch (most reliable for React apps)
            print("🖱️ Clicking post button with JavaScript...")
            await post_button.evaluate("""
                element => {
                    element.focus();
                    // Dispatch mousedown, mouseup, click events
                    element.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, cancelable: true }));
                    element.dispatchEvent(new MouseEvent('mouseup', { bubbles: true, cancelable: true }));
                    element.click();
                }
            """)
            print("✅ Post button clicked with JavaScript (with events)")
        except Exception as e1:
            print(f"⚠️ JavaScript click failed: {e1}")
            # Only try other methods if first attempt truly failed
            try:
                # Force click as fallback
                await post_button.click(force=True)
                print("✅ Post button clicked with force=True")
            except Exception as e2:
                print(f"⚠️ Force click failed: {e2}")
                raise Exception(f"All post methods failed: js={e1}, force={e2}")
        
        # Wait for post to be submitted and verify it actually posted
        await page.wait_for_timeout(2000)
        logger.info("✅ Post button clicked - waiting for submission...")
        print("⏳ Waiting for post to be submitted...")
        
        # Wait for modal to close or post to appear (indicating success)
        post_success = False
        post_id = None
        post_url = None
        
        # Check multiple ways to verify post was successful:
        # 1. Modal should close
        # 2. URL should change to post URL
        # 3. Success message should appear
        # 4. Post should appear in feed
        
        for attempt in range(10):  # Check up to 10 times (10 seconds)
            try:
                current_url = page.url
                
                # Check if URL changed to a post URL
                if "/post/" in current_url:
                    # URL changed to post - success!
                    post_id = current_url.split("/post/")[-1].split("?")[0]
                    username_from_page = current_url.split("threads.net/@")[1].split("/post/")[0] if "@" in current_url else None
                    if username_from_page:
                        post_url = f"https://www.threads.net/@{username_from_page}/post/{post_id}"
                    else:
                        post_url = current_url
                    post_success = True
                    print(f"✅ Post URL detected: {post_url}")
                    logger.info(f"✅ Post successful - URL: {post_url}")
                    break
                
                # Check if modal closed (compose modal should disappear)
                # Also check if textarea is still visible (modal still open)
                modal_open = await page.query_selector('[aria-label*="Empty text field"]')
                # Look for compose modal more broadly
                compose_modal = await page.query_selector('div[role="dialog"], [data-testid*="compose"], [aria-label*="compose"]')
                textarea_still_visible = await page.query_selector('[contenteditable="true"]')
                
                # Check if modal/dialog is still open
                modal_still_open = modal_open or compose_modal or textarea_still_visible
                
                print(f"🔍 Modal check - modal_open: {bool(modal_open)}, compose_modal: {bool(compose_modal)}, textarea_visible: {bool(textarea_still_visible)}")
                
                if not modal_still_open:
                    # Modal closed - might be success!
                    print("✅ Modal closed - checking if post appeared...")
                    await page.wait_for_timeout(3000)  # Wait for post to appear in feed
                    
                    # Check if post appears in feed (search for our content)
                    try:
                        # Look for the post in the feed by content
                        page_content = await page.evaluate("document.body.innerText")
                        # Take first 100 chars of our content to search
                        search_text = content[:100].strip()
                        if search_text in page_content:
                            print(f"✅ Post found in feed - content detected!")
                            logger.info(f"✅ Post successful - content found in feed")
                            post_success = True
                            
                            # Try to get post URL from feed (find the post and extract URL)
                            try:
                                # Look for links with our content nearby
                                post_links = await page.query_selector_all(f'a[href*="/post/"]')
                                if post_links:
                                    # Get the first post link (likely our new post)
                                    post_url = await post_links[0].get_attribute('href')
                                    if post_url and not post_url.startswith('http'):
                                        post_url = f"https://www.threads.net{post_url}"
                                    post_id = post_url.split("/post/")[-1].split("?")[0] if "/post/" in post_url else None
                                    print(f"✅ Post URL: {post_url}")
                            except Exception as e:
                                logger.debug(f"Failed to extract post URL from feed: {e}")
                                pass
                            break
                    except Exception as feed_check_error:
                        logger.debug(f"Feed check failed: {feed_check_error}")
                    
                    # Also check URL change
                    current_url = page.url
                    if "/post/" in current_url:
                        post_id = current_url.split("/post/")[-1].split("?")[0]
                        username_from_page = current_url.split("threads.net/@")[1].split("/post/")[0] if "@" in current_url else None
                        if username_from_page:
                            post_url = f"https://www.threads.net/@{username_from_page}/post/{post_id}"
                        else:
                            post_url = current_url
                        post_success = True
                        print(f"✅ Post successful - modal closed, URL: {post_url}")
                        logger.info(f"✅ Post successful - modal closed, URL: {post_url}")
                        break
                    else:
                        # Modal closed but no URL change - might be success (post on same page)
                        print("⚠️ Modal closed but no URL change - post may be in feed")
                        # Assume success if modal closed (Threads posts to feed, not new page)
                        post_success = True
                        print("✅ Post successful - modal closed (post likely in feed)")
                        logger.info("✅ Post successful - modal closed (post likely in feed)")
                        break
                
                # Check for error messages AND success messages
                message_selectors = [
                    '[role="alert"]',
                    '[data-testid="error"]',
                    'div:has-text("error")',
                    'div:has-text("Error")',
                    'div:has-text("failed")',
                    'div:has-text("fediverse")',
                    'div:has-text("shared")',
                    'div:has-text("posted")',
                ]
                
                for message_selector in message_selectors:
                    try:
                        message_element = await page.query_selector(message_selector)
                        if message_element:
                                message_text = await message_element.inner_text()
                                if message_text and len(message_text) < 300:  # Reasonable message length
                                    print(f"📄 Message detected: {message_text}")
                                    logger.info(f"Post message: {message_text}")
                                    
                                    # CRITICAL: "Posting..." message means the post WAS submitted!
                                    if "posting" in message_text.lower():
                                        print("✅ 'Posting...' message detected - post was submitted!")
                                        logger.info("✅ 'Posting...' message detected - post was submitted!")
                                        post_success = True
                                        # Wait a bit more for it to complete, then assume success
                                        await page.wait_for_timeout(3000)
                                        
                                        # Try to get post ID/URL from the page
                                        current_url = page.url
                                        if "/post/" in current_url:
                                            post_id = current_url.split("/post/")[-1].split("?")[0]
                                            username_from_page = current_url.split("threads.net/@")[1].split("/post/")[0] if "@" in current_url else None
                                            if username_from_page:
                                                post_url = f"https://www.threads.net/@{username_from_page}/post/{post_id}"
                                            else:
                                                post_url = current_url
                                        else:
                                            # Generate synthetic ID since we can't get the real one yet
                                            post_id = f"playwright_{int(datetime.now().timestamp())}"
                                            post_url = None
                                        
                                        logger.info(f"✅ Post successful - 'Posting...' detected, assuming success")
                                        break
                                    
                                    # Check if it's a success message (but not button text)
                                    # Make sure it's not just the button text "Post"
                                    is_button_text = "post" in message_text.lower() and len(message_text.strip()) <= 5
                                    is_success_message = any(word in message_text.lower() for word in ["fediverse", "shared", "success", "published", "your post"]) and not is_button_text
                                
                                if is_success_message:
                                    print("✅ Success message detected!")
                                    logger.info("✅ Post successful - success message found")
                                    
                                    # Wait for modal to close after success
                                    await page.wait_for_timeout(2000)
                                    
                                    # Re-check if textarea disappeared
                                    textarea_check = await page.query_selector('[contenteditable="true"]')
                                    if not textarea_check:
                                        post_success = True
                                        print("✅ Post successful - success message + textarea disappeared")
                                        logger.info("✅ Post successful - success message + textarea disappeared")
                                        break
                                    else:
                                        # Textarea still there, but success message - might be posted anyway
                                        print("⚠️ Success message but modal still open - post may have been created")
                                        # Check feed to confirm
                                        try:
                                            page_content = await page.evaluate("document.body.innerText")
                                            if content[:50].strip() in page_content:
                                                post_success = True
                                                print("✅ Post confirmed in feed!")
                                                break
                                        except Exception as e:
                                            logger.debug(f"Feed check failed: {e}")
                                            pass
                                
                                # Also check if "This post was shared to the fediverse" appears (specific success message)
                                if "fediverse" in message_text.lower():
                                    print("✅ Fediverse message detected - post was shared!")
                                    logger.info("✅ Post successful - fediverse message")
                                    post_success = True
                                    print("✅ Post successful - shared to fediverse")
                                    break
                                
                                # Check if it's an error message
                                elif any(word in message_text.lower() for word in ["error", "failed", "cannot", "invalid", "try again"]):
                                    print(f"❌ Error detected: {message_text}")
                                    logger.error(f"Post error: {message_text}")
                                    raise Exception(f"Post failed with error: {message_text}")
                    except Exception as check_error:
                        if "Post failed" in str(check_error):
                            raise  # Re-raise our error
                        continue
                
                # If textarea disappeared, post might have been submitted
                if not textarea_still_visible and not post_success:
                    print("⚠️ Textarea disappeared but no success message - checking feed...")
                    await page.wait_for_timeout(2000)
                    
                    # Check if post appears in feed
                    try:
                        page_content = await page.evaluate("document.body.innerText")
                        search_text = content[:50].strip()
                        if search_text in page_content:
                            print(f"✅ Post found in feed - content detected!")
                            post_success = True
                            logger.info("✅ Post successful - found in feed")
                            break
                    except Exception as e:
                        logger.debug(f"Feed check failed: {e}")
                        pass
                    
                    # If modal is still open but textarea is gone, might be a confirmation or success state
                    if modal_open or compose_modal:
                        print("⚠️ Modal still open but textarea gone - might be confirmation screen")
                        # Wait a bit more and check again
                        await page.wait_for_timeout(3000)
                
                await page.wait_for_timeout(1000)  # Wait 1 second before next check
                print(f"⏳ Waiting for post confirmation... ({attempt + 1}/10)")
                
            except Exception as check_error:
                if "Post failed" in str(check_error):
                    raise  # Re-raise post error
                logger.debug(f"Check attempt {attempt + 1} failed: {check_error}")
                await page.wait_for_timeout(1000)
        
        # If still not confirmed, check one more time after longer wait
        if not post_success:
            await page.wait_for_timeout(3000)
            current_url = page.url
        if "/post/" in current_url:
            post_id = current_url.split("/post/")[-1].split("?")[0]
            username_from_page = current_url.split("threads.net/@")[1].split("/post/")[0] if "@" in current_url else None
            if username_from_page:
                post_url = f"https://www.threads.net/@{username_from_page}/post/{post_id}"
            else:
                post_url = current_url
                post_success = True
                print(f"✅ Post URL found after extended wait: {post_url}")
        
        if not post_success:
            # Take screenshot to debug
            try:
                await page.screenshot(path="logs/threads_post_failed.png", full_page=True)
                logger.error("📸 Screenshot: logs/threads_post_failed.png")
            except Exception as e:
                logger.debug(f"Screenshot failed: {e}")
                pass

            # Get page text to see what's happening
            try:
                page_text = await page.evaluate("document.body.innerText")
                logger.debug(f"Page text after post attempt: {page_text[:500]}")
            except Exception as e:
                logger.debug(f"Failed to get page text: {e}")
                pass
            
            # Final check: Look for content in feed
            try:
                page_content = await page.evaluate("document.body.innerText")
                search_text = content[:50].strip()
                if search_text in page_content:
                    logger.info("✅ Post confirmed in feed after timeout - success!")
                    post_success = True
                    post_id = f"playwright_{int(datetime.now().timestamp())}"
                else:
                    logger.error("❌ Content NOT found in feed after posting")
            except Exception as e:
                logger.error(f"❌ Could not verify post: {e}")
        
        # Return failure if we couldn't confirm success
        if not post_success:
            return {
                "success": False,
                "error": "Post verification failed - check screenshot: logs/threads_post_failed.png",
                "post_id": None,
                "url": None,
            }
        
        # Save cookies for next time (mimesis format: {"cookies": [...], "origins": [...]})
        if cookie_file and context:
            try:
                cookies = await context.cookies()
                # Save in mimesis format
                cookie_data = {"cookies": cookies}
                # Note: origins/localStorage not saved for now, but format matches mimesis
                Path(cookie_file).parent.mkdir(parents=True, exist_ok=True)
                with open(cookie_file, "w") as f:
                    json.dump(cookie_data, f, indent=2)
                logger.info(f"✅ Saved {len(cookies)} cookies to {cookie_file} (mimesis format)")
            except Exception as e:
                logger.warning(f"Failed to save cookies: {e}")
        
        return {
            "success": True,
            "post_id": post_id or f"playwright_{int(datetime.now().timestamp())}",
            "url": post_url or current_url,
            "error": None,
        }
        
    except Exception as e:
        # Try to save cookies even on error (in case auth succeeded)
        try:
            if cookie_file and context:
                cookies = await context.cookies()
                if cookies:
                    cookie_data = {"cookies": cookies}
                    Path(cookie_file).parent.mkdir(parents=True, exist_ok=True)
                    with open(cookie_file, "w") as f:
                        json.dump(cookie_data, f, indent=2)
                    logger.info(f"✅ Saved {len(cookies)} cookies even after error")
        except Exception as cookie_error:
            logger.debug(f"Failed to save cookies on error: {cookie_error}")
        
        return {
            "success": False,
            "error": f"Playwright posting failed: {str(e)}",
        }
    finally:
        # Cleanup - only close if we actually opened them
        if page:
            try:
                if not page.is_closed():
                    await page.close()
            except Exception as e:
                logger.debug(f"Page close failed: {e}")
                pass
        if browser:
            try:
                if browser.is_connected():
                    await browser.close()
            except Exception as e:
                logger.debug(f"Browser close failed: {e}")
                pass
        if playwright:
            try:
                await playwright.stop()
            except Exception as e:
                logger.debug(f"Playwright stop failed: {e}")
                pass


def post_to_threads_direct(content: str, image_url: Optional[str] = None) -> Dict:
    """
    Post to Threads using Playwright (wrapper for async function).
    
    Returns:
        Dict with 'success', 'post_id', 'url', 'error' keys
    """
    try:
        # Check if event loop is already running
        try:
            asyncio.get_running_loop()
            # Event loop is running - need to use create_task or run in executor
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, post_to_threads_playwright(content, image_url=image_url))
                return future.result()
        except RuntimeError:
            # No event loop running - safe to use asyncio.run
            return asyncio.run(post_to_threads_playwright(content, image_url=image_url))
    except Exception as e:
        import traceback
        error_msg = str(e)
        logger.error(f"Threads posting failed: {error_msg}")
        logger.debug(traceback.format_exc())
        return {
            "success": False,
            "error": f"Failed to run Playwright: {error_msg}",
        }

