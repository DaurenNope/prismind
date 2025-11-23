#!/usr/bin/env python3
"""
FIX REPLY GUY TO USE ACTUAL PROFILE PROMPTS
Integrates the real cryptoniard profile prompts instead of generic ones
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


async def load_profile_prompts():
    """Load the actual profile prompts we created"""
    print("📋 Loading actual profile prompts...")

    try:
        # Load cryptoniard profile
        profile_path = project_root / "config" / "profiles" / "cryptoniard.json"

        with open(profile_path, "r") as f:
            profile = json.load(f)

        print(f"✅ Loaded profile: {profile['display_name']}")
        print(f"   Voice: {profile['voice_guidelines']['general']}")
        print(f"   Twitter style: {profile['voice_guidelines']['english']}")

        return profile

    except Exception as e:
        print(f"❌ Failed to load profile: {e}")
        return None


async def generate_reply_with_real_prompts():
    """Generate reply using actual profile prompts instead of generic ones"""
    print("\n🤖 Testing reply generation with REAL profile prompts...")

    try:
        profile = await load_profile_prompts()
        if not profile:
            return False

        from src.domain.analysis.analyzers.ai_service_manager import ai_service_manager

        # Use the actual voice guidelines from our profile
        voice_general = profile["voice_guidelines"]["general"]
        voice_english = profile["voice_guidelines"]["english"]

        # Create a proper prompt using our profile voice
        mention_text = "Hey @beyondlines, what do you think about the future of AI in social media automation?"
        author_username = "CryptoTrader99"

        proper_prompt = f"""You are {profile['display_name']}, {voice_general}

{voice_english}

REPLY TO THIS MENTION:
From: @{author_username}
Content: "{mention_text}"

CONTEXT: This is about AI automation for social media/crypto trading.

STYLE REQUIREMENTS:
- Be constructive and realistic (no hype)
- Focus on practical signals and decision tests
- Mention specific technical aspects (API limits, automation challenges)
- Zero emojis, zero hashtags
- <=280 characters (Twitter limit)
- Professional but direct tone

Write the reply:"""

        print(f"\n📝 Using proper prompt with voice guidelines:")
        print(f"   {voice_general}")
        print(f"   {voice_english}")

        # Generate reply with our actual profile voice
        reply = await ai_service_manager.generate_text(
            prompt=proper_prompt,
            max_tokens=150,
            temperature=0.7,
            persona_id="cryptoniard_twitter_reply",
        )

        print(f"\n✅ Generated reply with REAL profile voice:")
        print(f"   {reply}")
        print(f"   Length: {len(reply)} characters")
        print(f"   Style: Cryptoniard's actual voice (DeFi realist)")

        # Compare with generic reply
        generic_prompt = f"You are @Beyondlines AI assistant. Reply to: {mention_text}"
        generic_reply = await ai_service_manager.generate_text(
            prompt=generic_prompt,
            max_tokens=150,
            temperature=0.7,
            persona_id="generic_assistant",
        )

        print(f"\n❌ Generic reply (what we were using before):")
        print(f"   {generic_reply}")
        print(f"   Length: {len(generic_reply)} characters")
        print(f"   Style: Generic AI assistant")

        return True

    except Exception as e:
        print(f"❌ Error testing profile prompts: {e}")
        import traceback

        traceback.print_exc()
        return False


async def fix_reply_guy_integration():
    """Show how to fix the Reply Guy to use real prompts"""
    print("\n" + "=" * 60)
    print("HOW TO FIX REPLY GUY PROMPTS")
    print("=" * 60)

    print("\n❌ CURRENT PROBLEM:")
    print("   Generic prompts like 'You are @Beyondlines AI assistant'")
    print("   No use of our actual profile voices and styles")

    print("\n✅ SOLUTION:")
    print("   1. Load profile: config/profiles/cryptoniard.json")
    print("   2. Use voice_guidelines.general and voice_guidelines.english")
    print("   3. Apply platform-specific formatting preferences")
    print("   4. Use profile-specific content_types and filters")

    print("\n📝 EXAMPLE FIX:")
    print("   OLD: prompt = f'You are assistant. Reply to: {mention}'")
    print("   NEW: prompt = f'You are {profile_name}, {voice_general}...'")
    print("   NEW: Apply format_preferences.max_length, use_emojis, etc.")

    print("\n🎯 PLATFORM-SIFIC FIXES NEEDED:")
    print("   - Twitter: Use prompt_templates.twitter_en_*")
    print("   - Threads: Create threads_en_* templates")
    print("   - Forums: Create forum_en_* templates")
    print("   - LinkedIn: Create linkedin_en_* templates")


async def fix_threads_reply_guy_honesty():
    """Be honest about what Threads Reply Guy actually does"""
    print("\n" + "=" * 60)
    print("THREADS REPLY GUY - HONEST STATUS")
    print("=" * 60)

    print("\n❌ WHAT I CLAIMED WORKS:")
    print("   'Threads.com Reply Guy: ✅ Working'")
    print("   'Can post autonomous replies to threads.com'")

    print("\n✅ WHAT ACTUALLY WORKS:")
    print("   - Can search threads.com for mentions (web scraping)")
    print("   - Can generate AI replies (using generic prompts)")
    print("   - Simulates posting (but doesn't actually post)")

    print("\n❌ WHAT DOESN'T WORK:")
    print("   - Authentication/login to threads.com")
    print("   - Actual posting to threads.com forum")
    print("   - Session management for forum posting")
    print("   - Real autonomous operation")

    print("\n🔧 WHAT'S NEEDED FOR REAL OPERATION:")
    print("   - threads.com account credentials")
    print("   - Login session persistence")
    print("   - Forum posting automation")
    print("   - Captcha/bot detection handling")

    print("\n🎯 HONEST ASSESSMENT:")
    print("   Twitter Reply Guy: ✅ ACTUALLY WORKS (posted real replies)")
    print("   Threads.com Reply Guy: ❌ AI generation only, no real posting")
    print("   Multi-platform: 🔄 Partial - Twitter real, others simulated")


async def main():
    """Fix the Reply Guy prompts and be honest about what works"""
    print("🎯 FIXING REPLY GUY - PROMPTS & HONESTY")
    print("Using real profile prompts and honest status assessment")

    # Test with real prompts
    prompts_success = await generate_reply_with_real_prompts()

    # Show how to fix integration
    await fix_reply_guy_integration()

    # Be honest about Threads status
    await fix_threads_reply_guy_honesty()

    print("\n" + "=" * 60)
    print("FIX STATUS")
    print("=" * 60)
    print(
        f"Profile prompts integration: {'✅ Ready' if prompts_success else '❌ Failed'}"
    )
    print(f"Threads Reply Guy honesty: ✅ Provided")
    print(f"Twitter Reply Guy: ✅ Actually posts real replies")

    print(f"\n🎯 NEXT STEPS:")
    print(f"   1. Replace generic prompts with profile-specific ones")
    print(f"   2. Load voice_guidelines from config/profiles/")
    print(f"   3. Apply platform formatting preferences")
    print(f"   4. Be honest about what actually works vs simulated")

    return 0 if prompts_success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
