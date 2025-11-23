import logging

logger = logging.getLogger(__name__)
"""
EDGY RSS Sources - No Mainstream Bullshit
Only content with actual edge and actionable intelligence
"""

EDGY_SOURCES = {
    "crypto_alpha": {
        "feeds": [
            "https://cointelegraph.com/rss",
            "https://decrypt.co/feed",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://thedefiant.io/feed/",
            "https://newsletter.banklesshq.com/feed",
        ],
        "topics": ["DeFi", "Crypto", "Blockchain", "NFTs", "Web3"],
    },
    "underground_tech": {
        "feeds": [
            "https://www.reddit.com/r/netsec/.rss",
            "https://www.reddit.com/r/privacy/.rss",
            "https://www.reddit.com/r/darknet/.rss",
            "https://www.reddit.com/r/onions/.rss",
            "https://krebsonsecurity.com/feed/",
            "https://www.schneier.com/blog/atom.xml",
            "https://blog.torproject.org/feed",
        ],
        "topics": ["Security", "Privacy", "Hacking", "Dark Web", "Anonymity"],
    },
    "conspiracy_esoteric": {
        "feeds": [
            "https://www.reddit.com/r/conspiracy/.rss",
            "https://www.reddit.com/r/conspiracytheories/.rss",
            "https://www.reddit.com/r/HighStrangeness/.rss",
            "https://www.reddit.com/r/UFOs/.rss",
            "https://www.reddit.com/r/occult/.rss",
            "https://www.reddit.com/r/AlternativeHistory/.rss",
            "https://www.reddit.com/r/C_S_T/.rss",
            "https://vigilantcitizen.com/feed/",
        ],
        "topics": ["Conspiracy", "Occult", "UFOs", "Alternative", "Esoteric"],
    },
    "financial_edge": {
        "feeds": [
            "https://www.zerohedge.com/feed/all",
            "https://www.reddit.com/r/wallstreetbets/.rss",
            "https://www.reddit.com/r/Superstonk/.rss",
            "https://www.reddit.com/r/options/.rss",
            "https://www.reddit.com/r/investing/.rss",
            "https://www.bloomberg.com/feed/podcast/odd-lots",
        ],
        "topics": ["Finance", "Trading", "Markets", "Economics", "Stocks"],
    },
    "ai_cutting_edge": {
        "feeds": [
            "https://www.reddit.com/r/MachineLearning/.rss",
            "https://www.reddit.com/r/artificial/.rss",
            "https://www.reddit.com/r/LocalLLaMA/.rss",
            "https://www.reddit.com/r/singularity/.rss",
            "https://blog.openai.com/rss/",
            "https://www.anthropic.com/index.xml",
        ],
        "topics": ["AI", "ML", "LLM", "AGI", "Automation"],
    },
    "longevity_biohacking": {
        "feeds": [
            "https://www.reddit.com/r/longevity/.rss",
            "https://www.reddit.com/r/Biohackers/.rss",
            "https://www.reddit.com/r/Nootropics/.rss",
            "https://www.reddit.com/r/QuantifiedSelf/.rss",
            "https://www.lifespan.io/feed/",
        ],
        "topics": ["Longevity", "Biohacking", "Nootropics", "Health", "Enhancement"],
    },
    "startup_intelligence": {
        "feeds": [
            "https://news.ycombinator.com/rss",
            "https://www.reddit.com/r/startups/.rss",
            "https://www.reddit.com/r/Entrepreneur/.rss",
            "https://www.indiehackers.com/feed",
            "https://blog.ycombinator.com/feed/",
        ],
        "topics": ["Startups", "Business", "Entrepreneurship", "Growth", "SaaS"],
    },
    "advanced_crypto_defi": {
        "feeds": [
            "https://www.reddit.com/r/CryptoCurrency/.rss",
            "https://www.reddit.com/r/defi/.rss",
            "https://www.reddit.com/r/ethfinance/.rss",
            "https://www.reddit.com/r/CryptoMoonShots/.rss",
            "https://www.reddit.com/r/SatoshiStreetBets/.rss",
            "https://www.reddit.com/r/0xPolygon/.rss",
            "https://www.reddit.com/r/solana/.rss",
            "https://www.reddit.com/r/cardano/.rss",
        ],
        "topics": ["DeFi", "Yield", "Staking", "Airdrops", "Gems"],
    },
    "psychedelics_consciousness": {
        "feeds": [
            "https://www.reddit.com/r/Psychonaut/.rss",
            "https://www.reddit.com/r/RationalPsychonaut/.rss",
            "https://www.reddit.com/r/DMT/.rss",
            "https://www.reddit.com/r/LSD/.rss",
            "https://www.maps.org/news/feed",
        ],
        "topics": ["Psychedelics", "Consciousness", "DMT", "Meditation", "Expansion"],
    },
    "alternative_news": {
        "feeds": [
            "https://www.reddit.com/r/Anarchism/.rss",
            "https://www.reddit.com/r/collapse/.rss",
            "https://www.reddit.com/r/CriticalTheory/.rss",
            "https://www.reddit.com/r/LateStageCapitalism/.rss",
            "https://theintercept.com/feed/",
        ],
        "topics": ["Alternative", "Critical", "System", "Revolution", "Truth"],
    },
}


def get_all_edgy_sources():
    """Get all edgy RSS feeds"""
    all_feeds = []
    for category, data in EDGY_SOURCES.items():
        for feed_url in data["feeds"]:
            all_feeds.append(
                {"url": feed_url, "category": category, "topics": data["topics"]}
            )
    return all_feeds


def get_feeds_by_category(category: str):
    """Get feeds for specific category"""
    if category in EDGY_SOURCES:
        return EDGY_SOURCES[category]["feeds"]
    return []


# Total sources count
TOTAL_EDGY_SOURCES = sum(len(cat["feeds"]) for cat in EDGY_SOURCES.values())

logger.info(
    f"Loaded {TOTAL_EDGY_SOURCES} edgy sources across {len(EDGY_SOURCES)} categories"
)
