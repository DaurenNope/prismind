"""
Multi-Topic Content Sources
Comprehensive RSS feeds across diverse categories
"""

# ============================================
# TECHNOLOGY & ENGINEERING
# ============================================
TECHNOLOGY_SOURCES = {
    'rss': [
        'https://news.ycombinator.com/rss',
        'https://techcrunch.com/feed/',
        'https://www.theverge.com/rss/index.xml',
        'https://feeds.arstechnica.com/arstechnica/index',
        'https://www.wired.com/feed/rss',
        'https://www.engadget.com/rss.xml',
        'https://www.technologyreview.com/feed/',
        'https://www.zdnet.com/news/rss.xml',
        'https://venturebeat.com/feed/',
    ],
    'reddit': [
        # Advanced Web3/Blockchain Tech (not basic crypto)
        'https://www.reddit.com/r/Solana/.rss',
        'https://www.reddit.com/r/sui/.rss',
        'https://www.reddit.com/r/Aptos/.rss',
        'https://www.reddit.com/r/cosmosnetwork/.rss',
        'https://www.reddit.com/r/Near/.rss',
        'https://www.reddit.com/r/Algorand/.rss',
        'https://www.reddit.com/r/polkadot_network/.rss',
        'https://www.reddit.com/r/avalanche/.rss',
        'https://www.reddit.com/r/Cardano_ELI5/.rss',
        # Web3 Dev & Tech
        'https://www.reddit.com/r/ethdev/.rss',
        'https://www.reddit.com/r/rust/.rss',
        'https://www.reddit.com/r/solidity/.rss',
        'https://www.reddit.com/r/CosmWasm/.rss',
        'https://www.reddit.com/r/Move_language/.rss',
        # Advanced DeFi/Protocol Dev
        'https://www.reddit.com/r/UniSwap/.rss',
        'https://www.reddit.com/r/Aave_Official/.rss',
        'https://www.reddit.com/r/MakerDAO/.rss',
        'https://www.reddit.com/r/Yearn/.rss',
        'https://www.reddit.com/r/synthetix_io/.rss',
        # Layer 2 & Scaling
        'https://www.reddit.com/r/Arbitrum/.rss',
        'https://www.reddit.com/r/optimismEthereum/.rss',
        'https://www.reddit.com/r/0xPolygon/.rss',
        'https://www.reddit.com/r/zkSync/.rss',
        'https://www.reddit.com/r/StarkNet/.rss',
        # Infrastructure & Tools
        'https://www.reddit.com/r/IPFS/.rss',
        'https://www.reddit.com/r/Chainlink/.rss',
        'https://www.reddit.com/r/TheGraph/.rss',
        'https://www.reddit.com/r/Filecoin/.rss',
    ],
    'topics': ['AI', 'ML', 'Programming', 'DevOps', 'Cloud', 'Cybersecurity', 'Web3', 'Blockchain Dev', 'DeFi Protocols', 'Layer 2']
}

# ============================================
# BUSINESS & FINANCE
# ============================================
BUSINESS_SOURCES = {
    'rss': [
        'https://feeds.bloomberg.com/markets/news.rss',
        'https://www.forbes.com/innovation/feed/',
        'https://www.inc.com/rss/',
        'https://hbr.org/feed',
        'https://www.fastcompany.com/latest/rss',
        'https://www.entrepreneur.com/latest.rss',
        'https://www.businessinsider.com/rss',
        'https://fortune.com/feed/',
        'https://www.cnbc.com/id/100003114/device/rss/rss.html',
        'https://www.marketwatch.com/rss/topstories',
        # Crypto Business/Finance (not basic price talk)
        'https://www.coindesk.com/arc/outboundfeeds/rss/',
        'https://cointelegraph.com/rss',
        'https://decrypt.co/feed',
        'https://www.theblock.co/rss.xml',
    ],
    'reddit': [
        # Advanced Crypto Finance/Trading
        'https://www.reddit.com/r/CryptoTechnology/.rss',  # Tech focus, not price
        'https://www.reddit.com/r/defi/.rss',
        'https://www.reddit.com/r/CryptoCurrencyTrading/.rss',
        'https://www.reddit.com/r/ethfinance/.rss',
        'https://www.reddit.com/r/CryptoMarkets/.rss',
        # Web3 Business/Startups
        'https://www.reddit.com/r/web3/.rss',
        'https://www.reddit.com/r/NFTsMarketplace/.rss',
        'https://www.reddit.com/r/DAOTrader/.rss',
    ],
    'topics': ['Startups', 'Investing', 'Business', 'Finance', 'Entrepreneurship', 'Economics', 'Leadership', 'Crypto Finance', 'DeFi', 'Web3 Business']
}

# ============================================
# SCIENCE & RESEARCH
# ============================================
SCIENCE_SOURCES = {
    'rss': [
        'https://www.nature.com/nature.rss',
        'https://www.sciencemag.org/rss/news_current.xml',
        'https://www.scientificamerican.com/feed/',
        'https://phys.org/rss-feed/',
        'https://www.newscientist.com/feed/home/',
        'https://www.space.com/feeds/all',
        'https://www.livescience.com/feeds/all',
        'https://www.sciencedaily.com/rss/all.xml',
        'https://www.nasa.gov/rss/dyn/breaking_news.rss',
    ],
    'topics': ['Science', 'Research', 'Space', 'Physics', 'Biology', 'Chemistry', 'Climate', 'Astronomy']
}

# ============================================
# HEALTH & WELLNESS
# ============================================
HEALTH_SOURCES = {
    'rss': [
        'https://www.health.harvard.edu/feed',
        'https://www.medicalnewstoday.com/rss/news.xml',
        'https://www.healthline.com/rss',
        'https://www.webmd.com/rss/rss.aspx?RSSSource=RSS_PUBLIC',
        'https://www.mayoclinic.org/rss',
        'https://www.nih.gov/feeds/news.xml',
        'https://www.who.int/feeds/entity/mediacentre/news/en/rss.xml',
    ],
    'topics': ['Health', 'Fitness', 'Nutrition', 'Medicine', 'Mental Health', 'Wellness']
}

# ============================================
# CULTURE & ARTS
# ============================================
CULTURE_SOURCES = {
    'rss': [
        'https://pitchfork.com/rss/news/',
        'https://www.theguardian.com/culture/rss',
        'https://www.nytimes.com/svc/collections/v1/publish/https://www.nytimes.com/section/arts/rss.xml',
        'https://lithub.com/feed/',
        'https://www.polygon.com/rss/index.xml',
        'https://www.vulture.com/rss/index.xml',
        'https://www.hollywoodreporter.com/feed/',
        'https://variety.com/feed/',
    ],
    'topics': ['Movies', 'Music', 'Books', 'Gaming', 'TV', 'Art', 'Design', 'Culture']
}

# ============================================
# LIFESTYLE
# ============================================
LIFESTYLE_SOURCES = {
    'rss': [
        'https://www.bonappetit.com/feed/rss',
        'https://www.seriouseats.com/feed',
        'https://feeds.feedburner.com/lonelyplanet/QTYl',
        'https://www.cntraveler.com/feed/rss',
        'https://www.outsideonline.com/rss/',
        'https://www.apartmenttherapy.com/main.rss',
        'https://lifehacker.com/rss',
    ],
    'topics': ['Cooking', 'Travel', 'Food', 'Productivity', 'Lifestyle', 'Home']
}

# ============================================
# NEWS & CURRENT EVENTS
# ============================================
NEWS_SOURCES = {
    'rss': [
        'https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml',
        'https://www.theguardian.com/world/rss',
        'https://www.bbc.com/news/world/rss.xml',
        'https://www.reuters.com/rssFeed/topNews',
        'https://www.aljazeera.com/xml/rss/all.xml',
        'https://www.npr.org/rss/rss.php?id=1001',
    ],
    'topics': ['News', 'World', 'Politics', 'Society', 'Current Events']
}

# ============================================
# SPORTS & FITNESS
# ============================================
SPORTS_SOURCES = {
    'rss': [
        'https://www.espn.com/espn/rss/news',
        'https://www.si.com/rss/si_topstories.rss',
        'https://www.bleacherreport.com/rss',
        'https://www.theathletic.com/rss/',
    ],
    'topics': ['Sports', 'Fitness', 'Athletics', 'Football', 'Basketball', 'Soccer']
}

# ============================================
# PERSONAL DEVELOPMENT & PSYCHOLOGY
# ============================================
PERSONAL_DEVELOPMENT_SOURCES = {
    'rss': [
        'https://www.psychologytoday.com/us/blog/feed',
        'https://tinybuddha.com/feed/',
        'https://zenhabits.net/feed/',
        'https://www.mindbodygreen.com/rss',
        'https://www.Success.com/feed/',
        'https://jamesclear.com/feed',
        'https://markmanson.net/feed',
        'https://tim.blog/feed/',
        'https://www.brainpickings.org/feed/',
    ],
    'topics': ['Psychology', 'Self-Improvement', 'Personal Growth', 'Mindfulness', 'Habits', 'Mental Health', 'Motivation']
}

# ============================================
# RELATIONSHIPS & DATING
# ============================================
RELATIONSHIPS_SOURCES = {
    'rss': [
        'https://www.psychologytoday.com/us/blog/between-you-and-me/feed',
        'https://www.gottman.com/blog/feed/',
        'https://www.esther-perel.com/feed',
        'https://greatergood.berkeley.edu/feeds/rss/greater_good',
    ],
    'topics': ['Relationships', 'Dating', 'Love', 'Communication', 'Marriage', 'Family', 'Intimacy']
}

# ============================================
# SPIRITUALITY & PHILOSOPHY
# ============================================
SPIRITUALITY_SOURCES = {
    'rss': [
        'https://www.lionsroar.com/feed/',
        'https://www.tricycle.org/feed/',
        'https://aeon.co/feed.rss',
        'https://philosophynow.org/rss',
        'https://dailystoic.com/feed/',
        'https://www.awakin.org/rss/inspiration.xml',
        # Reddit philosophy & spirituality
        'https://www.reddit.com/r/Philosophy/.rss',
        'https://www.reddit.com/r/Showerthoughts/.rss',
        'https://www.reddit.com/r/stoicism/.rss',
        'https://www.reddit.com/r/awakened/.rss',
        'https://www.reddit.com/r/spirituality/.rss',
        'https://www.reddit.com/r/DeepThoughts/.rss',
    ],
    'topics': ['Spirituality', 'Philosophy', 'Buddhism', 'Meditation', 'Wisdom', 'Consciousness', 'Stoicism', 'Meaning']
}

# ============================================
# LIFE STORIES & NARRATIVES
# ============================================
LIFE_STORIES_SOURCES = {
    'rss': [
        'https://humanparts.medium.com/feed',
        'https://longreads.com/feed/',
        'https://narratively.com/feed/',
        'https://www.thisamericanlife.org/podcast/rss.xml',
        'https://storycorps.org/podcast/feed/',
        'https://www.themoth.org/podcast-rss',
    ],
    'topics': ['Life Stories', 'Narratives', 'Personal Essays', 'Memoirs', 'Human Interest', 'Biography']
}

# ============================================
# CREATIVITY & WRITING
# ============================================
CREATIVITY_SOURCES = {
    'rss': [
        'https://lithub.com/feed/',
        'https://www.brainpickings.org/feed/',
        'https://austinkleon.com/feed/',
        'https://medium.com/creators-hub/feed',
        'https://writingcooperative.com/feed',
    ],
    'topics': ['Writing', 'Creativity', 'Art', 'Literature', 'Poetry', 'Storytelling']
}

# ============================================
# PARENTING & FAMILY
# ============================================
PARENTING_SOURCES = {
    'rss': [
        'https://www.parentingscience.com/feed',
        'https://www.mother.ly/feed',
        'https://www.fatherly.com/feed/',
        'https://www.parents.com/feeds/latest/',
    ],
    'topics': ['Parenting', 'Family', 'Children', 'Education', 'Child Development']
}

# ============================================
# ADVENTURE & NATURE
# ============================================
ADVENTURE_SOURCES = {
    'rss': [
        'https://www.outsideonline.com/rss/',
        'https://www.nationalgeographic.com/pages/topic/latest-stories/feed/',
        'https://www.adventure-journal.com/feed/',
        'https://www.rei.com/blog/feed',
    ],
    'topics': ['Adventure', 'Nature', 'Outdoors', 'Hiking', 'Environment', 'Wildlife', 'Conservation']
}

# ============================================
# MYSTERY & UNEXPLAINED (THE FUN STUFF!)
# ============================================
MYSTERY_SOURCES = {
    'rss': [
        'https://mysteriousuniverse.org/feed/',
        'https://www.unexplained-mysteries.com/rss/news.xml',
        'https://theoccultmuseum.com/feed/',
        'https://www.ancient-origins.net/rss.xml',
        'https://www.coasttocoastam.com/rss/articles/',
        # Reddit underground (non-mainstream!)
        'https://www.reddit.com/r/UnresolvedMysteries/.rss',
        'https://www.reddit.com/r/HighStrangeness/.rss',
        'https://www.reddit.com/r/Glitch_in_the_Matrix/.rss',
        'https://www.reddit.com/r/Paranormal/.rss',
        'https://www.reddit.com/r/UFOs/.rss',
        'https://www.reddit.com/r/aliens/.rss',
        'https://www.reddit.com/r/Missing411/.rss',
        'https://www.reddit.com/r/Humanoidencounters/.rss',
    ],
    'topics': ['Mystery', 'Unexplained', 'Paranormal', 'UFOs', 'Ancient Mysteries', 'Occult', 'Strange Phenomena']
}

# ============================================
# CONSPIRACY & ALTERNATIVE
# ============================================
CONSPIRACY_SOURCES = {
    'rss': [
        'https://vigilantcitizen.com/feed/',
        'https://www.zerohedge.com/fullrss2.xml',
        'https://www.activistpost.com/feed',
        # Reddit underground
        'https://www.reddit.com/r/conspiracy/.rss',
        'https://www.reddit.com/r/conspiracytheories/.rss',
        'https://www.reddit.com/r/AlternativeHistory/.rss',
        'https://www.reddit.com/r/C_S_T/.rss',  # Critical Shower Thoughts
    ],
    'topics': ['Conspiracy', 'Alternative News', 'Hidden Truth', 'Deep State', 'Cover-ups', 'Revelations']
}

# ============================================
# HUMOR & SATIRE
# ============================================
HUMOR_SOURCES = {
    'rss': [
        'https://theonion.com/rss',
        'https://www.mcsweeneys.net/feeds/rss',
        'https://www.cracked.com/feeds/rss',
        'https://www.thebeaverton.com/feed/',
        'https://medium.com/feed/@humordaily',
    ],
    'topics': ['Humor', 'Satire', 'Comedy', 'Funny', 'Parody', 'Jokes']
}

# ============================================
# ESOTERIC & SPIRITUAL (Angels, Demons, etc.)
# ============================================
ESOTERIC_SOURCES = {
    'rss': [
        'https://www.gaia.com/lp/content/rss/',
        'https://in5d.com/feed/',
        'https://www.bibliotecapleyades.net/rss.xml',
        'https://www.collective-evolution.com/feed/',
        # Reddit underground - the deep stuff!
        'https://www.reddit.com/r/occult/.rss',
        'https://www.reddit.com/r/Esoteric/.rss',
        'https://www.reddit.com/r/Hermetics/.rss',
        'https://www.reddit.com/r/Alchemy/.rss',
        'https://www.reddit.com/r/Psychonaut/.rss',
        'https://www.reddit.com/r/Shamanism/.rss',
        'https://www.reddit.com/r/energy_work/.rss',
        'https://www.reddit.com/r/Soulnexus/.rss',
    ],
    'topics': ['Angels', 'Demons', 'Metaphysics', 'Esoteric', 'Energy', 'Dimensions', 'Mysticism', 'Sacred Geometry']
}

# ============================================
# WEIRD & INTERESTING
# ============================================
WEIRD_SOURCES = {
    'rss': [
        'https://www.atlasobscura.com/feeds/latest',
        'https://boingboing.net/feed',
        'https://kottke.org/feed/',
        'https://www.mentalfloss.com/feed',
        # Reddit weird
        'https://www.reddit.com/r/Weird/.rss',
        'https://www.reddit.com/r/Damnthatsinteresting/.rss',
        'https://www.reddit.com/r/Interestingasfuck/.rss',
        'https://www.reddit.com/r/Creepy/.rss',
    ],
    'topics': ['Weird', 'Interesting', 'Oddities', 'Curiosities', 'Strange', 'Bizarre', 'Fascinating']
}

# ============================================
# MASTER SOURCE REGISTRY
# ============================================
ALL_SOURCES_BY_CATEGORY = {
    'technology': TECHNOLOGY_SOURCES,
    'business': BUSINESS_SOURCES,
    'science': SCIENCE_SOURCES,
    'health': HEALTH_SOURCES,
    'culture': CULTURE_SOURCES,
    'lifestyle': LIFESTYLE_SOURCES,
    'news': NEWS_SOURCES,
    'sports': SPORTS_SOURCES,
    'personal_development': PERSONAL_DEVELOPMENT_SOURCES,
    'relationships': RELATIONSHIPS_SOURCES,
    'spirituality': SPIRITUALITY_SOURCES,
    'life_stories': LIFE_STORIES_SOURCES,
    'creativity': CREATIVITY_SOURCES,
    'parenting': PARENTING_SOURCES,
    'adventure': ADVENTURE_SOURCES,
    'mystery': MYSTERY_SOURCES,
    'conspiracy': CONSPIRACY_SOURCES,
    'humor': HUMOR_SOURCES,
    'esoteric': ESOTERIC_SOURCES,
    'weird': WEIRD_SOURCES,
}

# ============================================
# TOPIC TO CATEGORY MAPPING
# ============================================
TOPIC_CATEGORY_MAP = {
    # Technology
    'AI': 'technology',
    'ML': 'technology',
    'Machine Learning': 'technology',
    'Programming': 'technology',
    'DevOps': 'technology',
    'Cloud': 'technology',
    'Cybersecurity': 'technology',
    'Web3': 'technology',
    'Blockchain': 'technology',
    
    # Business
    'Startups': 'business',
    'Business': 'business',
    'Finance': 'business',
    'Investing': 'business',
    'Entrepreneurship': 'business',
    'Economics': 'business',
    'Leadership': 'business',
    'Management': 'business',
    
    # Science
    'Science': 'science',
    'Research': 'science',
    'Space': 'science',
    'Physics': 'science',
    'Biology': 'science',
    'Chemistry': 'science',
    'Climate': 'science',
    'Astronomy': 'science',
    
    # Health
    'Health': 'health',
    'Fitness': 'health',
    'Nutrition': 'health',
    'Medicine': 'health',
    'Mental Health': 'health',
    'Wellness': 'health',
    
    # Culture
    'Movies': 'culture',
    'Music': 'culture',
    'Books': 'culture',
    'Gaming': 'culture',
    'TV': 'culture',
    'Art': 'culture',
    'Design': 'culture',
    'Culture': 'culture',
    
    # Lifestyle
    'Cooking': 'lifestyle',
    'Travel': 'lifestyle',
    'Food': 'lifestyle',
    'Productivity': 'lifestyle',
    'Lifestyle': 'lifestyle',
    'Home': 'lifestyle',
    
    # News
    'News': 'news',
    'World': 'news',
    'Politics': 'news',
    'Society': 'news',
    'Current Events': 'news',
    
    # Sports
    'Sports': 'sports',
    'Athletics': 'sports',
    'Football': 'sports',
    'Basketball': 'sports',
    'Soccer': 'sports',
    
    # Personal Development
    'Psychology': 'personal_development',
    'Self-Improvement': 'personal_development',
    'Personal Growth': 'personal_development',
    'Mindfulness': 'personal_development',
    'Habits': 'personal_development',
    'Motivation': 'personal_development',
    
    # Relationships
    'Relationships': 'relationships',
    'Dating': 'relationships',
    'Love': 'relationships',
    'Communication': 'relationships',
    'Marriage': 'relationships',
    'Family': 'relationships',
    'Intimacy': 'relationships',
    
    # Spirituality
    'Spirituality': 'spirituality',
    'Philosophy': 'spirituality',
    'Buddhism': 'spirituality',
    'Meditation': 'spirituality',
    'Wisdom': 'spirituality',
    'Consciousness': 'spirituality',
    'Stoicism': 'spirituality',
    'Meaning': 'spirituality',
    
    # Life Stories
    'Life Stories': 'life_stories',
    'Narratives': 'life_stories',
    'Personal Essays': 'life_stories',
    'Memoirs': 'life_stories',
    'Human Interest': 'life_stories',
    'Biography': 'life_stories',
    
    # Creativity
    'Writing': 'creativity',
    'Creativity': 'creativity',
    'Literature': 'creativity',
    'Poetry': 'creativity',
    'Storytelling': 'creativity',
    
    # Parenting
    'Parenting': 'parenting',
    'Children': 'parenting',
    'Child Development': 'parenting',
    
    # Adventure
    'Adventure': 'adventure',
    'Nature': 'adventure',
    'Outdoors': 'adventure',
    'Hiking': 'adventure',
    'Environment': 'adventure',
    'Wildlife': 'adventure',
    'Conservation': 'adventure',
    
    # Mystery
    'Mystery': 'mystery',
    'Unexplained': 'mystery',
    'Paranormal': 'mystery',
    'UFOs': 'mystery',
    'Ancient Mysteries': 'mystery',
    'Occult': 'mystery',
    'Strange Phenomena': 'mystery',
    
    # Conspiracy
    'Conspiracy': 'conspiracy',
    'Alternative News': 'conspiracy',
    'Hidden Truth': 'conspiracy',
    'Deep State': 'conspiracy',
    'Cover-ups': 'conspiracy',
    'Revelations': 'conspiracy',
    
    # Humor
    'Humor': 'humor',
    'Satire': 'humor',
    'Comedy': 'humor',
    'Funny': 'humor',
    'Parody': 'humor',
    'Jokes': 'humor',
    
    # Esoteric
    'Angels': 'esoteric',
    'Demons': 'esoteric',
    'Metaphysics': 'esoteric',
    'Esoteric': 'esoteric',
    'Energy': 'esoteric',
    'Dimensions': 'esoteric',
    'Mysticism': 'esoteric',
    'Sacred Geometry': 'esoteric',
    
    # Weird
    'Weird': 'weird',
    'Interesting': 'weird',
    'Oddities': 'weird',
    'Curiosities': 'weird',
    'Strange': 'weird',
    'Bizarre': 'weird',
    'Fascinating': 'weird',
}

# ============================================
# DEFAULT USER TOPICS (MAXIMUM DIVERSITY!)
# ============================================
DEFAULT_TOPICS = [
    # Tech (more now!)
    'AI', 'ML', 'Programming', 'Startups', 'Web3',
    
    # Business
    'Entrepreneurship', 'Investing',
    
    # Science & Mystery
    'Science', 'Space', 'Ancient Mysteries',
    
    # Health & Wellness
    'Health', 'Fitness', 'Mental Health',
    
    # Personal Development
    'Psychology', 'Self-Improvement', 'Mindfulness', 'Habits',
    
    # Relationships
    'Relationships', 'Dating', 'Communication',
    
    # Spirituality & Esoteric (THE GOOD STUFF!)
    'Spirituality', 'Philosophy', 'Meditation', 'Angels', 'Demons', 'Mysticism',
    
    # Life & Stories
    'Life Stories', 'Personal Essays', 'Human Interest',
    
    # Creativity
    'Writing', 'Creativity',
    
    # Culture & Entertainment
    'Movies', 'Books', 'Music', 'Comedy',
    
    # Mystery & Unexplained (PEOPLE LOVE THIS!)
    'Mystery', 'Unexplained', 'Paranormal', 'UFOs',
    
    # Alternative & Conspiracy (CONTROVERSIAL BUT ENGAGING!)
    'Conspiracy', 'Alternative News', 'Hidden Truth',
    
    # Humor (EVERYONE NEEDS LAUGHS!)
    'Humor', 'Satire', 'Funny',
    
    # Weird & Fascinating
    'Weird', 'Bizarre', 'Fascinating',
    
    # Lifestyle
    'Travel', 'Adventure',
    
    # News
    'Current Events'
]


def get_sources_for_topics(topics: list) -> dict:
    """
    Get RSS sources relevant to user's topics
    
    Args:
        topics: List of topic strings (e.g., ['AI', 'Health', 'Travel'])
    
    Returns:
        Dictionary with 'rss' list of feed URLs
    """
    sources = {'rss': set(), 'topics': set()}
    
    for topic in topics:
        # Map topic to category
        category = TOPIC_CATEGORY_MAP.get(topic)
        
        if category and category in ALL_SOURCES_BY_CATEGORY:
            # Add RSS feeds from this category
            category_sources = ALL_SOURCES_BY_CATEGORY[category]
            sources['rss'].update(category_sources['rss'])
            sources['topics'].update(category_sources['topics'])
    
    # Convert sets to lists
    return {
        'rss': list(sources['rss']),
        'topics': list(sources['topics'])
    }


def get_all_available_topics() -> list:
    """Get all available topics across all categories"""
    all_topics = set()
    for category_data in ALL_SOURCES_BY_CATEGORY.values():
        all_topics.update(category_data['topics'])
    return sorted(list(all_topics))


def get_categories() -> list:
    """Get all available categories"""
    return list(ALL_SOURCES_BY_CATEGORY.keys())


def get_category_info(category: str) -> dict:
    """Get information about a specific category"""
    if category in ALL_SOURCES_BY_CATEGORY:
        cat_data = ALL_SOURCES_BY_CATEGORY[category]
        return {
            'category': category,
            'rss_count': len(cat_data['rss']),
            'topics': cat_data['topics'],
            'sources': cat_data['rss']
        }
    return None
