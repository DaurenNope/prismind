#!/usr/bin/env python3
"""
Test script to verify Telegram notifications
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def load_env_variables():
    """Load environment variables from .env file"""
    load_dotenv()
    print("Loaded environment variables from .env file")

def test_telegram_notification():
    """Test Telegram notification functionality"""
    print("Testing Telegram notification...")
    
    # Get Telegram credentials from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    assert bot_token is not None, "TELEGRAM_BOT_TOKEN not set in environment"
    assert chat_id is not None, "TELEGRAM_CHAT_ID not set in environment"
    
    print(f"Bot token length: {len(bot_token)}")
    print(f"Chat ID: {chat_id}")
    
    # Send test message
    message = "🧪 PrisMind Test Notification\n\nThis is a test message to verify Telegram notifications are working correctly."
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = {
        'chat_id': chat_id,
        'text': message
    }
    
    response = requests.post(url, data=data)
    assert response.status_code == 200, f"Failed to send Telegram notification: {response.status_code}\nResponse: {response.text}"
    print("✅ Telegram notification sent successfully!")

if __name__ == "__main__":
    load_env_variables()
    try:
        test_telegram_notification()
        sys.exit(0)
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)