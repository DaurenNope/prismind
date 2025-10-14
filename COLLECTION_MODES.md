# PrisMind Collection Modes

## Overview

PrisMind has two distinct collection modes:

1. **Bookmark-Based Collection** - Collects content from your personal bookmarks and accounts
2. **Autonomous Discovery** - Collects content from public sources to provide additional intelligence

## Bookmark-Based Collection

This is the primary collection mode that focuses on content you've personally saved or are following.

### Platforms Supported:
- **Reddit**: Collects your saved posts and comments
- **Twitter**: Collects your bookmarked tweets
- **Threads**: Collects your bookmarked posts
- **GitHub**: Collects trending repositories
- **Telegram**: Collects messages from channels you're following

### How It Works:
1. Uses your personal credentials to access your accounts
2. Collects only content you've explicitly saved/bookmarked
3. Stores the content in your personal database
4. Provides a personalized view of your saved content

### Requirements:
- Valid credentials for each platform in your `.env` file
- Proper cookie files for platforms that require them (Twitter, Threads)

### Run Command:
```bash
python run_bookmark_collection.py
```

## Autonomous Discovery

This is a secondary collection mode that provides additional intelligence beyond your personal bookmarks.

### Sources:
- **RSS Feeds**: Collects articles from various news and technology sources
- **Public APIs**: Collects data from public APIs (when implemented)
- **Other Sources**: Collects from various public sources to provide broader context

### How It Works:
1. Collects content from public sources without requiring personal credentials
2. Filters content based on your topics of interest
3. Stores the content in a separate discoveries table
4. Provides broader context and trending information

### Requirements:
- None (uses public sources only)

### Run Command:
```bash
python run_full_collection.py
```

Or to run only autonomous discovery:
```bash
python -c "from src.services.autonomous_discovery import get_discovery_engine; import asyncio; asyncio.run(get_discovery_engine().discover_content())"
```

## Key Differences

| Aspect | Bookmark-Based Collection | Autonomous Discovery |
|--------|---------------------------|----------------------|
| **Content Source** | Your personal bookmarks | Public sources |
| **Credentials Required** | Yes | No |
| **Personalization** | High (your content) | Medium (topic-based) |
| **Storage Location** | Posts table | Discoveries table |
| **Update Frequency** | When you run collection | Scheduled/regular intervals |
| **Purpose** | Organize your saved content | Provide additional intelligence |

## When to Use Each Mode

### Use Bookmark-Based Collection When:
- You want to organize and analyze content you've personally saved
- You want to keep track of your bookmarks across platforms
- You want to generate insights from your personal content collection

### Use Autonomous Discovery When:
- You want to discover new content related to your interests
- You want to stay informed about trends and news
- You want to supplement your personal collection with broader context

## Configuration

Both collection modes can be configured through:
- `.env` file for credentials
- `config/collection.json` for collection settings
- `config/content_sources.json` for specifying sources

## Best Practice

For optimal use of PrisMind:
1. Set up your credentials properly for bookmark-based collection
2. Run bookmark collection regularly to keep your personal collection updated
3. Use autonomous discovery to supplement your personal collection with broader context
4. Configure your topics of interest to improve autonomous discovery relevance