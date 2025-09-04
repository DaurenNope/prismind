#!/usr/bin/env python3
"""
Simple test to see where Threads login redirects
"""

import asyncio

from playwright.async_api import async_playwright


async def test_threads_url():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    
    print("🌐 Navigating to https://www.threads.net/login...")
    await page.goto('https://www.threads.net/login', wait_until='domcontentloaded')
    await page.wait_for_timeout(5000)
    
    current_url = page.url
    title = await page.title()
    
    print(f"📍 Current URL: {current_url}")
    print(f"📄 Page title: {title}")
    
    # Check if we're redirected to Instagram
    if "instagram.com" in current_url:
        print("🔄 Redirected to Instagram login!")
    elif "threads.net" in current_url:
        print("✅ Still on Threads domain")
    else:
        print(f"❓ Redirected to unexpected domain: {current_url}")
    
    # Look for any login form
    print("\n🔍 Looking for form elements...")
    
    # Check for Instagram login elements
    if "instagram.com" in current_url:
        instagram_selectors = [
            'input[name="username"]',
            'input[aria-label*="username" i]',
            'input[aria-label*="phone" i]',
            'input[aria-label*="email" i]'
        ]
        
        for selector in instagram_selectors:
            try:
                element = await page.query_selector(selector)
                if element:
                    placeholder = await element.get_attribute('placeholder')
                    aria_label = await element.get_attribute('aria-label')
                    print(f"✅ Found Instagram input: {selector}")
                    print(f"   Placeholder: {placeholder}")
                    print(f"   Aria-label: {aria_label}")
                    break
            except:
                continue
    else:
        # Look for any input elements
        inputs = await page.query_selector_all('input')
        print(f"📋 Found {len(inputs)} input elements")
        
        for i, input_elem in enumerate(inputs[:5]):  # Show first 5
            try:
                input_type = await input_elem.get_attribute('type')
                input_name = await input_elem.get_attribute('name')
                input_placeholder = await input_elem.get_attribute('placeholder')
                input_aria_label = await input_elem.get_attribute('aria-label')
                
                print(f"  {i+1}. Type: {input_type}, Name: {input_name}")
                print(f"      Placeholder: {input_placeholder}")
                print(f"      Aria-label: {input_aria_label}")
            except:
                print(f"  {i+1}. Error reading attributes")
    
    print("\n⏳ Waiting 10 seconds for manual inspection...")
    await page.wait_for_timeout(10000)
    
    # Cleanup
    await context.close()
    await browser.close()
    await playwright.stop()

if __name__ == "__main__":
    asyncio.run(test_threads_url()) 