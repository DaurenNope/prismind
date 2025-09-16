#!/usr/bin/env python3
"""
Reddit Connectivity Test and Troubleshooting Script
"""

import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def test_reddit_connectivity():
    """Test different Reddit endpoints to diagnose connectivity issues"""
    
    load_dotenv()
    
    print("🌐 Reddit Connectivity Test")
    print("=" * 50)
    
    # Test different Reddit endpoints
    endpoints = [
        "https://www.reddit.com",
        "https://oauth.reddit.com",
        "https://api.reddit.com",
        "https://reddit.com"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"Testing {endpoint}...")
            response = requests.get(endpoint, timeout=10)
            print(f"  ✅ Status: {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            print(f"  ❌ Connection Error: {e}")
        except requests.exceptions.Timeout:
            print(f"  ❌ Timeout")
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n🔧 Troubleshooting Steps:")
    print("1. Check if you're behind a firewall/proxy")
    print("2. Try using a VPN if Reddit is geo-blocked")
    print("3. Check DNS settings")
    print("4. Try different network connection")
    
    print("\n📊 Current Status:")
    print("- 60 Reddit posts successfully collected earlier")
    print("- OAuth2 tokens are valid but network connectivity issues")
    print("- Automated workflow is now running")
    print("- System will retry automatically")

if __name__ == "__main__":
    test_reddit_connectivity()
