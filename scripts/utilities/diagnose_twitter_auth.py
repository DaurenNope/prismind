"""
Diagnose Twitter API authentication issues
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import tweepy
from dotenv import load_dotenv

load_dotenv()


def diagnose():
    """Diagnose Twitter API authentication"""

    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    print("🔍 Twitter API Authentication Diagnostics\n")
    print("=" * 60)

    # Check if all credentials are present
    print("\n1️⃣  Checking credentials...")
    missing = []
    if not api_key:
        missing.append("TWITTER_API_KEY")
    if not api_secret:
        missing.append("TWITTER_API_SECRET")
    if not access_token:
        missing.append("TWITTER_ACCESS_TOKEN")
    if not access_secret:
        missing.append("TWITTER_ACCESS_TOKEN_SECRET")

    if missing:
        print(f"   ❌ Missing: {', '.join(missing)}")
        return
    else:
        print("   ✅ All credentials present")
        print(f"   API Key: {api_key[:10]}...")
        print(f"   Access Token: {access_token[:15]}...")

    # Try different authentication methods
    print("\n2️⃣  Testing authentication methods...")

    # Method 1: OAuth 1.0a with all credentials
    print("\n   Method 1: OAuth 1.0a (Full credentials)")
    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
            wait_on_rate_limit=True,
        )

        me = client.get_me()
        print(f"   ✅ SUCCESS! Authenticated as @{me.data.username}")
        print(f"      User ID: {me.data.id}")
        print(f"      Name: {me.data.name}")

        # Test posting capability
        print("\n   Testing posting capability...")
        try:
            # Check rate limits
            rate_limits = client.get_rate_limit_status()
            status_limits = rate_limits["resources"]["statuses"]["/statuses/update"]
            remaining = status_limits["remaining"]
            reset = status_limits["reset"]

            print(f"   ✅ Can post tweets!")
            print(f"      Remaining: {remaining} tweets")
            print(f"      Resets at: {reset}")

            return True

        except Exception as e:
            print(f"   ⚠️  Rate limit check failed: {e}")
            return True  # Auth worked, rate limit check is optional

    except tweepy.Unauthorized as e:
        print(f"   ❌ 401 Unauthorized: {e}")
        print("\n   💡 Possible causes:")
        print("      - Access Token/Secret are incorrect")
        print("      - Tokens were regenerated (need to update .env)")
        print("      - App doesn't have 'Read and Write' permissions")
        print("\n   🔧 Solutions:")
        print("      1. Go to https://developer.twitter.com/en/portal/dashboard")
        print("      2. Select your app")
        print("      3. Check 'App permissions' - must be 'Read and Write'")
        print("      4. Regenerate Access Token & Secret if needed")
        print("      5. Update .env with new tokens")
        return False

    except tweepy.Forbidden as e:
        print(f"   ❌ 403 Forbidden: {e}")
        print("\n   💡 Your app may not have the right permissions.")
        print("   🔧 Check app permissions in Twitter Developer Portal")
        return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = diagnose()
    print("\n" + "=" * 60)
    if success:
        print("✅ Authentication is working! You can post tweets.")
    else:
        print("❌ Authentication failed. See diagnostics above.")
    sys.exit(0 if success else 1)
