#!/usr/bin/env python3
"""
Cookie Management Helper
Check, validate, and manage cookies for Twitter and Threads
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

def check_twitter_cookies() -> Dict:
    """Check Twitter cookie file status"""
    username = os.getenv("TWITTER_USERNAME")
    cookie_file = os.getenv("TWITTER_COOKIE_FILE") or (f"config/twitter_cookies_{username}.json" if username else "config/twitter_cookies.json")
    cookie_path = Path(cookie_file)
    
    result = {
        "platform": "twitter",
        "cookie_file": str(cookie_file),
        "exists": cookie_path.exists(),
        "cookie_count": 0,
        "is_valid": False,
        "error": None
    }
    
    if not username:
        result["message"] = "TWITTER_USERNAME not set"
        result["status"] = "error"
        return result
    
    if not cookie_path.exists():
        result["message"] = f"Cookie file not found: {cookie_file}"
        return result
    
    try:
        with open(cookie_path, "r") as f:
            cookie_data = json.load(f)
        
        # Handle different formats
        if isinstance(cookie_data, list):
            cookies = cookie_data
        elif isinstance(cookie_data, dict):
            cookies = cookie_data.get("cookies", cookie_data.get("data", []))
        else:
            cookies = []
        
        result["cookie_count"] = len(cookies)
        result["is_valid"] = len(cookies) > 0
        
        # Check if cookies have expiration dates
        if cookies:
            expired_count = 0
            for cookie in cookies:
                if isinstance(cookie, dict):
                    expires = cookie.get("expires", cookie.get("expirationDate", 0))
                    if expires and expires > 0:
                        # Convert timestamp to datetime
                        try:
                            if expires > 10000000000:  # Unix timestamp in milliseconds
                                expires_dt = datetime.fromtimestamp(expires / 1000)
                            else:  # Unix timestamp in seconds
                                expires_dt = datetime.fromtimestamp(expires)
                            
                            if expires_dt < datetime.now():
                                expired_count += 1
                        except:
                            pass
            
            if expired_count > 0:
                result["expired_count"] = expired_count
                result["message"] = f"Found {expired_count} expired cookies out of {len(cookies)}"
            else:
                result["message"] = f"✅ Valid cookies found ({len(cookies)} cookies)"
        
    except Exception as e:
        result["error"] = str(e)
        result["message"] = f"Error reading cookies: {e}"
    
    return result

def check_threads_cookies() -> Dict:
    """Check Threads cookie file status"""
    cookie_file = os.getenv("THREADS_COOKIES_FILE") or "config/threads_cookies.json"
    
    # Also check alternative locations
    alt_paths = [
        cookie_file,
        "cookies/threads_cookies.json",
        "config/threads_cookies.json"
    ]
    
    cookie_path = None
    for path in alt_paths:
        p = Path(path)
        if p.exists():
            cookie_path = p
            cookie_file = str(p)
            break
    
    result = {
        "platform": "threads",
        "cookie_file": cookie_file,
        "exists": cookie_path is not None,
        "cookie_count": 0,
        "is_valid": False,
        "error": None
    }
    
    if not cookie_path:
        result["message"] = f"Cookie file not found in: {', '.join(alt_paths)}"
        return result
    
    try:
        with open(cookie_path, "r") as f:
            cookie_data = json.load(f)
        
        # Threads uses storage_state format
        if isinstance(cookie_data, dict):
            cookies = cookie_data.get("cookies", [])
            result["cookie_count"] = len(cookies)
            result["is_valid"] = len(cookies) > 0
            
            if cookies:
                result["message"] = f"✅ Valid cookies found ({len(cookies)} cookies)"
            else:
                result["message"] = "Cookie file exists but no cookies found"
        else:
            result["message"] = "Invalid cookie format (expected dict with 'cookies' key)"
        
    except Exception as e:
        result["error"] = str(e)
        result["message"] = f"Error reading cookies: {e}"
    
    return result

def print_status():
    """Print cookie status for both platforms"""
    print("=" * 70)
    print("🍪 COOKIE MANAGEMENT")
    print("=" * 70)
    print()
    
    # Check Twitter
    print("🐦 Twitter Cookies:")
    print("-" * 70)
    twitter_status = check_twitter_cookies()
    print(f"File: {twitter_status['cookie_file']}")
    print(f"Exists: {'✅ Yes' if twitter_status['exists'] else '❌ No'}")
    if twitter_status['exists']:
        print(f"Cookies: {twitter_status['cookie_count']}")
        print(f"Valid: {'✅ Yes' if twitter_status['is_valid'] else '❌ No'}")
        if 'expired_count' in twitter_status:
            print(f"⚠️  Expired: {twitter_status['expired_count']}")
    print(f"Status: {twitter_status['message']}")
    if twitter_status.get('error'):
        print(f"❌ Error: {twitter_status['error']}")
    print()
    
    # Check Threads
    print("🧵 Threads Cookies:")
    print("-" * 70)
    threads_status = check_threads_cookies()
    print(f"File: {threads_status['cookie_file']}")
    print(f"Exists: {'✅ Yes' if threads_status['exists'] else '❌ No'}")
    if threads_status['exists']:
        print(f"Cookies: {threads_status['cookie_count']}")
        print(f"Valid: {'✅ Yes' if threads_status['is_valid'] else '❌ No'}")
    print(f"Status: {threads_status['message']}")
    if threads_status.get('error'):
        print(f"❌ Error: {threads_status['error']}")
    print()
    
    # Recommendations
    print("💡 Recommendations:")
    print("-" * 70)
    
    if not twitter_status['exists'] or not twitter_status['is_valid']:
        print("🐦 Twitter:")
        print("   • Set TWITTER_PASSWORD in .env for automatic cookie refresh")
        print("   • Or manually log in once to generate cookies")
        print("   • Cookie file will be saved automatically")
    
    if not threads_status['exists'] or not threads_status['is_valid']:
        print("🧵 Threads:")
        print("   • Set THREADS_USERNAME and THREADS_PASSWORD in .env")
        print("   • Run: python scripts/capture_threads_cookies.py")
        print("   • Or let the system authenticate automatically")
    
    print()
    print("=" * 70)

if __name__ == "__main__":
    print_status()

