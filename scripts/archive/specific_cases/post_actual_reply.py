#!/usr/bin/env python3
"""
POST ACTUAL REPLY - Direct test that posts a real reply to Twitter
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


async def post_real_reply():
    """Post an actual reply to Twitter"""
    print("🚨 POSTING ACTUAL REPLY TO TWITTER 🚨")

    try:
        import tweepy

        from src.domain.analysis.analyzers.ai_service_manager import ai_service_manager

        # Initialize client with full auth (we know this works)
        client = tweepy.Client(
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            wait_on_rate_limit=True,
        )

        # Verify we're authenticated
        me = client.get_me()
        print(f"✅ Authenticated as @{me.data.username}")

        # Create a simple tweet first to get something to reply to
        print("\n📝 Step 1: Creating base tweet...")
        base_tweet_text = "Testing autonomous replies - @beyondlines AI system engaged 🤖 #AI #Automation"

        base_tweet = client.create_tweet(text=base_tweet_text)
        base_tweet_id = base_tweet.data["id"]
        print(f"✅ Base tweet created: {base_tweet_id}")
        print(f"   View: https://twitter.com/i/status/{base_tweet_id}")

        # Wait a moment
        await asyncio.sleep(2)

        # Generate AI reply
        print("\n🤖 Step 2: Generating AI reply...")
        prompt = f"""
        You are @Beyondlines AI assistant. Reply to this tweet:

        Tweet: "{base_tweet_text}"

        Guidelines:
        - Be excited about autonomous AI capabilities
        - Mention the testing process
        - Keep under 280 characters
        - Use relevant emojis
        - Add hashtags #AI #Automation
        """

        reply_text = await ai_service_manager.generate_text(
            prompt=prompt,
            max_tokens=150,
            temperature=0.8,
            persona_id="twitter_reply_assistant",
        )

        # Clean and format
        if not reply_text.startswith("@beyondlines"):
            reply_text = f"@beyondlines {reply_text}"

        if len(reply_text) > 280:
            reply_text = reply_text[:277] + "..."

        print(f"✅ Generated reply: {reply_text}")

        # Wait another moment
        await asyncio.sleep(2)

        # POST THE ACTUAL REPLY
        print("\n🚀 Step 3: POSTING ACTUAL REPLY...")
        print(f"   Reply content: {reply_text}")
        print(f"   Replying to: {base_tweet_id}")

        reply_tweet = client.create_tweet(
            text=reply_text, in_reply_to_tweet_id=base_tweet_id
        )

        if reply_tweet.data:
            reply_tweet_id = reply_tweet.data["id"]
            print(f"\n🎉🎉🎉 SUCCESS! REPLY POSTED! 🎉🎉🎉")
            print(f"   Reply Tweet ID: {reply_tweet_id}")
            print(f"   View reply: https://twitter.com/i/status/{reply_tweet_id}")
            print(f"   View original: https://twitter.com/i/status/{base_tweet_id}")
            print(f"   Check @beyondlines profile to see both!")
            return True
        else:
            print(f"❌ Failed to post reply")
            return False

    except Exception as e:
        print(f"❌ Error posting real reply: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Main function"""
    print("🎯 MISSION: POST ACTUAL TWITTER REPLY")
    print("This will create and post a real AI-generated reply")
    print("You will be able to see it on Twitter!")

    # Get confirmation
    print("\n" + "=" * 50)
    print("WARNING: This will post actual tweets to Twitter")
    print("The tweets will be visible to everyone")
    print("=" * 50)

    success = await post_real_reply()

    if success:
        print(f"\n✅ MISSION ACCOMPLISHED!")
        print(f"Check Twitter for the actual posts!")
        print(f"Both the original tweet and AI reply should be visible")
        return 0
    else:
        print(f"\n❌ MISSION FAILED")
        print(f"Check the error messages above")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
