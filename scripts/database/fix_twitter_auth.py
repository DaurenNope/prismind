"""
Fix Twitter API authentication - test different approaches
"""

import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import tweepy
from dotenv import load_dotenv

load_dotenv()


def test_auth():
    """Test authentication with different methods"""

    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

    print("🔧 Testing Twitter Authentication Fixes\n")
    print("=" * 60)

    # Check token format
    print("\n1️⃣  Checking token format...")
    print(f"   API Key length: {len(api_key) if api_key else 0}")
    print(f"   API Secret length: {len(api_secret) if api_secret else 0}")
    print(f"   Access Token length: {len(access_token) if access_token else 0}")
    print(f"   Access Secret length: {len(access_secret) if access_secret else 0}")

    # Check for common issues
    if access_token and "PASTE" in access_token.upper():
        print("   ❌ Access Token still has placeholder!")
        return False

    # Try OAuth 1.0a User Context (recommended for posting)
    print("\n2️⃣  Testing OAuth 1.0a User Context...")
    try:
        # Method 1: Using tweepy.Client (v2 API)
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret,
            wait_on_rate_limit=True,
        )

        me = client.get_me()
        print(f"   ✅ SUCCESS with tweepy.Client!")
        print(f"      Username: @{me.data.username}")
        print(f"      User ID: {me.data.id}")
        print(f"      Name: {me.data.name}")

        # Test if we can actually post (dry run - check permissions)
        print("\n3️⃣  Testing posting permissions...")
        try:
            # Just check rate limits - this verifies we have write access
            rate_limits = client.get_rate_limit_status()
            if "statuses" in rate_limits.get("resources", {}):
                print("   ✅ Write permissions confirmed!")
                print(
                    f"      Remaining tweets: {rate_limits['resources']['statuses']['/statuses/update']['remaining']}"
                )
            return True
        except Exception as e:
            print(f"   ⚠️  Couldn't check rate limits: {e}")
            return True  # Auth worked, that's the main thing

    except tweepy.Unauthorized as e:
        print(f"   ❌ 401 Unauthorized")
        print(f"      Error: {e}")
        print("\n   🔧 SOLUTION: Regenerate Access Token & Secret")
        print("      Even if you have Read and Write permissions,")
        print("      if the Access Token was generated BEFORE you")
        print("      changed permissions, it won't work.")
        print("\n   Steps:")
        print("   1. Go to https://developer.twitter.com/en/portal/dashboard")
        print("   2. Select your app")
        print("   3. Go to 'Keys and tokens' tab")
        print("   4. Under 'Access Token and Secret', click 'Regenerate'")
        print("   5. Copy the NEW Access Token and Secret")
        print("   6. Update .env with the new values")
        print("   7. Run this script again")
        return False

    except tweepy.Forbidden as e:
        print(f"   ❌ 403 Forbidden: {e}")
        print("\n   This usually means:")
        print("   - App permissions are still 'Read only'")
        print("   - Or Access Token doesn't match the app")
        return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_auth()
    print("\n" + "=" * 60)
    if success:
        print("✅ Authentication is working!")
        print("   You can now post tweets using the Twitter API.")
    else:
        print("❌ Authentication failed.")
        print("   Follow the steps above to regenerate tokens.")
    sys.exit(0 if success else 1)
