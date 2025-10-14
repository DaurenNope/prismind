"""
Underground & Niche Content Sources
Reddit RSS feeds for non-mainstream, fascinating content
"""

# ============================================
# REDDIT RSS FEEDS (No API needed!)
# ============================================

# Reddit RSS format: https://www.reddit.com/r/SUBREDDIT/.rss

UNDERGROUND_REDDIT_MYSTERY = [
    'https://www.reddit.com/r/UnresolvedMysteries/.rss',
    'https://www.reddit.com/r/HighStrangeness/.rss',
    'https://www.reddit.com/r/Glitch_in_the_Matrix/.rss',
    'https://www.reddit.com/r/Paranormal/.rss',
    'https://www.reddit.com/r/Thetruthishere/.rss',
    'https://www.reddit.com/r/Missing411/.rss',
    'https://www.reddit.com/r/Humanoidencounters/.rss',
    'https://www.reddit.com/r/UFOs/.rss',
    'https://www.reddit.com/r/aliens/.rss',
    'https://www.reddit.com/r/ufo/.rss',
    'https://www.reddit.com/r/cryptids/.rss',
]

UNDERGROUND_REDDIT_CONSPIRACY = [
    'https://www.reddit.com/r/conspiracy/.rss',
    'https://www.reddit.com/r/conspiracytheories/.rss',
    'https://www.reddit.com/r/conspiracy_commons/.rss',
    'https://www.reddit.com/r/AlternativeHistory/.rss',
    'https://www.reddit.com/r/CulturalLayer/.rss',
    'https://www.reddit.com/r/C_S_T/.rss',  # Critical Shower Thoughts
]

UNDERGROUND_REDDIT_OCCULT = [
    'https://www.reddit.com/r/occult/.rss',
    'https://www.reddit.com/r/Esoteric/.rss',
    'https://www.reddit.com/r/Hermetics/.rss',
    'https://www.reddit.com/r/Alchemy/.rss',
    'https://www.reddit.com/r/Psychonaut/.rss',
    'https://www.reddit.com/r/RationalPsychonaut/.rss',
    'https://www.reddit.com/r/Shamanism/.rss',
    'https://www.reddit.com/r/energy_work/.rss',
    'https://www.reddit.com/r/kundalini/.rss',
    'https://www.reddit.com/r/Soulnexus/.rss',
    'https://www.reddit.com/r/Echerdex/.rss',
]

UNDERGROUND_REDDIT_WEIRD = [
    'https://www.reddit.com/r/Weird/.rss',
    'https://www.reddit.com/r/Damnthatsinteresting/.rss',
    'https://www.reddit.com/r/Interestingasfuck/.rss',
    'https://www.reddit.com/r/WTF/.rss',
    'https://www.reddit.com/r/Creepy/.rss',
    'https://www.reddit.com/r/oddlyterrifying/.rss',
    'https://www.reddit.com/r/Nosleep/.rss',
    'https://www.reddit.com/r/LetsNotMeet/.rss',
]

UNDERGROUND_REDDIT_PHILOSOPHY = [
    'https://www.reddit.com/r/Philosophy/.rss',
    'https://www.reddit.com/r/Showerthoughts/.rss',
    'https://www.reddit.com/r/stoicism/.rss',
    'https://www.reddit.com/r/awakened/.rss',
    'https://www.reddit.com/r/spirituality/.rss',
    'https://www.reddit.com/r/consciousness/.rss',
    'https://www.reddit.com/r/Jung/.rss',
]

UNDERGROUND_REDDIT_PSYCHOLOGY = [
    'https://www.reddit.com/r/psychology/.rss',
    'https://www.reddit.com/r/Meditation/.rss',
    'https://www.reddit.com/r/Mindfulness/.rss',
    'https://www.reddit.com/r/getdisciplined/.rss',
    'https://www.reddit.com/r/DecidingToBeBetter/.rss',
    'https://www.reddit.com/r/selfimprovement/.rss',
]

UNDERGROUND_REDDIT_DEEP = [
    'https://www.reddit.com/r/DeepThoughts/.rss',
    'https://www.reddit.com/r/StonerPhilosophy/.rss',
    'https://www.reddit.com/r/Theoryofreddit/.rss',
    'https://www.reddit.com/r/InsightfulQuestions/.rss',
]

# Niche tech/startup subreddits (non-mainstream)
UNDERGROUND_REDDIT_TECH = [
    'https://www.reddit.com/r/coolgithubprojects/.rss',
    'https://www.reddit.com/r/SideProject/.rss',
    'https://www.reddit.com/r/indiehackers/.rss',
    'https://www.reddit.com/r/SaaS/.rss',
    'https://www.reddit.com/r/smallbusiness/.rss',
]

# ============================================
# AGGREGATE BY CATEGORY
# ============================================

UNDERGROUND_SOURCES = {
    'mystery': UNDERGROUND_REDDIT_MYSTERY,
    'conspiracy': UNDERGROUND_REDDIT_CONSPIRACY,
    'occult': UNDERGROUND_REDDIT_OCCULT,
    'weird': UNDERGROUND_REDDIT_WEIRD,
    'philosophy': UNDERGROUND_REDDIT_PHILOSOPHY,
    'psychology': UNDERGROUND_REDDIT_PSYCHOLOGY,
    'deep_thoughts': UNDERGROUND_REDDIT_DEEP,
    'indie_tech': UNDERGROUND_REDDIT_TECH,
}

def get_all_underground_sources():
    """Get all underground Reddit RSS feeds"""
    all_sources = []
    for sources in UNDERGROUND_SOURCES.values():
        all_sources.extend(sources)
    return all_sources

def get_underground_by_category(category):
    """Get underground sources by category"""
    return UNDERGROUND_SOURCES.get(category, [])

# ============================================
# STATS
# ============================================

TOTAL_UNDERGROUND_SOURCES = sum(len(s) for s in UNDERGROUND_SOURCES.values())

if __name__ == "__main__":
    print("🔮 Underground Reddit RSS Sources")
    print("=" * 70)
    print(f"\nTotal sources: {TOTAL_UNDERGROUND_SOURCES}\n")
    
    for category, sources in UNDERGROUND_SOURCES.items():
        print(f"{category.upper()}: {len(sources)} subreddits")
        for src in sources[:3]:
            sub = src.split('/r/')[1].split('/')[0]
            print(f"  • r/{sub}")
        if len(sources) > 3:
            print(f"  ... and {len(sources) - 3} more")
        print()
