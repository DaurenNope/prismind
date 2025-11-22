#!/bin/bash
# Quick test script for elizaOS Laura (Social Media Manager)
# This will set up and test if Laura can actually post to Twitter

set -e

EVAL_DIR="/tmp/the-org-eval"
cd "$EVAL_DIR"

echo "📦 Checking Bun installation..."
if ! command -v bun &> /dev/null; then
    echo "⚠️  Bun not found. Installing..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
fi

echo "📦 Installing dependencies..."
bun install

echo "📝 Creating .env from template..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
        echo "⚠️  Please edit .env and add your Twitter credentials:"
        echo "   - TWITTER_USERNAME"
        echo "   - TWITTER_EMAIL"
        echo "   - TWITTER_PASSWORD"
        echo "   - TWITTER_2FA_SECRET (optional)"
        echo ""
        echo "   Also add Discord bot tokens if you want approval workflow:"
        echo "   - SOCIAL_MEDIA_MANAGER_DISCORD_APPLICATION_ID"
        echo "   - SOCIAL_MEDIA_MANAGER_DISCORD_API_TOKEN"
        echo ""
        read -p "Press Enter after you've configured .env..."
    else
        echo "❌ No .env.example found. Creating minimal .env..."
        cat > .env << EOF
# Twitter credentials
TWITTER_USERNAME=your_username
TWITTER_EMAIL=your_email@example.com
TWITTER_PASSWORD=your_password
TWITTER_2FA_SECRET=

# Discord (optional, for approval workflow)
SOCIAL_MEDIA_MANAGER_DISCORD_APPLICATION_ID=
SOCIAL_MEDIA_MANAGER_DISCORD_API_TOKEN=

# LLM (required)
OPENAI_API_KEY=your_openai_key
# or
ANTHROPIC_API_KEY=your_anthropic_key
EOF
        echo "✅ Created minimal .env - please edit with your credentials"
        read -p "Press Enter after you've configured .env..."
    fi
fi

echo "🔍 Inspecting @elizaos/plugin-twitter..."
if [ -d "node_modules/@elizaos/plugin-twitter" ]; then
    echo "✅ Plugin found in node_modules"
    echo "📂 Checking for source files..."
    find node_modules/@elizaos/plugin-twitter -name "*.ts" -o -name "*.js" | head -10
    echo ""
    echo "📄 Key files:"
    ls -la node_modules/@elizaos/plugin-twitter/ | head -20
else
    echo "⚠️  Plugin not found - will be installed with bun install"
fi

echo ""
echo "🚀 Starting Laura (Social Media Manager)..."
echo "   This will start the agent. You can interact via Discord if configured."
echo "   Or test posting programmatically."
echo ""
echo "   To test posting, you'll need to:"
echo "   1. Have Discord bot running (if using approval workflow)"
echo "   2. Send a message like: 'Please create a post about X for Twitter'"
echo "   3. Approve the generated tweet"
echo ""
echo "   Press Ctrl+C to stop"
echo ""

bun src/index.ts --socialMediaManager
