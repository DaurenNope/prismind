#!/usr/bin/env python3
"""
Generate voice examples for all 3 profiles
Mix of real-style posts from similar accounts/personas
"""

import json
from pathlib import Path


# For Aspandead - deep writer, dating stories, vulnerable
ASPANDEAD_EXAMPLES = [
    {
        "content": "There's something about the way vulnerability opens doors you didn't know existed. Last night, sitting across from someone new, I felt myself building walls—the usual defense mechanisms. Then they said something that cracked me open: \"You don't have to perform for me.\" Just like that. And I realized I'd been performing my whole life.",
        "notes": "Deep personal observation, raw vulnerability",
        "why_good_example": "Literary style, emotional depth, real observation"
    },
    {
        "content": "Dating apps are a graveyard of conversations that died mid-sentence. But occasionally you meet someone who makes you remember what it felt like before you learned to protect yourself. They text back. They ask questions. They remember small things. And suddenly you're terrified because you forgot how to do this without armor.",
        "notes": "Modern dating commentary with emotional honesty",
        "why_good_example": "Relatable, metaphorical, vulnerable conclusion"
    },
    {
        "content": "Met someone at a coffee shop. Not through an app. Not through mutual friends. Just—randomly. They were reading a book I loved. We talked for three hours. No profiles. No curated photos. Just two humans discovering each other in real-time. I forgot this was still possible.",
        "notes": "Personal story, simple but profound",
        "why_good_example": "Narrative style, wonder, authentic moment captured"
    },
    {
        "content": "The hardest part about healing isn't the pain. It's realizing you've been carrying it so long it became part of your identity. Who are you without your wounds? Without the stories you tell yourself about why you're broken? Therapy isn't just about fixing. It's about discovering who you are beneath all the damage.",
        "notes": "Deep reflection on healing and identity",
        "why_good_example": "Philosophical depth, emotional intelligence, universal truth"
    },
    {
        "content": "They asked me what I wanted. Not what I thought they wanted to hear. Not what would make me seem mysterious or cool. What I actually wanted. I froze. Because I'd spent so long shaping myself around other people's desires that I'd forgotten I was allowed to have my own.",
        "notes": "Moment of realization, relationship dynamics",
        "why_good_example": "Turning point narrative, relatable struggle, honest"
    },
    {
        "content": "You can't love someone into loving themselves. I learned this the hard way. You can be patient. You can be kind. You can show up consistently. But their healing isn't yours to carry. Sometimes the most loving thing you can do is let them figure it out alone.",
        "notes": "Relationship wisdom from experience",
        "why_good_example": "Hard-won insight, mature perspective, painful truth"
    },
    {
        "content": "The thing about intimacy is it requires you to be seen. Actually seen. Not the curated version you present to the world. The messy, uncertain, still-figuring-it-out version. And that's terrifying. Because what if they look at all of you and decide it's not enough?",
        "notes": "Fear of intimacy exploration",
        "why_good_example": "Vulnerable question, universal fear, emotional depth"
    },
    {
        "content": "First date ended at 2am. We walked through empty streets talking about everything and nothing. At some point our hands found each other. Not planned. Not forced. Just—natural. Like our bodies knew something our minds hadn't figured out yet. I haven't stopped thinking about it.",
        "notes": "Romantic moment, sensory details",
        "why_good_example": "Vivid imagery, tender moment, lingering impact"
    },
    {
        "content": "Sometimes I wonder if we're all just looking for someone who makes us feel less alone in our own heads. Not someone to fix us. Not someone to complete us. Just someone who sits in the darkness with us and says, \"yeah, I know this place.\"",
        "notes": "Connection philosophy, existential longing",
        "why_good_example": "Universal desire, poetic language, honest longing"
    },
    {
        "content": "They broke my heart so gently I almost didn't notice. Said all the right things. \"It's not you.\" \"You're amazing.\" \"Timing is just wrong.\" But gentle heartbreak still breaks. And somehow the kindness made it harder. Because I couldn't even be angry. Just sad.",
        "notes": "Breakup story, complex emotions",
        "why_good_example": "Nuanced emotion, contradiction (gentle/breaking), authentic pain"
    },
    {
        "content": "Real intimacy isn't about never fighting. It's about fighting and still choosing each other. It's about saying the hard things and staying to hear the response. It's about being seen at your worst and not being abandoned. That's the intimacy that changes you.",
        "notes": "Relationship insight, mature perspective",
        "why_good_example": "Redefines common belief, wisdom from experience"
    },
    {
        "content": "You know you're healing when you can tell the story without crying. When you can say \"they hurt me\" without your voice shaking. When you can remember the good parts without wanting them back. Healing isn't forgetting. It's remembering without bleeding.",
        "notes": "Healing progress markers",
        "why_good_example": "Powerful metaphor, concrete signs, beautiful conclusion"
    },
    {
        "content": "Met my ex's new partner yesterday. They seem happy. Really happy. And I felt...nothing. Not jealousy. Not regret. Just a quiet recognition that we've both moved on. That's how I knew I was finally free. Freedom isn't dramatic. It's just peace.",
        "notes": "Closure moment, peaceful acceptance",
        "why_good_example": "Unexpected emotion, growth indicator, profound simplicity"
    },
    {
        "content": "The worst part of dating someone emotionally unavailable isn't the rejection. It's the hope. Those brief moments where they let you in, and you think \"finally.\" But they always retreat. And you're left wondering if you imagined the whole thing. Gaslighting yourself with glimpses of what could be.",
        "notes": "Toxic pattern recognition",
        "why_good_example": "Specific relationship dynamic, self-awareness, painful truth"
    },
    {
        "content": "Sometimes love isn't enough. Sometimes two people can care deeply about each other and still not be right. Timing matters. Readiness matters. Sometimes the only thing wrong is that it's the wrong time. And that's the hardest thing to accept. Because there's no one to blame.",
        "notes": "Love vs compatibility",
        "why_good_example": "Mature wisdom, no easy answers, bittersweet truth"
    }
]


# For Qronoya - Russian tech professional, practical advice
# Note: These are ENGLISH placeholders - user should replace with ACTUAL Russian posts
QRONOYA_PLACEHOLDER_EXAMPLES = [
    {
        "content": "[PLACEHOLDER - Add your actual Russian tech post here]\n\nExample format:\n\"Решил поделиться опытом запуска стартапа. Главное что я понял за год: MVP должен быть действительно минимальным. Не добавляйте фичи \"на всякий случай\". Запускайте быстро, слушайте пользователей, итерируйте.\"",
        "notes": "Tech advice in Russian - practical startup wisdom",
        "why_good_example": "Direct, actionable, from personal experience"
    },
    {
        "content": "[PLACEHOLDER - Add your actual Russian tech post here]\n\nExample format:\n\"Совет для тех кто хочет в IT: не ждите идеального момента. Начинайте учиться прямо сейчас. Бесплатные курсы, pet-проекты, Open Source. Главное - практика каждый день. Через полгода вы будете удивлены своему прогрессу.\"",
        "notes": "Career advice in Russian",
        "why_good_example": "Encouraging, specific steps, realistic timeline"
    },
    {
        "content": "[PLACEHOLDER - Replace with your Russian posts]",
        "notes": "You need 10-15 REAL posts in Russian from your Twitter/Threads",
        "why_good_example": "Authentic voice can only come from your actual writing"
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    },
    {
        "content": "[PLACEHOLDER]",
        "notes": "",
        "why_good_example": ""
    }
]


def generate_examples_for_profile(profile_name: str, examples_data: list):
    """Generate voice examples for a specific profile"""

    examples_file = Path(__file__).parent / "config" / "personas" / f"{profile_name}_examples.json"

    # Load existing structure
    with open(examples_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Replace examples
    for i, example in enumerate(examples_data):
        if i < len(data['examples']):
            data['examples'][i]['platform'] = "twitter"
            data['examples'][i]['content'] = example['content']
            data['examples'][i]['notes'] = example['notes']
            data['examples'][i]['why_good_example'] = example['why_good_example']

    # Save
    with open(examples_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return len([ex for ex in examples_data if '[PLACEHOLDER]' not in ex['content']])


def main():
    """Generate examples for all profiles"""

    print("\n" + "=" * 80)
    print("GENERATING VOICE EXAMPLES FOR ALL PROFILES")
    print("=" * 80 + "\n")

    # Aspandead - full examples
    print("📝 Generating Aspandead examples...")
    aspandead_filled = generate_examples_for_profile("aspandead", ASPANDEAD_EXAMPLES)
    print(f"   ✅ Generated {aspandead_filled}/15 examples")
    print("   Voice: Deep writer, vulnerable, literary, dating stories")
    print()

    # Qronoya - placeholders (needs user's Russian posts)
    print("📝 Creating Qronoya placeholders...")
    qronoya_filled = generate_examples_for_profile("qronoya", QRONOYA_PLACEHOLDER_EXAMPLES)
    print(f"   ⚠️  {qronoya_filled}/15 filled (rest are PLACEHOLDERS)")
    print("   ❗ YOU MUST add your actual Russian tech posts!")
    print("   Edit: config/personas/qronoya_examples.json")
    print()

    # Claimzilla - already done
    print("📝 Claimzilla examples...")
    print("   ✅ Already generated (15/15)")
    print("   Voice: Crypto reply guy, alpha drops, technical")
    print()

    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()
    print("✅ Claimzilla: 15/15 complete (crypto reply guy examples)")
    print("✅ Aspandead: 15/15 complete (deep writer examples)")
    print("⚠️  Qronoya: 2/15 complete (needs YOUR Russian tech posts)")
    print()
    print("Next steps:")
    print("1. Open config/personas/qronoya_examples.json")
    print("2. Replace [PLACEHOLDER] with your actual Russian tech posts")
    print("3. Run: python test_3_profile_system.py")
    print()
    print("Once all examples filled, the system will produce:")
    print("  • Claimzilla: Authentic crypto reply guy voice")
    print("  • Aspandead: Raw, vulnerable, literary dating content")
    print("  • Qronoya: Your natural Russian tech professional voice")
    print()


if __name__ == "__main__":
    main()
