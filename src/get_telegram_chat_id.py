#!/usr/bin/env python3
"""
Script to get Telegram chat ID
"""

import os
import requests
from dotenv import load_dotenv

def load_env_variables():
    """Load environment variables from .env file"""
    load_dotenv()

def get_chat_id():
    """Get chat ID from Telegram bot"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment")
        return
    
    print(f"Bot Username: BookmarkerQronoya_bot")
    print("Please follow these steps:")
    print("1. Open Telegram")
    print("2. Search for @BookmarkerQronoya_bot")
    print("3. Send any message to the bot (like 'Hello')")
    print("4. Press Enter after sending the message...")
    
    input()
    
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['ok'] and data['result']:
                # Print all updates for debugging
                print("\nAll updates received:")
                for i, update in enumerate(data['result']):
                    print(f"Update {i}: {update}")
                
                # Get the most recent message
                latest_update = data['result'][-1]
                if 'message' in latest_update:
                    chat_id = latest_update['message']['chat']['id']
                    print(f"\n✅ Your chat ID is: {chat_id}")
                    print("Please add this to your .env file:")
                    print(f"TELEGRAM_CHAT_ID={chat_id}")
                    print("\nThen update the GitHub secrets with:")
                    print(f"gh secret set TELEGRAM_CHAT_ID --body \"{chat_id}\"")
                else:
                    print("No message found in the latest update")
            else:
                print("No updates found. Please make sure you sent a message to your bot.")
        else:
            print(f"Failed to get updates: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error getting chat ID: {e}")

if __name__ == "__main__":
    load_env_variables()
    get_chat_id()