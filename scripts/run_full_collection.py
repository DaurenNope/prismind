#!/usr/bin/env python3
"""
Complete Intelligence Collection Pipeline
Runs all collectors: RSS, Reddit, GitHub, Telegram
"""

import asyncio
import sys
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path('.env'), override=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def run_complete_collection():
    """Run full intelligence collection pipeline"""
    
    print("=" * 70)
    print("🚀 COMPLETE INTELLIGENCE COLLECTION PIPELINE")
    print("=" * 70)
    print()
    
    start_time = datetime.now()
    results = {
        "rss": 0,
        "reddit": 0,
        "github": 0,
        "telegram": 0,
        "errors": []
    }
    
    # ==========================================
    # 1. RSS + Reddit + GitHub (Autonomous Discovery)
    # ==========================================
    print("📡 PHASE 1: Autonomous Discovery (RSS + Reddit + GitHub)")
    print("-" * 70)
    try:
        from src.services.autonomous_discovery import AutonomousDiscovery
        from src.core.extraction.edgy_sources import get_all_edgy_sources
        
        discovery = AutonomousDiscovery()
        disc_results = await discovery.discover_content()
        
        if disc_results and not disc_results.get('error'):
            results['rss'] = disc_results.get('sources', {}).get('rss', 0)
            results['reddit'] = disc_results.get('sources', {}).get('reddit', 0)
            results['github'] = disc_results.get('sources', {}).get('github', 0)
            
            print(f"   ✅ RSS: {results['rss']} items")
            print(f"   ✅ Reddit: {results['reddit']} items")
            print(f"   ✅ GitHub: {results['github']} items")
            print(f"   💾 Saved: {disc_results.get('saved', 0)} discoveries")
        else:
            error = disc_results.get('error', 'Unknown error')
            print(f"   ❌ Error: {error}")
            results['errors'].append(f"Discovery: {error}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        results['errors'].append(f"Discovery: {str(e)}")
    
    print()
    
    # ==========================================
    # 2. Russian Telegram Channels (Optional)
    # ==========================================
    print("🇷🇺 PHASE 2: Russian Telegram Intelligence (Optional)")
    print("-" * 70)
    
    # Check if we should run Telegram (only if >1 day since last run)
    try:
        from supabase import create_client
        import os
        
        supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_ROLE_KEY'))
        
        # Check last Telegram message date
        last_tg = supabase.table('telegram_messages')\
            .select('created_at')\
            .order('created_at', desc=True)\
            .limit(1)\
            .execute()
        
        should_run_telegram = True
        if last_tg.data:
            from datetime import timedelta
            last_date = datetime.fromisoformat(last_tg.data[0]['created_at'].replace('Z', '+00:00'))
            if datetime.now(last_date.tzinfo) - last_date < timedelta(days=1):
                should_run_telegram = False
                print(f"   ⏭️  Skipping (last run: {last_date.strftime('%Y-%m-%d %H:%M')})")
                print(f"   💡 Telegram runs once per day to avoid spam")
        
        if should_run_telegram:
            print(f"   🚀 Running Telegram scraper...")
            from scrape_russian_telegram import RussianTelegramScraper
            
            scraper = RussianTelegramScraper()
            tg_results = await scraper.scrape_and_analyze(
                channels=['whitelist1', 'cryptoforto', 'idoresearch', 
                         'CoinMetrika', 'don_invest', 'CryptorankFundraisingSniper'],
                limit_per_channel=10,  # 10 new messages per channel
                days_back=3
            )
            
            results['telegram'] = tg_results.get('saved', 0)
            print(f"   ✅ Collected: {tg_results.get('total', 0)}")
            print(f"   💾 Saved: {results['telegram']} new messages")
            print(f"   🌐 Translated: {tg_results.get('translated', 0)}")
            
    except Exception as e:
        print(f"   ⚠️  Telegram skipped: {e}")
        results['errors'].append(f"Telegram: {str(e)}")
    
    print()
    
    # ==========================================
    # 3. Social Bookmarks (Optional)
    # ==========================================
    print("📱 PHASE 3: Social Bookmarks (Optional - Skipped)")
    print("-" * 70)
    print("   ⏭️  Twitter/Reddit/Threads bookmarks - manual only")
    print("   💡 These are your personal saves, not auto-scraped")
    print()
    
    # ==========================================
    # SUMMARY
    # ==========================================
    duration = (datetime.now() - start_time).total_seconds()
    
    print("=" * 70)
    print("✅ COLLECTION COMPLETE!")
    print("=" * 70)
    print()
    print(f"⏱️  Duration: {duration:.1f}s")
    print()
    print("📊 Results:")
    print(f"   RSS feeds: {results['rss']} items")
    print(f"   Reddit: {results['reddit']} items")
    print(f"   GitHub: {results['github']} items")
    print(f"   Telegram: {results['telegram']} items")
    print(f"   Total: {sum([results['rss'], results['reddit'], results['github'], results['telegram']])} items")
    print()
    
    if results['errors']:
        print(f"⚠️  Errors: {len(results['errors'])}")
        for err in results['errors']:
            print(f"   • {err}")
        print()
    
    print("🎯 View results in Web UI:")
    print("   • Discoveries tab → RSS/Reddit/GitHub")
    print("   • 🇷🇺 Telegram tab → Russian crypto intel")
    print()
    
    return results


if __name__ == "__main__":
    asyncio.run(run_complete_collection())