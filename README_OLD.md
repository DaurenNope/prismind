# 🧠 PrisMind - Fixed Social Media Bookmark Collector

> **🚨 MANDATORY**: All developers MUST read and follow [RULES.md](./RULES.md) before making ANY changes.
> 
> **📋 COMPLIANCE**: Use [CHANGE_TEMPLATE.md](./CHANGE_TEMPLATE.md) for all modifications.

PrisMind is a personal intelligence engine that transforms your bookmarked content from Twitter, Reddit, and Threads into a structured, searchable knowledge base.

## 🌟 Key Features

- **Multi-platform Collection**: Collect bookmarks from Twitter, Reddit, and Threads
- **AI-powered Analysis**: Extract insights using Mistral AI, Gemini, and Perplexity
- **Interactive Dashboard**: Explore your data with a Streamlit-based interface
- **Duplicate Detection**: Automatically detect and skip duplicate content
- **Fixed Reliability Issues**: All platforms now work reliably

## 🛠️ Prerequisites

- Python 3.8+
- pip package manager
- Git

## 📦 Installation

```bash
# Clone the repository
git clone <repository-url>
cd prismind

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## ⚙️ Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```bash
   # Twitter cookies (required for Twitter collection)
   TWITTER_COOKIES="your_cookies_here"
   
   # Reddit API credentials (required for Reddit collection)
   REDDIT_CLIENT_ID="your_client_id"
   REDDIT_CLIENT_SECRET="your_client_secret"
   REDDIT_USER_AGENT="your_user_agent"
   
   # Threads cookies (required for Threads collection)
   THREADS_COOKIES="your_cookies_here"
   
   # Supabase credentials (for remote storage)
   SUPABASE_URL="your_supabase_url"
   SUPABASE_KEY="your_supabase_key"
   ```

## 🌐 Environment Variables

- `TWITTER_COOKIES` - Extract from your browser when logged into Twitter
- `REDDIT_CLIENT_ID` - Reddit API client ID
- `REDDIT_CLIENT_SECRET` - Reddit API client secret
- `REDDIT_USER_AGENT` - Reddit API user agent
- `REDDIT_USERNAME` - Reddit username
- `REDDIT_PASSWORD` - Reddit password
- `THREADS_COOKIES` - Extract from your browser when logged into Threads
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase API key

## 🚀 Usage

### Main Entry Point

PrisMind provides a unified command-line interface:

```bash
# Show help and available commands
python main.py --help

# Show version
python main.py --version

# Launch web interface (default)
python main.py web
# or simply
python main.py

# Run collection service
python main.py collect

# Launch dashboard
python main.py dashboard
```

### Collecting Bookmarks

To collect bookmarks from all configured platforms:

```bash
python main.py collect
# or
python main_collector.py
```

This will:
1. Collect bookmarks from all configured platforms
2. Upload new bookmarks to Supabase (skipping duplicates)
3. Show a summary of collected and uploaded items

### Testing Collectors

To test if your collectors are working properly:

```bash
python test_fixed_collectors.py
```

This will:
1. Check environment variables for completeness
2. Test the collection system
3. Show detailed error messages if any collector is not configured correctly

### Running the Web Interface

```bash
python main.py web
# or
streamlit run src/web/app.py
```

## 📁 Code Structure

```
src/
├── core/
│   ├── extraction/              # Platform extractors
│   │   ├── reddit_extractor.py
│   │   ├── twitter_extractor_playwright.py
│   │   ├── threads_extractor.py
│   │   └── social_extractor_base.py
│   ├── analysis/                # AI analysis components
│   ├── research/                # Research and search
│   └── validation/              # Content validation
├── services/
│   ├── collection/              # Collection orchestrator
│   ├── database_operations.py   # Database management
│   └── new_database_manager.py  # Main database manager
├── web/
│   ├── app.py                   # Main Streamlit app
│   └── components/              # UI components
└── supabase_manager.py          # Supabase integration

main.py                          # Main entry point
main_collector.py                # Collection script
test_fixed_collectors.py         # Testing script
.env.example                     # Environment variable template
.env                             # Local environment configuration
requirements.txt                 # Dependencies
README.md                        # This file
```

## 🧪 Testing

The project includes comprehensive testing:

### Test Collection System

```bash
python test_fixed_collectors.py
```

This script will:
1. Check environment variables for completeness
2. Test the collection system
3. Show detailed error messages for troubleshooting

### Test Individual Components

```bash
# Test database connection
python -c "from src.services.new_database_manager import get_database_manager; db = get_database_manager(); print('Database:', db.get_post_count(), 'posts')"

# Test web interface
python -c "from src.web.app import main; print('Web app imports successfully')"

# Test collection orchestrator
python -c "import asyncio; from src.services.collection.collection_orchestrator import run_full_collection; print('Collection system ready')"
```

## 🧩 How It Works

1. **Twitter Collection**:
   - Uses GraphQL API with cookies for authentication
   - Implements pagination to collect more than 20 bookmarks
   - Extracts usernames correctly for proper URL generation

2. **Reddit Collection**:
   - Uses PRAW library with user credentials
   - Implements pagination to collect more than 20 bookmarks

3. **Threads Collection**:
   - Uses GraphQL API with cookies for authentication
   - Automatically discovers working document IDs
   - Collects saved posts

4. **Supabase Upload**:
   - Checks for duplicates based on URL
   - Uploads only new content
   - Stores metadata with each post

## 🧰 Platform-Specific Notes

### Twitter
- Requires cookies for authentication (no username/password)
- Collects up to 500 bookmarks with proper pagination
- Fixed issues with username extraction and GraphQL queries
- See `.env` for required cookie format

### Reddit
- Requires Reddit API credentials
- Collects saved posts and comments
- Works reliably with PRAW library
- Ensure you have the correct user agent format

### Threads
- Requires cookies for authentication
- Automatically discovers working GraphQL document IDs
- Collects up to 500 bookmarks with proper pagination
- See `.env` for required cookie format

## 🛠️ Troubleshooting

### Common Issues

1. **Authentication failures**: 
   - Make sure cookies are current and properly formatted
   - Check that environment variables are set correctly

2. **Rate limiting**:
   - The collector includes built-in delays to respect rate limits
   - If you encounter issues, try reducing the max_bookmarks value

3. **Duplicate content**:
   - The system automatically detects and skips duplicates
   - Seeing 0 uploaded posts may indicate all content is already in the database

### Getting Help

If you continue to experience issues:
1. Check the logs for detailed error messages
2. Verify your credentials are correct and current
3. Ensure you have network connectivity to the platforms

## 🤖 Telegram Bot (Phase 3)

Prerequisites:
- Set `TELEGRAM_BOT_TOKEN` in your environment (or `.env`). The bot now auto-loads `.env`.

Install dependency (if not already installed):

```bash
pip install -r requirements.txt
```

Run the bot:

```bash
python -m src.services.telegram_bot
```

Commands:
- `/start`, `/help` — basics
- `/status` — scraping statistics from `scrape_state_manager`
- `/collect` — triggers multi-platform collection orchestrator
- `/analyze` — analyzes recent posts and stores insights

## 🧑‍💻 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.