#!/usr/bin/env python3
"""
Debug script for GitHub automation issues
"""

import os
import sys
import json
from pathlib import Path

def check_github_secrets():
    """Check if required GitHub secrets are set"""
    print("🔍 Checking GitHub Secrets...")
    
    # Required secrets for the workflow
    required_secrets = [
        'REDDIT_COOKIES_JSON',
        'TWITTER_COOKIES_JSON',
        'REDDIT_USERNAME',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    # Optional but useful secrets
    optional_secrets = [
        'REDDIT_CLIENT_ID',
        'REDDIT_CLIENT_SECRET', 
        'REDDIT_PASSWORD',
        'REDDIT_ACCESS_TOKEN',
        'REDDIT_REFRESH_TOKEN',
        'REDDIT_USER_AGENT',
        'TWITTER_USERNAME',
        'TWITTER_PASSWORD',
        'SUPABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
        'GEMINI_API_KEY',
        'MISTRAL_API_KEY'
    ]
    
    missing_required = []
    missing_optional = []
    found_secrets = []
    
    # Check environment variables (in GitHub Actions these would be secrets)
    for secret in required_secrets:
        if os.getenv(secret):
            found_secrets.append(secret)
        else:
            missing_required.append(secret)
            
    for secret in optional_secrets:
        if os.getenv(secret):
            found_secrets.append(secret)
        else:
            missing_optional.append(secret)
    
    print(f"✅ Found {len(found_secrets)} secrets:")
    for secret in found_secrets:
        print(f"  - {secret}")
        
    if missing_required:
        print(f"❌ Missing {len(missing_required)} required secrets:")
        for secret in missing_required:
            print(f"  - {secret}")
    else:
        print("✅ All required secrets are present")
        
    if missing_optional:
        print(f"⚠️ Missing {len(missing_optional)} optional secrets:")
        for secret in missing_optional:
            print(f"  - {secret}")

def check_cookie_files():
    """Check if cookie files exist and are valid"""
    print("\n🔍 Checking Cookie Files...")
    
    cookies_dir = Path("cookies")
    if not cookies_dir.exists():
        print("❌ Cookies directory not found")
        return
        
    reddit_cookie = cookies_dir / "reddit.json"
    twitter_cookie = cookies_dir / "twitter.json"
    
    if reddit_cookie.exists():
        try:
            with open(reddit_cookie, 'r') as f:
                data = json.load(f)
            print(f"✅ Reddit cookie file found with {len(data)} entries")
        except Exception as e:
            print(f"❌ Reddit cookie file invalid: {e}")
    else:
        print("❌ Reddit cookie file not found")
        
    if twitter_cookie.exists():
        try:
            with open(twitter_cookie, 'r') as f:
                data = json.load(f)
            print(f"✅ Twitter cookie file found with {len(data)} entries")
        except Exception as e:
            print(f"❌ Twitter cookie file invalid: {e}")
    else:
        print("❌ Twitter cookie file not found")

def check_python_environment():
    """Check Python environment and dependencies"""
    print("\n🔍 Checking Python Environment...")
    
    # Check Python version
    print(f"✅ Python version: {sys.version}")
    
    # Check key dependencies
    try:
        import playwright
        print("✅ Playwright installed")
    except ImportError:
        print("❌ Playwright not installed")
        
    try:
        import requests
        print("✅ Requests installed")
    except ImportError:
        print("❌ Requests not installed")
        
    try:
        from dotenv import load_dotenv
        print("✅ Python-dotenv installed")
    except ImportError:
        print("❌ Python-dotenv not installed")

def check_github_cli():
    """Check if GitHub CLI is installed and configured"""
    print("\n🔍 Checking GitHub CLI...")
    
    try:
        import subprocess
        result = subprocess.run(['gh', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ GitHub CLI installed")
            print(f"   Version: {result.stdout.splitlines()[0]}")
        else:
            print("❌ GitHub CLI not installed or not in PATH")
    except FileNotFoundError:
        print("❌ GitHub CLI not installed")

def main():
    """Main debug function"""
    print("🤖 PrisMind GitHub Automation Debug Tool")
    print("=" * 50)
    
    check_github_secrets()
    check_cookie_files()
    check_python_environment()
    check_github_cli()
    
    print("\n💡 Recommendations:")
    print("1. Make sure all required secrets are set in GitHub repository settings")
    print("2. Verify cookie files are properly exported and uploaded as secrets")
    print("3. Check that cron schedule syntax is correct in the workflow file")
    print("4. Ensure the workflow file is in the correct location (.github/workflows/)")
    print("5. Check GitHub Actions logs for specific error messages")

if __name__ == "__main__":
    main()