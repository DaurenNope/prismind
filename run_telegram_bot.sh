#!/bin/bash
# PrisMind Telegram Bot - Simple One-Command Startup

set -e  # Exit on error

echo "🤖 Starting PrisMind Telegram Bot..."
echo ""

# 1. Check .env exists and is configured
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "   Copy .env.example to .env and configure TELEGRAM_BOT_TOKEN"
    exit 1
fi

if ! grep -q "TELEGRAM_BOT_TOKEN=" .env || grep -q "TELEGRAM_BOT_TOKEN=your_" .env; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN not configured in .env"
    exit 1
fi

# 2. Kill any existing bot instances (prevents 409 conflicts)
echo "🧹 Cleaning up old bot instances..."
pkill -9 -f "python.*telegram_bot" 2>/dev/null || true
rm -f /tmp/prismind_bot.pid 2>/dev/null || true
sleep 2  # Wait for Telegram API to clear

# 3. Activate virtual environment
if [ -d ".venv311" ]; then
    source .venv311/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  No venv found, using system Python"
fi

# 4. Start the bot
echo "✅ Bot starting..."
echo ""
echo "Commands: /start /help /status /collect /analyze /latest /insight /publish /transform"
echo "Press Ctrl+C to stop"
echo ""

python -m src.services.telegram_bot
