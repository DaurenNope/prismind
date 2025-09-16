#!/usr/bin/env python3
"""
Supabase Webhook Receiver
Receives row insert/update events and forwards digests to Telegram
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

from news_digest_generator import NewsDigestGenerator
from telegram_bot import PrismindTelegramBot

app = Flask(__name__)

TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

news = NewsDigestGenerator()
bot = PrismindTelegramBot()

@app.route('/health', methods=['GET'])
def health() -> Any:
    return jsonify({"ok": True}), 200

@app.route('/supabase/post-changed', methods=['POST'])
def supabase_post_changed() -> Any:
    try:
        payload: Dict[str, Any] = request.get_json(force=True) or {}
        event_type = payload.get('type', 'unknown')
        record = payload.get('record') or payload.get('new') or {}

        # Only react to inserts/updates of posts
        table = payload.get('table', '') or payload.get('table_name', '')
        if table and table != 'posts':
            return jsonify({"ignored": True}), 200

        # Build a short message for Telegram
        title = record.get('title', 'New post')
        category = record.get('category', 'General')
        value_score = record.get('value_score', 0) or 0
        url = record.get('url', '')

        msg = f"🆕 New content ({event_type}):\n\n**{title}**\n🏷️ {category} | ⭐ {value_score}/10\n"
        if url:
            msg += f"🔗 {url}"

        # Send via Telegram if chat id is configured
        if TELEGRAM_CHAT_ID:
            from telegram.ext import Application
            application = Application.builder().token(bot.token).build()
            application.bot.send_message = application.bot.send_message  # type: ignore
            # Fire-and-forget send (simplified for this lightweight endpoint)
            import asyncio
            async def _send():
                try:
                    await application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode='Markdown')
                except Exception:
                    pass
            asyncio.get_event_loop().run_until_complete(_send())

        return jsonify({"ok": True}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', '8080'))
    app.run(host='0.0.0.0', port=port)



