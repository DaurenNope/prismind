#!/usr/bin/env python3
"""
Manual Collection Trigger Script
Run this after adding Twitter bookmarks to test the collection and notification system
"""

import os
import sys
from dotenv import load_dotenv

def main():
    print("🤖 Manual Collection Trigger")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Set the missing chat ID for local testing
    os.environ['TELEGRAM_CHAT_ID'] = '319089661'
    
    print("📋 Checking environment variables...")
    required_vars = [
        'REDDIT_CLIENT_ID', 'REDDIT_CLIENT_SECRET', 'REDDIT_ACCESS_TOKEN', 'REDDIT_REFRESH_TOKEN',
        'TWITTER_USERNAME', 'TWITTER_PASSWORD',
        'SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY',
        'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'
    ]
    
    missing = []
    for var in required_vars:
        if os.getenv(var):
            print(f'✅ {var}: Set')
        else:
            print(f'❌ {var}: Missing')
            missing.append(var)
    
    if missing:
        print(f'\n❌ Missing {len(missing)} required variables')
        return 1
    
    print('\n✅ All required variables are set!')
    
    # Import and run collection
    try:
        print('\n🚀 Starting manual collection...')
        from services.collector_runner import collect_reddit_bookmarks, collect_twitter_bookmarks_sync
        from scripts.database_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # Collect from both platforms
        print('\n📱 Collecting Twitter bookmarks...')
        twitter_result = collect_twitter_bookmarks_sync(db_manager, set(), set())
        print(f'✅ Twitter collection result: {twitter_result}')
        
        print('\n🔴 Collecting Reddit bookmarks...')
        reddit_result = collect_reddit_bookmarks(db_manager, set(), set())
        print(f'✅ Reddit collection result: {reddit_result}')
        
        # Send notification
        print('\n📱 Sending Telegram notification...')
        import requests
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        message = f"""🤖 Manual Collection Complete!

📊 Results:
• Twitter: {twitter_result} posts collected
• Reddit: {reddit_result} posts collected

✅ Collection and notification system is working!"""
        
        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        data = {
            'chat_id': chat_id,
            'text': message
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print('✅ Telegram notification sent successfully!')
        else:
            print(f'❌ Failed to send notification: {response.status_code}')
            print(response.text)
        
        print('\n🎉 Manual collection test complete!')
        return 0
        
    except Exception as e:
        print(f'\n❌ Collection failed: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
