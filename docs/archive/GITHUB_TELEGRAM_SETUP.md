# GitHub & Telegram Setup Guide

## ✅ What Was Fixed

### 1. Telegram Tab - Now Useful!

**Before**: Useless sidebar filters
**After**: Full channel management UI

**New Features**:
- ➕ Add channels from UI (no editing files!)
- 🗑️ Remove channels with one click
- 📝 Bulk add multiple channels
- 📋 See all configured channels
- 📊 Channel count stats

**Access**: http://localhost:8501 → "🇷🇺 Telegram" tab

### 2. GitHub Trending - Auto Collection Script

**Created**: `collect_github_daily.py`

**What it collects**:
- Trending repos by language (Python, JS, TS, Rust, Go)
- Trending repos by topic (ML, AI, LLM, blockchain, web3, DeFi)
- Daily updates
- Filters out duplicates

**Run manually**:
```bash
python3 collect_github_daily.py
```

**Or automate** (add to cron):
```bash
# Run daily at 9 AM
0 9 * * * cd /path/to/beyondlines && python3 collect_github_daily.py
```

### 3. Sidebar - Will Be Cleaned

The useless sidebar filters will be removed/simplified in next update.

## How to Use Telegram Channels Manager

### Step 1: Configure API Credentials

1. Go to https://my.telegram.org/apps
2. Create an app
3. Copy API ID and API Hash
4. Add to `.env`:
   ```
   TELEGRAM_API_ID=12345678
   TELEGRAM_API_HASH=your_hash_here
   TELEGRAM_PHONE=+1234567890
   ```
5. Restart Svelte

### Step 2: Add Channels in UI

1. Open http://localhost:8501
2. Go to "🇷🇺 Telegram" tab
3. See "➕ Add New Channel" section
4. Enter channel username (without @)
5. Click "Add Channel"

**Examples**:
- `cryptoforto`
- `idoresearch`
- `don_invest`

### Step 3: Bulk Add (Optional)

1. Click "📝 Bulk Add Channels"
2. Paste channel list (one per line):
   ```
   cryptoforto
   idoresearch
   CoinMetrika
   don_invest
   ```
3. Click "Add All Channels"

### Current Channels (Pre-configured)

Your `config/telegram_channels.txt` already has:
- whitelist1
- cryptoforto
- idoresearch
- CoinMetrika
- don_invest
- CryptorankFundraisingSniper

You can see and manage these in the UI now!

## How to Use GitHub Trending

### Manual Collection

```bash
# Collect trending repos now
python3 collect_github_daily.py
```

**Output**:
```
================================================================================
GITHUB TRENDING DAILY COLLECTION
================================================================================

1. Collecting trending repositories...
   Languages: python, javascript, typescript, rust, go
   Topics: machine-learning, artificial-intelligence, llm, blockchain, web3, defi

   📊 Collecting trending python repos...
      Found 10 repos
   📊 Collecting trending javascript repos...
      Found 8 repos
   ...

2. Processing 50 repositories...
   New repos: 45

   ✅ Saved: openai/gpt-4
   ✅ Saved: microsoft/autogen
   ...

================================================================================
COLLECTION COMPLETE
================================================================================

Summary:
  Total found: 50
  New repos: 45
  Saved: 45

GitHub posts in database: 46
```

### Automated Daily Collection

**Option 1: Cron Job** (macOS/Linux)

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 9 AM)
0 9 * * * cd /Users/mac/Documents/Development/beyondlines && /Users/mac/Documents/Development/beyondlines/.venv311/bin/python collect_github_daily.py >> /tmp/github_collection.log 2>&1
```

**Option 2: launchd** (macOS, more reliable)

Create `~/Library/LaunchAgents/com.beyondlines.github.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.beyondlines.github</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/mac/Documents/Development/beyondlines/.venv311/bin/python</string>
        <string>/Users/mac/Documents/Development/beyondlines/collect_github_daily.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/github_collection.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/github_collection.error.log</string>
</dict>
</plist>
```

Then load it:
```bash
launchctl load ~/Library/LaunchAgents/com.beyondlines.github.plist
```

**Option 3: Add to Svelte Automation Tab**

The Automation tab can be configured to run GitHub collection on schedule.

### What Gets Collected

**Languages**:
- Python (AI/ML repos)
- JavaScript/TypeScript (web3/frontend)
- Rust (blockchain/performance)
- Go (backend/infrastructure)

**Topics**:
- machine-learning
- artificial-intelligence
- llm (Large Language Models)
- blockchain
- web3
- defi

**Criteria**:
- Trending today
- High stars/activity
- Relevant to tech/crypto/AI

### Customize Collection

Edit `collect_github_daily.py`:

```python
# Add more languages
languages = [
    'python',
    'javascript',
    'solidity',  # For smart contracts
    'move',      # For Aptos/Sui
]

# Add more topics
topics = [
    'cryptocurrency',
    'dao',
    'nft',
    'zero-knowledge',
]
```

## Quick Start Checklist

### Telegram Setup
- [ ] Get API credentials from https://my.telegram.org/apps
- [ ] Add to `.env` file
- [ ] Restart Svelte
- [ ] Go to Telegram tab
- [ ] Add/manage channels from UI
- [ ] Run first collection (will ask for phone verification)

### GitHub Setup
- [ ] Run manual collection: `python3 collect_github_daily.py`
- [ ] Verify repos saved to database
- [ ] Set up automated daily collection (cron or launchd)
- [ ] Check logs to ensure it runs

## Verification

### Check Telegram Channels

```python
from pathlib import Path

channels = Path('config/telegram_channels.txt').read_text()
print(channels)
```

### Check GitHub Repos

```python
from src.services.new_database_manager import NewDatabaseManager

db = NewDatabaseManager()
github_posts = db.get_posts_by_platform('github')
print(f"GitHub repos: {len(github_posts)}")

for post in github_posts[:5]:
    print(f"  - {post['author']}: {post['title']}")
```

## Summary

✅ **Telegram**: Channel manager in UI (add/remove channels easily)
✅ **GitHub**: Daily trending collector script ready
✅ **Automation**: Can be added to cron/launchd for daily runs
🔧 **Sidebar**: Will be cleaned up in next update

**All changes are live at http://localhost:8501!** 🎉
