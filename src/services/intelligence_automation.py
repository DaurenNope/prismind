#!/usr/bin/env python3
"""
Intelligence Automation System for PrisMind
Autonomous scheduling, discovery, and digest delivery
"""

import logging
from datetime import datetime, time
from typing import Optional, Dict, Any
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from src.core.discovery.profile_manager import ProfileManager
from src.core.discovery.comprehensive_discovery import ComprehensiveDiscovery
from src.services.new_database_manager import get_database_manager
from src.services.digest_generator import DigestGenerator

logger = logging.getLogger(__name__)


class IntelligenceAutomation:
    """Autonomous intelligence system that runs scheduled discoveries and digests"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.profile_manager = ProfileManager()
        self.db = get_database_manager()
        self.discovery_engine = ComprehensiveDiscovery()
        self.digest_generator = DigestGenerator()
        self.telegram_chat_id = None  # Will be set when sending
        
        # Track automation metrics
        self.metrics = {
            "discoveries_run": 0,
            "discoveries_succeeded": 0,
            "discoveries_failed": 0,
            "last_discovery": None,
            "last_digest": None,
            "errors": []
        }
        
        # Setup event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
        )
    
    def start(self):
        """Start the autonomous intelligence system"""
        logger.info("🚀 Starting Intelligence Automation System...")
        
        # Schedule discovery jobs (every 4 hours with profile rotation)
        self._schedule_discoveries()
        
        # Schedule daily digests
        self._schedule_digests()
        
        # Start scheduler
        self.scheduler.start()
        logger.info("✅ Automation system started")
        
        # Print schedule
        self.print_schedule()
    
    def stop(self):
        """Stop the automation system"""
        logger.info("🛑 Stopping Intelligence Automation System...")
        self.scheduler.shutdown(wait=True)
        logger.info("✅ Automation system stopped")
    
    def _schedule_discoveries(self):
        """Schedule profile-based discoveries throughout the day"""
        
        # Discovery schedule with profile rotation
        schedule = [
            ("06:00", "work", "Morning deep work content"),
            ("10:00", "startup", "Business & startup content"),
            ("14:00", "learning", "Afternoon learning content"),
            ("18:00", "trends", "Evening news & trends"),
            ("22:00", "work", "Tomorrow's prep content")
        ]
        
        for time_str, profile_id, description in schedule:
            hour, minute = map(int, time_str.split(":"))
            
            self.scheduler.add_job(
                func=self._run_discovery,
                trigger=CronTrigger(hour=hour, minute=minute),
                args=[profile_id],
                id=f"discovery_{profile_id}_{time_str.replace(':', '')}",
                name=f"Discovery: {profile_id} at {time_str}",
                replace_existing=True,
                max_instances=1,
                misfire_grace_time=300  # 5 min grace period
            )
            
            logger.info(f"   ⏰ Scheduled: {time_str} - {description}")
    
    def _schedule_digests(self):
        """Schedule daily digest delivery"""
        
        # Morning digest (8 AM)
        self.scheduler.add_job(
            func=self._generate_morning_digest,
            trigger=CronTrigger(hour=8, minute=0),
            id="digest_morning",
            name="Morning Digest",
            replace_existing=True,
            max_instances=1
        )
        logger.info("   📬 Scheduled: Morning digest at 08:00")
        
        # Evening summary (6 PM)
        self.scheduler.add_job(
            func=self._generate_evening_summary,
            trigger=CronTrigger(hour=18, minute=0),
            id="digest_evening",
            name="Evening Summary",
            replace_existing=True,
            max_instances=1
        )
        logger.info("   📬 Scheduled: Evening summary at 18:00")
    
    def _run_discovery(self, profile_id: str):
        """
        Run discovery for a specific profile with error recovery
        
        Args:
            profile_id: Profile to use for discovery
        """
        start_time = datetime.now()
        logger.info(f"🔍 Starting scheduled discovery: {profile_id}")
        
        try:
            # Switch to profile
            self.profile_manager.switch_profile(profile_id)
            profile = self.profile_manager.get_active_profile()
            
            # Run discovery
            discoveries = self.discovery_engine.discover_all()
            
            # Save to database
            saved_count = 0
            for post in discoveries:
                try:
                    self.db.save_post(post)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Error saving post: {e}")
                    continue
            
            # Update metrics
            duration = (datetime.now() - start_time).total_seconds()
            self.metrics["discoveries_run"] += 1
            self.metrics["discoveries_succeeded"] += 1
            self.metrics["last_discovery"] = {
                "profile": profile_id,
                "time": datetime.now().isoformat(),
                "count": saved_count,
                "duration": duration
            }
            
            logger.info(f"✅ Discovery complete: {saved_count} posts saved ({duration:.1f}s)")
            
        except Exception as e:
            logger.error(f"❌ Discovery failed for {profile_id}: {e}")
            
            # Update metrics
            self.metrics["discoveries_run"] += 1
            self.metrics["discoveries_failed"] += 1
            self.metrics["errors"].append({
                "type": "discovery",
                "profile": profile_id,
                "time": datetime.now().isoformat(),
                "error": str(e)
            })
            
            # Retry logic (up to 3 attempts)
            retry_count = getattr(self, f"_retry_{profile_id}", 0)
            if retry_count < 3:
                setattr(self, f"_retry_{profile_id}", retry_count + 1)
                logger.info(f"🔄 Will retry {profile_id} (attempt {retry_count + 1}/3)")
                
                # Schedule retry in 10 minutes
                self.scheduler.add_job(
                    func=self._run_discovery,
                    trigger='date',
                    run_date=datetime.now().replace(second=0, microsecond=0) + \
                            timedelta(minutes=10),
                    args=[profile_id],
                    id=f"retry_{profile_id}_{retry_count}",
                    replace_existing=True
                )
            else:
                # Max retries reached
                setattr(self, f"_retry_{profile_id}", 0)
                logger.error(f"❌ Max retries reached for {profile_id}")
    
    def _generate_morning_digest(self):
        """Generate and deliver morning digest"""
        logger.info("🌅 Generating morning digest...")
        
        try:
            # Generate digest
            digest = self.digest_generator.generate_morning_digest()
            
            if digest["posts_count"] == 0:
                logger.info("📭 No new posts for morning digest")
                return
            
            # Format for Telegram
            telegram_text = self.digest_generator.format_for_telegram(digest)
            
            # Send via Telegram (if bot is available)
            self._send_to_telegram(telegram_text)
            
            # Update metrics
            self.metrics["last_digest"] = {
                "type": "morning",
                "time": datetime.now().isoformat(),
                "count": digest["posts_count"],
                "stories": len(digest["top_stories"]),
                "topics": len(digest["trending_topics"])
            }
            
            logger.info(f"✅ Morning digest sent: {digest['posts_count']} posts, "
                       f"{len(digest['top_stories'])} stories")
            
        except Exception as e:
            logger.error(f"❌ Morning digest failed: {e}")
            self.metrics["errors"].append({
                "type": "morning_digest",
                "time": datetime.now().isoformat(),
                "error": str(e)
            })
    
    def _generate_evening_summary(self):
        """Generate and deliver evening summary"""
        logger.info("🌆 Generating evening summary...")
        
        try:
            # Generate summary
            summary = self.digest_generator.generate_evening_summary()
            
            # Format for Telegram
            telegram_text = self.digest_generator.format_for_telegram(summary)
            
            # Send via Telegram
            self._send_to_telegram(telegram_text)
            
            # Update metrics
            self.metrics["last_digest"] = {
                "type": "evening",
                "time": datetime.now().isoformat(),
                "total_posts": summary["total_posts"],
                "quality_posts": summary["quality_posts"]
            }
            
            # Reset daily counters
            self.metrics["discoveries_run"] = 0
            self.metrics["discoveries_succeeded"] = 0
            
            logger.info(f"✅ Evening summary sent: {summary['total_posts']} posts, "
                       f"{summary['quality_posts']} high-quality")
            
        except Exception as e:
            logger.error(f"❌ Evening summary failed: {e}")
            self.metrics["errors"].append({
                "type": "evening_summary",
                "time": datetime.now().isoformat(),
                "error": str(e)
            })
    
    
    def _send_to_telegram(self, text: str):
        """
        Send message to Telegram (if bot is running)
        
        Args:
            text: Message to send
        """
        try:
            import os
            from telegram import Bot
            from telegram.constants import ParseMode
            import asyncio
            
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            
            if not token or not chat_id:
                logger.warning("⚠️ Telegram credentials not configured")
                return
            
            bot = Bot(token=token)
            
            # Send message async
            async def send():
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=ParseMode.HTML
                )
            
            # Run async
            asyncio.run(send())
            logger.info("✅ Message sent to Telegram")
            
        except Exception as e:
            logger.error(f"❌ Failed to send to Telegram: {e}")
    def _job_executed_listener(self, event):
        """Listen to job execution events for monitoring"""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed successfully")
    
    def print_schedule(self):
        """Print current schedule"""
        logger.info("\n📅 SCHEDULED JOBS:")
        logger.info("━" * 50)
        
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
            logger.info(f"   {job.name}")
            logger.info(f"      Next run: {next_run}")
        
        logger.info("━" * 50)
    
    def get_status(self) -> Dict[str, Any]:
        """Get automation system status"""
        return {
            "running": self.scheduler.running,
            "jobs": len(self.scheduler.get_jobs()),
            "metrics": self.metrics,
            "next_runs": [
                {
                    "job": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in self.scheduler.get_jobs()
            ]
        }
    
    def run_discovery_now(self, profile_id: Optional[str] = None):
        """
        Trigger discovery immediately (for testing/manual runs)
        
        Args:
            profile_id: Profile to use, or None for active profile
        """
        if not profile_id:
            profile_id = self.profile_manager.active_profile
        
        logger.info(f"🚀 Running immediate discovery: {profile_id}")
        self._run_discovery(profile_id)


# Global instance
_automation_instance = None


def get_automation() -> IntelligenceAutomation:
    """Get global automation instance"""
    global _automation_instance
    if _automation_instance is None:
        _automation_instance = IntelligenceAutomation()
    return _automation_instance


def test_automation():
    """Test the automation system"""
    from datetime import timedelta
    
    print("\n🧪 Testing Intelligence Automation System\n")
    
    # Create automation
    automation = IntelligenceAutomation()
    
    # Print schedule
    automation.print_schedule()
    
    # Show status
    status = automation.get_status()
    print(f"\n📊 Status:")
    print(f"   Running: {status['running']}")
    print(f"   Jobs: {status['jobs']}")
    print(f"   Discoveries run: {status['metrics']['discoveries_run']}")
    
    print("\n✅ Automation system ready!")
    print("\nTo start: automation.start()")
    print("To stop: automation.stop()")


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_automation()
