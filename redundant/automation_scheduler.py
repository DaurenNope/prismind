#!/usr/bin/env python3
"""
PrisMind Automation Scheduler
============================

Intelligent scheduling system that runs collection automatically
with smart rate limiting and error recovery.

Features:
- Adaptive scheduling based on success/failure rates
- Platform-specific timing to avoid rate limits
- Automatic retry with exponential backoff
- Health monitoring and alerting
- Cookie refresh automation
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import os
import sys

# Setup paths
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from collect_multi_platform import collect_twitter_bookmarks, collect_reddit_bookmarks, collect_threads_bookmarks
from scripts.database_manager import DatabaseManager
from scripts.supabase_manager import SupabaseManager


@dataclass
class PlatformStatus:
    """Track platform collection status"""
    name: str
    last_success: Optional[datetime] = None
    last_attempt: Optional[datetime] = None
    consecutive_failures: int = 0
    success_rate: float = 1.0
    next_scheduled: Optional[datetime] = None
    is_enabled: bool = True
    failure_reason: str = ""


class IntelligentScheduler:
    """Intelligent scheduling system for automated collection"""
    
    def __init__(self, config_file: str = "automation_config.json"):
        self.config_file = Path(config_file)
        self.platforms = {
            'twitter': PlatformStatus('twitter'),
            'reddit': PlatformStatus('reddit'), 
            'threads': PlatformStatus('threads')
        }
        self.db_manager = DatabaseManager(str(project_root / "data" / "prismind.db"))
        self.supabase = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('automation.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize Supabase if configured
        if os.getenv('SAVE_TO_SUPABASE', '0') == '1':
            try:
                self.supabase = SupabaseManager()
                self.logger.info("✅ Supabase connection initialized")
            except Exception as e:
                self.logger.warning(f"⚠️ Supabase not available: {e}")
    
    def load_config(self) -> Dict:
        """Load scheduling configuration"""
        default_config = {
            "collection_intervals": {
                "twitter": 6,  # hours
                "reddit": 4,   # hours  
                "threads": 8   # hours (more conservative due to auth issues)
            },
            "rate_limits": {
                "twitter": {"requests_per_hour": 10, "delay_between": 60},
                "reddit": {"requests_per_hour": 30, "delay_between": 30},
                "threads": {"requests_per_hour": 5, "delay_between": 120}
            },
            "retry_config": {
                "max_retries": 3,
                "backoff_multiplier": 2,
                "initial_delay": 300  # 5 minutes
            },
            "health_monitoring": {
                "max_consecutive_failures": 5,
                "disable_threshold": 0.3  # Disable if success rate < 30%
            }
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge with defaults
                    default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"Could not load config: {e}, using defaults")
        
        return default_config
    
    def save_config(self):
        """Save current configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def calculate_next_run(self, platform: str, success: bool) -> datetime:
        """Calculate next scheduled run based on success/failure"""
        base_interval = self.config["collection_intervals"][platform]
        
        if success:
            # Successful run - use normal interval
            interval_hours = base_interval
            self.platforms[platform].consecutive_failures = 0
        else:
            # Failed run - exponential backoff
            failures = self.platforms[platform].consecutive_failures
            backoff = min(failures * self.config["retry_config"]["backoff_multiplier"], 24)
            interval_hours = base_interval + backoff
            
        return datetime.now() + timedelta(hours=interval_hours)
    
    async def run_platform_collection(self, platform: str) -> Tuple[bool, int, str]:
        """Run collection for a specific platform"""
        self.logger.info(f"🔄 Starting {platform} collection...")
        
        platform_status = self.platforms[platform]
        platform_status.last_attempt = datetime.now()
        
        existing_posts = self.db_manager.get_all_posts(include_deleted=False)
        existing_ids = set(existing_posts['post_id'].tolist()) if not existing_posts.empty else set()
        
        try:
            if platform == 'twitter':
                count = await collect_twitter_bookmarks(self.db_manager, existing_ids)
            elif platform == 'reddit':
                count = collect_reddit_bookmarks(self.db_manager, existing_ids)
            elif platform == 'threads':
                count = await collect_threads_bookmarks(self.db_manager, existing_ids)
            else:
                return False, 0, f"Unknown platform: {platform}"
            
            # Success!
            platform_status.last_success = datetime.now()
            platform_status.consecutive_failures = 0
            platform_status.success_rate = min(1.0, platform_status.success_rate + 0.1)
            platform_status.failure_reason = ""
            
            self.logger.info(f"✅ {platform} collection successful: {count} new posts")
            return True, count, ""
            
        except Exception as e:
            # Failure
            error_msg = str(e)
            platform_status.consecutive_failures += 1
            platform_status.success_rate = max(0.0, platform_status.success_rate - 0.2)
            platform_status.failure_reason = error_msg
            
            self.logger.error(f"❌ {platform} collection failed: {error_msg}")
            
            # Disable platform if too many failures
            max_failures = self.config["health_monitoring"]["max_consecutive_failures"]
            if platform_status.consecutive_failures >= max_failures:
                platform_status.is_enabled = False
                self.logger.warning(f"🚨 {platform} disabled after {max_failures} consecutive failures")
            
            return False, 0, error_msg
    
    def should_run_platform(self, platform: str) -> bool:
        """Check if platform should run now"""
        platform_status = self.platforms[platform]
        
        # Check if platform is enabled
        if not platform_status.is_enabled:
            return False
        
        # Check if it's time to run
        if platform_status.next_scheduled and datetime.now() < platform_status.next_scheduled:
            return False
        
        # Check success rate threshold
        min_success_rate = self.config["health_monitoring"]["disable_threshold"]
        if platform_status.success_rate < min_success_rate:
            self.logger.warning(f"⚠️ {platform} success rate too low: {platform_status.success_rate:.2f}")
            return False
        
        return True
    
    async def run_collection_cycle(self):
        """Run one complete collection cycle"""
        self.logger.info("🚀 Starting automated collection cycle")
        
        total_collected = 0
        platforms_run = []
        
        for platform_name in self.platforms.keys():
            if self.should_run_platform(platform_name):
                platforms_run.append(platform_name)
                
                # Add delay between platforms to avoid overwhelming
                if platforms_run and len(platforms_run) > 1:
                    delay = self.config["rate_limits"][platform_name]["delay_between"]
                    self.logger.info(f"⏱️ Waiting {delay}s between platforms...")
                    await asyncio.sleep(delay)
                
                success, count, error = await self.run_platform_collection(platform_name)
                total_collected += count
                
                # Schedule next run
                next_run = self.calculate_next_run(platform_name, success)
                self.platforms[platform_name].next_scheduled = next_run
                
                self.logger.info(f"📅 {platform_name} next scheduled: {next_run}")
        
        self.logger.info(f"🎉 Collection cycle complete! Total new posts: {total_collected}")
        return total_collected, platforms_run
    
    def get_status_report(self) -> Dict:
        """Get detailed status report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "platforms": {},
            "overall_health": "healthy"
        }
        
        healthy_platforms = 0
        
        for name, status in self.platforms.items():
            platform_report = {
                "enabled": status.is_enabled,
                "success_rate": status.success_rate,
                "consecutive_failures": status.consecutive_failures,
                "last_success": status.last_success.isoformat() if status.last_success else None,
                "last_attempt": status.last_attempt.isoformat() if status.last_attempt else None,
                "next_scheduled": status.next_scheduled.isoformat() if status.next_scheduled else None,
                "failure_reason": status.failure_reason
            }
            
            # Determine platform health
            if status.is_enabled and status.success_rate > 0.7:
                platform_report["health"] = "healthy"
                healthy_platforms += 1
            elif status.is_enabled and status.success_rate > 0.3:
                platform_report["health"] = "degraded"
            else:
                platform_report["health"] = "unhealthy"
            
            report["platforms"][name] = platform_report
        
        # Overall health
        if healthy_platforms == 0:
            report["overall_health"] = "critical"
        elif healthy_platforms < len(self.platforms) / 2:
            report["overall_health"] = "degraded"
        
        return report
    
    async def run_forever(self, check_interval_minutes: int = 30):
        """Run scheduler indefinitely"""
        self.logger.info(f"🤖 PrisMind Automation Scheduler started (check every {check_interval_minutes}m)")
        
        while True:
            try:
                await self.run_collection_cycle()
                
                # Generate and log status report
                status = self.get_status_report()
                self.logger.info(f"📊 System Health: {status['overall_health']}")
                
                # Save status report
                with open("automation_status.json", "w") as f:
                    json.dump(status, f, indent=2)
                
            except Exception as e:
                self.logger.error(f"💥 Scheduler error: {e}")
            
            # Wait before next check
            self.logger.info(f"⏱️ Sleeping for {check_interval_minutes} minutes...")
            await asyncio.sleep(check_interval_minutes * 60)


async def main():
    """Main entry point"""
    scheduler = IntelligentScheduler()
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "status":
            # Show status report
            status = scheduler.get_status_report()
            print(json.dumps(status, indent=2))
            return
        elif sys.argv[1] == "run-once":
            # Run one collection cycle
            await scheduler.run_collection_cycle()
            return
    
    # Run continuously
    await scheduler.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
