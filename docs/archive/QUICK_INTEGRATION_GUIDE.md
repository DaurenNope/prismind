# Quick Integration Guide - 15 Minutes

## For Streamlit App

### Step 1: Update `src/web/app.py`

Add this import at the top:
```python
from src.web.components.collection_tab import render_collection_tab
```

Find where tabs are rendered and add:
```python
elif selected_tab == "Collection":
    render_collection_tab()
```

Add "Collection" to your tab list:
```python
tabs = ["Dashboard", "Collection", "Browse", "Settings", ...]
```

### Step 2: Test
```bash
streamlit run src/web/app.py
```

Click on "Collection" tab → Should see collection interface!

---

## For Telegram Bot

### Step 1: Update `src/services/telegram_bot.py`

Add imports at the top:
```python
from src.services.telegram_collection_commands import (
    collect_command,
    collection_status_command,
    collection_callback_handler
)
```

Find where command handlers are registered and add:
```python
# Add these with other CommandHandlers
application.add_handler(CommandHandler("collect", collect_command))
application.add_handler(CommandHandler("collection_status", collection_status_command))

# Add this with other CallbackQueryHandlers
application.add_handler(CallbackQueryHandler(
    collection_callback_handler,
    pattern="^collect_|^collection_"
))
```

Update help text:
```python
# In _cmd_help or wherever help is defined
help_text += "\n📥 <b>Collection Commands:</b>\n"
help_text += "/collect - Collect posts from platforms\n"
help_text += "/collection_status - Show current status\n"
```

### Step 2: Test
```bash
python3 -m src.services.telegram_bot
# Or
./run_telegram_bot.sh
```

Send `/collect` to the bot → Should see collection menu!

---

## Quick Test

Run the integration test:
```bash
python3 test_integration.py
```

Should see:
```
======================================================================
UNIFIED COLLECTION SERVICE TEST
======================================================================

1. Initializing service...
   ✅ Service initialized
   ✅ Supported platforms: ['twitter', 'reddit', 'threads']

2. Testing progress tracking...

3. Testing unsupported platform...
   ✅ Handled unsupported platform correctly: True

4. Testing Threads collection...
   🚀 threads: Starting threads collection...
   🔐 threads: Authenticating with threads...
   📥 threads: Collecting posts from threads...
   ...
   ✅ Collection succeeded!
```

---

## That's It!

You now have:
- ✅ Unified collection service
- ✅ Streamlit UI with collection tab
- ✅ Telegram bot with collection commands
- ✅ Full test coverage
- ✅ Progress tracking
- ✅ Error handling
- ✅ Automatic retries

**All platforms (Twitter, Reddit, Threads) work through the same reliable interface!**

---

## Common Issues

### "Module not found"
```bash
# Make sure you're in project root
cd /Users/mac/Documents/Development/prismind
python3 test_integration.py
```

### "Collection failed"
Check authentication:
- Threads: `config/threads_cookies.json`
- Twitter: `config/twitter_cookies_*.json`
- Reddit: `.env` credentials

### "Already collecting"
Only one collection can run at a time. Wait for current to finish or restart service.

---

## Next Steps

1. ✅ Integrate into Streamlit (5 min)
2. ✅ Integrate into Telegram (5 min)
3. ✅ Test both UIs (5 min)
4. 🚀 Start using!

**Total time: 15 minutes**
