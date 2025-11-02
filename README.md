# 🧠 PrisMind - Autonomous Intelligence System

**AI-powered content discovery and curation system with zero manual bookmarking**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-21%2F23%20passing-brightgreen.svg)](./tests/)

---

## 🎯 What is PrisMind?

PrisMind is an **autonomous intelligence pipeline** that discovers, analyzes, and curates high-value content from 60+ curated sources across crypto, hacking, conspiracy, AI, and alternative news — **with zero mainstream BS**.

### Key Features

✅ **Autonomous Discovery** - Collects from 60 edgy RSS sources automatically  
✅ **Smart Curation** - AI-powered quality filtering and categorization  
✅ **Intelligent Learning** - Learns from your dismissals and saves  
✅ **Telegram Bot** - Full control via 13 bot commands  
✅ **Web Dashboard** - Beautiful Streamlit UI with real-time feeds  
✅ **Multi-Source** - RSS, Reddit, Telegram, GitHub trending  
✅ **Zero Mainstream** - No Amazon deals, lifestyle, or celebrity fluff  

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Supabase account (free tier works)
- Telegram bot token (optional, for bot features)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/prismind.git
cd prismind

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for Twitter/Threads scraping)
python -m playwright install chromium
```

### Configuration

1. **Copy environment template:**
```bash
cp .env.example .env
```

2. **Configure `.env` with your credentials:**
```env
# Supabase (Required)
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

# Telegram Bot (Optional)
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Reddit (Optional - for bookmarks)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=prismind:v1.0

# Twitter (Optional - for bookmarks)
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
```

3. **Set up Supabase database:**
```sql
-- Run this in Supabase SQL Editor
-- Creates discoveries table with dismissed field

CREATE TABLE discoveries (
    id BIGSERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    source TEXT NOT NULL,
    category TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    dismissed BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_discoveries_dismissed ON discoveries(dismissed);
CREATE INDEX idx_discoveries_created_at ON discoveries(created_at DESC);
```

---

## 📖 Usage

### Web Dashboard

```bash
# Start web UI
streamlit run src/web/app.py

# Or use convenience script
./start_web.sh
```

Access at: `http://localhost:8501`

**Dashboard Features:**
- 📰 **Discoveries Tab** - RSS + Reddit + GitHub feeds
- 🇷🇺 **Telegram Tab** - Russian crypto intelligence
- 💾 **Bookmarks Tab** - Saved Twitter/Reddit posts
- 🤖 **Automation Tab** - Schedule collections
- 📊 **Analytics** - Content insights and trends
 - 📝 **Publishing** (Mimesis) - Personas, queue, scheduler, posting analytics
  - Flow: Generate → Edit/Approve → Schedule → Post → Analytics

### Publishing (Mimesis)

Posting methods:
- Twitter: Twitter API (Tweepy) or Playwright fallback
- Threads: Playwright (browser automation)
- Telegram: Bot API

Tabs included:
- Overview: Ready and due counts
- Queue: Create scheduled posts manually or Generate transformations from posts
- Editor: Review/edit transformations; Approve → Schedule
- Scheduler: Post due items, mark posted
- Analytics: Recent `posted_content`

Apply Supabase SQL migration in `migrations/2025_10_31_mimesis.sql` to create required tables.

### Telegram Bot

```bash
# Start bot
python src/services/telegram_bot.py

# Or use script
./run_telegram_bot.sh
```

**Bot Commands:**
```
/start       - Initialize bot
/help        - Show all commands
/status      - System status
/collect     - Run collection manually
/latest [N]  - Show N latest items
/search      - Search discoveries
/ask         - Ask research question
/recommend   - Get personalized recommendations
/curate      - Curate by topic
```

### One-Click Collection

```bash
# Run full autonomous discovery
python run_full_collection.py
```

Collects from:
- 60 edgy RSS feeds
- Reddit crypto/conspiracy subreddits
- Telegram Russian crypto channels
- Stores in Supabase with quality scoring

---

## 🎨 System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   PRISMIND PIPELINE                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │   SOURCES    │───▶│   ANALYSIS   │───▶│ DATABASE │ │
│  └──────────────┘    └──────────────┘    └──────────┘ │
│   • Twitter/Reddit/Threads   • Essential AI fields     │
│   • Telegram channels        • Incremental + dedupe    │
│   • GitHub trending          • Deterministic scoring   │
│   • RSS (curated)            Supabase + SQLite cache   │
│                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────┐ │
│  │     UI       │◀───│   LEARNING   │◀───│   USER   │ │
│  └──────────────┘    └──────────────┘    └──────────┘ │
│   • Web (Streamlit)    • Preferences        Actions:  │
│   • Bot (Telegram)     • Patterns           • Save    │
│                        • Trends             • Dismiss  │
│                                             • Skip     │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure (lean)

```
prismind/
├── src/
│   ├── core/
│   │   ├── extraction/          # Content collectors
│   │   │   ├── edgy_sources.py  # 60 curated RSS sources
│   │   │   ├── reddit_extractor.py
│   │   │   ├── twitter_extractor_playwright.py
│   │   │   └── threads_extractor.py
│   │   ├── analysis/            # AI analysis
│   │   │   ├── intelligent_content_analyzer.py
│   │   │   └── value_scorer.py
│   │   └── learning/            # Smart curation
│   │       └── intelligent_curator.py
│   │
│   ├── services/
│   │   ├── autonomous_discovery.py      # Discovery engine
│   │   ├── telegram_bot.py              # Bot commands
│   │   └── new_database_manager.py      # SQLite DB operations
│   │
│   └── web/
│       ├── app.py               # Main Streamlit app
│       └── components/          # UI components
│           ├── discoveries_tab.py
│           └── telegram_tab.py
│
├── tests/
│   ├── test_discovery_pipeline.py  # Integration tests
│   └── test_collectors.py          # Unit tests
│
├── run_full_collection.py      # One-click collection script
├── archive/                    # Moved: legacy scripts/assets
├── docs/archive/               # Moved: legacy notes/docs
├── requirements.txt             # Python dependencies
└── .env.example                 # Configuration template
```

---

## 🔥 Content Sources

### 10 Edgy Categories (60 Sources Total)

1. **Crypto Alpha** (5 feeds) - CoinTelegraph, Decrypt, CoinDesk, Defiant, Bankless
2. **Underground Tech** (7 feeds) - r/netsec, r/privacy, r/darknet, Krebs, Schneier
3. **Conspiracy/Esoteric** (8 feeds) - r/conspiracy, r/HighStrangeness, r/UFOs, r/occult
4. **Financial Edge** (6 feeds) - ZeroHedge, r/wallstreetbets, r/Superstonk
5. **AI Cutting Edge** (6 feeds) - r/MachineLearning, r/LocalLLaMA, OpenAI, Anthropic
6. **Longevity/Biohacking** (5 feeds) - r/longevity, r/Biohackers, r/Nootropics
7. **Startup Intelligence** (5 feeds) - HackerNews, r/startups, IndieHackers
8. **Advanced DeFi** (8 feeds) - r/CryptoCurrency, r/defi, r/ethfinance
9. **Psychedelics** (5 feeds) - r/Psychonaut, r/DMT, MAPS
10. **Alternative News** (5 feeds) - r/collapse, r/Anarchism, The Intercept

**Zero mainstream sources** - No Amazon, lifestyle, entertainment, or celebrity content.

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_discovery_pipeline.py -v
pytest tests/test_collectors.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Coverage:**
- ✅ 21/23 tests passing (91%)
- ✅ Discovery pipeline validation
- ✅ Source structure verification
- ✅ SocialPost schema compliance
- ✅ Database integration

---

## 🎯 Development Phases

### ✅ Phase 1-3: Foundation (COMPLETE)
- Multi-platform collectors (Twitter, Reddit, Threads)
- AI analysis pipeline
- Database integration
- Telegram bot with 13 commands

### ✅ Phase 4: Autonomous Discovery (COMPLETE)
- 60 edgy RSS sources curated
- Autonomous collection system
- Intelligent feed with learning
- Permanent dismiss functionality
- Clean UI with separated tabs

### 🔄 Phase 5: Production Readiness (79% COMPLETE)
- ✅ Security fixes (gitignore, dependencies)
- ✅ Integration tests (21/23 passing)
- ✅ Documentation updates
- 🔄 Remaining: Supabase audit, final verifications

### 🔮 Phase 6: Future Enhancements
- Knowledge base with vector search
- Multi-user support
- Advanced analytics dashboard
- REST API for integrations
- Mobile app

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

**Development Guidelines:**
- Follow existing code style
- Add tests for new features
- Update documentation
- Keep commits atomic and descriptive

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/) for web UI
- Powered by [Supabase](https://supabase.com/) for database
- Uses [Playwright](https://playwright.dev/) for browser automation
- Inspired by the need for **real** intelligence, not mainstream garbage

---

## 📧 Contact

Questions? Issues? Reach out:
- GitHub Issues: [Create an issue](https://github.com/yourusername/prismind/issues)
- Telegram: [@your_username](https://t.me/your_username)

---

**Made with 🧠 by humans who are tired of mainstream content**
