# BEYONDLINES Telegram Bot Usage Guide

## Quick Start

### 1. Setup

Ensure your `.env` file has the following configured:

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token_here

# Optional - for access control (comma-separated user IDs)
TELEGRAM_ALLOWED_USER_IDS=123456789,987654321

# Optional - command cooldown in seconds (default: 15)
TELEGRAM_COMMAND_COOLDOWN=15
```

### 2. Get Your Bot Token

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow the instructions
3. Copy the bot token to your `.env` file

### 3. Find Your User ID (Optional, for access control)

1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will reply with your user ID
3. Add it to `TELEGRAM_ALLOWED_USER_IDS` in `.env`

### 4. Start the Bot

```bash
# Using the startup script
./run_telegram_bot.sh

# Or directly with Python
python -m src.services.telegram_bot

# Or with virtual environment
source .venv311/bin/activate && python -m src.services.telegram_bot
```

## Available Commands

### Basic Commands

- `/start` - Welcome message and command list
- `/help` - Detailed usage instructions
- `/env` - Check configuration (shows which env vars are set, not their values)

### Collection Commands

- `/collect` - Trigger multi-platform collection (Twitter, Reddit, Threads)
  - This will collect bookmarks from all configured platforms
  - Takes a few minutes to complete
  - Returns counts for each platform

### Analysis Commands

- `/analyze [count] [platform]` - Analyze recent posts
  - Examples:
    - `/analyze` - Analyze 10 most recent unanalyzed posts
    - `/analyze 20` - Analyze 20 most recent posts
    - `/analyze 15 twitter` - Analyze 15 recent Twitter posts
  - Supported platforms: twitter, reddit, threads

### Browse Commands

- `/latest [count] [platform]` - Browse recent items
  - Examples:
    - `/latest` - Show 10 most recent items
    - `/latest 20` - Show 20 most recent items
    - `/latest 15 reddit` - Show 15 recent Reddit posts
  - Supported platforms: twitter, reddit, threads

- `/insight <post_id>` - Get AI insight card for a specific post
  - Example: `/insight abc123xyz`
  - Shows: summary, key concepts, value score, tags, sentiment, action items

### Status Commands

- `/status` - Show scraping statistics
  - Total posts collected
  - Per-platform breakdown

## Features

### Access Control

- **Allowlist**: Set `TELEGRAM_ALLOWED_USER_IDS` to restrict bot access
  - Leave empty to allow anyone
  - Set to comma-separated user IDs to restrict access
  - Example: `TELEGRAM_ALLOWED_USER_IDS=123456789,987654321`

### Rate Limiting

- Commands are rate-limited per user
- Default: 15 seconds cooldown between commands
- Configurable via `TELEGRAM_COMMAND_COOLDOWN` in `.env`
- Prevents bot abuse and API overload

### Error Handling

- All commands include error handling
- Errors are logged and reported back to the user
- Bot continues running even if individual commands fail

## Platform Configuration

### Twitter

Required in `.env`:
```bash
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
```

### Reddit

Required in `.env`:
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
REDDIT_USER_AGENT=BEYONDLINES v1.0
```

### Threads

Required in `.env`:
```bash
THREADS_USERNAME=your_username
THREADS_PASSWORD=your_password
```

## AI Analysis Configuration

For full AI analysis features, configure at least one AI service:

```bash
# Mistral AI
MISTRAL_API_KEY=your_key_here

# Google Gemini
GEMINI_API_KEY=your_key_here

# Local Ollama (optional)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

## Troubleshooting

### Bot doesn't respond
- Check that `TELEGRAM_BOT_TOKEN` is correctly set in `.env`
- Ensure the bot is running (check terminal output)
- Try `/start` command to wake up the bot

### "You are not authorized" message
- Your user ID is not in `TELEGRAM_ALLOWED_USER_IDS`
- Either add your user ID or remove the allowlist (leave empty)

### "Slow down" message
- You're hitting the rate limit
- Wait for the cooldown period (default: 15 seconds)
- Adjust `TELEGRAM_COMMAND_COOLDOWN` if needed

### Collection fails
- Check platform credentials in `.env`
- Verify internet connection
- Check logs for specific error messages
- Use `/env` command to verify configuration

### Analysis fails
- Check that AI service API keys are configured
- Use `/env` to verify AI keys are present
- Check logs for specific error messages

## Development

### Running in Development

```bash
# With debug logging
LOG_LEVEL=DEBUG python -m src.services.telegram_bot

# With custom port (if using webhooks)
PORT=8443 python -m src.services.telegram_bot
```

### Testing Commands

1. Start the bot locally
2. Message your bot on Telegram
3. Try each command to verify functionality
4. Check terminal logs for errors

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/beyondlines-bot.service`:

```ini
[Unit]
Description=BEYONDLINES Telegram Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/beyondlines
ExecStart=/path/to/beyondlines/.venv311/bin/python -m src.services.telegram_bot
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable beyondlines-bot
sudo systemctl start beyondlines-bot
sudo systemctl status beyondlines-bot
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps

CMD ["python", "-m", "src.services.telegram_bot"]
```

Build and run:
```bash
docker build -t beyondlines-bot .
docker run -d --name beyondlines-bot --env-file .env beyondlines-bot
```

### Using screen (Simple)

```bash
screen -S beyondlines-bot
./run_telegram_bot.sh
# Press Ctrl+A then D to detach

# To reattach:
screen -r beyondlines-bot
```

## Security Best Practices

1. **Never commit `.env` file** to version control
2. **Use allowlist** (`TELEGRAM_ALLOWED_USER_IDS`) in production
3. **Keep bot token secret** - regenerate if exposed
4. **Use rate limiting** to prevent abuse
5. **Monitor logs** for suspicious activity
6. **Regular updates** - keep dependencies up to date

## Support

For issues or questions:
- Check logs in terminal
- Use `/env` command to diagnose configuration
- Review this documentation
- Check [TELEGRAM_PLAN.md](./TELEGRAM_PLAN.md) for development roadmap
