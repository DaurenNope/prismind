#!/usr/bin/env python3
"""
Test script to verify the complete notification functionality
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

def simulate_collection_results():
    """Simulate collection results"""
    # Write a sample collection results file
    with open('collection_results.txt', 'w') as f:
        f.write("Reddit: 5 posts\n")
        f.write("Twitter: 8 posts\n")
        f.write("Total: 13 posts\n")
    print("✅ Created collection results file")

def send_notification():
    """Send notification using the same code as in the workflow"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return False
    
    # Read collection results if available
    try:
        with open('collection_results.txt', 'r') as f:
            results = f.read()
    except FileNotFoundError:
        results = 'Collection results unavailable'
    
    message = f'''🤖 Automated Collection Complete!

{results}

Your new bookmarks have been collected and processed.'''
    
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    data = {'chat_id': chat_id, 'text': message}
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print('✅ Telegram notification sent!')
            return True
        else:
            print(f'❌ Failed to send notification: {response.status_code}')
            print(response.text)
            return False
    except Exception as e:
        print(f'❌ Error sending notification: {e}')
        return False

def main():
    """Test the complete notification flow"""
    print("Testing complete notification flow...")
    
    load_env_variables()
    simulate_collection_results()
    success = send_notification()
    
    # Clean up
    try:
        os.remove('collection_results.txt')
    except:
        pass
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())