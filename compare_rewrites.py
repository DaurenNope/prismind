#!/usr/bin/env python3
"""Compare original vs rewritten content in easy-to-read format"""
import json

def print_comparison(post_num, post):
    """Print a clean comparison of original vs rewrites"""

    print(f"\n{'='*100}")
    print(f"POST #{post_num}: {post['platform'].upper()}")
    print(f"{'='*100}\n")

    # ORIGINAL
    print("📌 ORIGINAL POST")
    print("─" * 100)
    print(post['original_content'])
    print("─" * 100)
    print(f"Engagement: {post['engagement']['likes']} likes, {post['engagement']['replies']} replies")
    print(f"Analysis: Viral Potential {post['analysis']['viral_potential']}/100, Value Score {post['analysis']['value_score']}/10")

    # MATCHED PERSONAS
    print(f"\n🎯 INTELLIGENT MATCHING → Selected {len(post['matched_personas'])} Relevant Personas (not all 5!)")
    for p in post['matched_personas']:
        emoji = {'technical': '🔧', 'builder': '🚀', 'learner': '📚', 'trendsetter': '🔥', 'thought_leader': '💡'}
        print(f"   {emoji.get(p['persona'], '❓')} {p['persona'].upper()}: {p['score']:.0f}/100 points")
        print(f"      Why? {p['reason']}")

    # REWRITES
    print(f"\n✍️  TRANSFORMED VERSIONS\n")

    for i, rewrite in enumerate(post['rewrites'], 1):
        r = rewrite['rewritten']

        print(f"{'━'*100}")
        print(f"VERSION {i}: {r['persona_emoji']} {r['persona_name'].upper()}")
        print(f"{'━'*100}")
        print(f"Platform: {r['platform'].upper()} | Tone: {r['tone_used']} | Match Quality: {rewrite['match_score']:.0f}/100")
        print()
        print(r['rewritten_content'])
        print()
        print(f"✓ Call-to-Action: \"{r['call_to_action']}\"")
        print(f"✓ Key Points: {', '.join(r['key_points_covered'])}")
        print(f"{'━'*100}\n")


with open('real_world_test_results.json', 'r') as f:
    results = json.load(f)

print("\n" + "="*100)
print("PRISMIND INTELLIGENT REWRITING SYSTEM")
print("Real Database Posts → Persona Matching → Multi-Version Transformation")
print("="*100)

for i, post in enumerate(results, 1):
    print_comparison(i, post)

    if i < len(results):
        print("\n" + "▼"*100 + "\n")

print("\n" + "="*100)
print(f"✅ SUMMARY: Processed {len(results)} real posts from your database")
print(f"✅ Generated {sum(len(p['rewrites']) for p in results)} relevant rewrites (avg {sum(len(p['rewrites']) for p in results)/len(results):.1f} per post)")
print(f"✅ Intelligent matching: Only 2-3 personas per post (not all 5!)")
print("="*100 + "\n")
