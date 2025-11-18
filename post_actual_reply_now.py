#!/usr/bin/env python3
"""
POST ACTUAL REPLY RIGHT NOW
Posts the AI-generated reply to our existing mention
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


async def post_actual_reply():
    """Post the actual AI-generated reply"""
    print("🚨 POSTING ACTUAL REPLY RIGHT NOW!")
    print("This will post a real reply to Twitter")

    try:
        import tweepy

        # Initialize client
        client = tweepy.Client(
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            consumer_key=os.getenv("TWITTER_API_KEY"),
            consumer_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            wait_on_rate_limit=True,
        )

        print(f"✅ Authenticated as @{client.get_me().data.username}")

        # The mention we created earlier
        mention_id = "1989961724167139440"

        # The AI reply we generated
        reply_content = "@Cryptoniard Hey @Cryptoniard! It sounds like you're into some exciting crypto projects. If you have any questions about staying safe while exploring the blockchain world, I'm here to help! 🚀🔒 #CryptoSafetyTips"

        print(f"\n📝 Posting actual reply:")
        print(f"   Reply: {reply_content}")
        print(f"   To: https://twitter.com/i/status/{mention_id}")

        # POST THE ACTUAL REPLY
        response = client.create_tweet(
            text=reply_content, in_reply_to_tweet_id=mention_id
        )

        if response.data:
            reply_id = response.data["id"]
            print(f"\n🎉🎉🎉 ACTUAL REPLY POSTED! 🎉🎉🎉")
            print(f"   Reply ID: {reply_id}")
            print(f"   View at: https://twitter.com/i/status/{reply_id}")
            print(f"   Replying to: https://twitter.com/i/status/{mention_id}")
            print(f"\n🚀 GO CHECK TWITTER NOW!")
            print(f"The reply is LIVE on your timeline!")
            return True
        else:
            print(f"❌ Failed to post reply")
            return False

    except Exception as e:
        print(f"❌ Error posting actual reply: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Post the actual reply"""
    print("🎯 POSTING ACTUAL AI-GENERATED REPLY")
    print("This will post the reply the Reply Guy generated")

    success = await post_actual_reply()

    if success:
        print(f"\n✅ SUCCESS! CHECK TWITTER NOW!")
        print(f"The actual Reply Guy response is posted and visible!")
    else:
        print(f"\n❌ Failed to post actual reply")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
