#!/usr/bin/env python3
"""
Content Plan Generator - Strategic Content Planning System

Generates strategic content plans that distribute posts across time periods,
balance content types (breaking/trending/evergreen), and optimize posting times.
"""

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, time, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ContentPlanGenerator:
    """
    Generates strategic content plans for optimal distribution.
    
    Features:
    - Distributes posts across 7-day periods
    - Balances content types (breaking/trending/timely/evergreen)
    - Calculates optimal posting times per persona/platform
    - Prevents clustering (min 30 min between same persona/platform)
    """

    def __init__(self):
        # Peak engagement hours by platform (UTC)
        # Based on general social media engagement patterns
        self.peak_hours = {
            "twitter": [14, 15, 16, 17, 18, 19, 20, 21],  # 2 PM - 9 PM UTC
            "threads": [14, 15, 16, 17, 18, 19, 20, 21],  # Similar to Twitter
            "telegram": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],  # 8 AM - 5 PM UTC
        }
        
        # Minimum spacing between posts (minutes)
        self.min_spacing_minutes = 30

    def generate_daily_plan(self, days: int = 7) -> Dict[str, Any]:
        """
        Generate a 7-day content plan with optimal distribution.
        
        Args:
            days: Number of days to plan (default: 7)
            
        Returns:
            Dictionary with plan structure and recommendations
        """
        plan = {
            "plan_period_days": days,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "content_distribution": {
                "breaking": {"count": 0, "schedule": "immediate"},
                "trending": {"count": 0, "schedule": "within_1_hour"},
                "timely": {"count": 0, "schedule": "within_24_hours"},
                "evergreen": {"count": 0, "schedule": "distributed_7_days"},
            },
            "recommendations": [],
        }
        
        logger.info(f"📅 Generated {days}-day content plan")
        return plan

    def optimize_schedule(
        self, posts: List[Dict[str, Any]], persona: Optional[str] = None, platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Distribute posts across time to prevent clustering.
        
        Ensures minimum spacing (30 min) between posts from same persona/platform.
        
        Args:
            posts: List of posts with scheduling decisions
            persona: Optional persona filter
            platform: Optional platform filter
            
        Returns:
            List of posts with optimized scheduled times
        """
        if not posts:
            return []
        
        # Sort by priority (highest first)
        sorted_posts = sorted(
            posts, 
            key=lambda p: p.get("priority", 0), 
            reverse=True
        )
        
        optimized = []
        last_scheduled: Dict[Tuple[str, str], datetime] = {}  # (persona, platform) -> last_time
        
        for post in sorted_posts:
            post_persona = post.get("persona_key") or persona
            post_platform = post.get("platform") or platform
            
            if not post_persona or not post_platform:
                optimized.append(post)
                continue
            
            key = (post_persona, post_platform)
            original_time = post.get("scheduled_at")
            
            if isinstance(original_time, str):
                try:
                    original_time = datetime.fromisoformat(original_time.replace("Z", "+00:00"))
                except Exception:
                    original_time = datetime.now(timezone.utc)
            elif not isinstance(original_time, datetime):
                original_time = datetime.now(timezone.utc)
            
            # Check if we need to adjust for clustering
            last_time = last_scheduled.get(key)
            if last_time:
                min_time = last_time + timedelta(minutes=self.min_spacing_minutes)
                if original_time < min_time:
                    original_time = min_time
                    logger.debug(
                        f"   ⏱️  Adjusted {post_persona}/{post_platform} to prevent clustering: {original_time}"
                    )
            
            post["scheduled_at"] = original_time
            last_scheduled[key] = original_time
            optimized.append(post)
        
        logger.info(f"✅ Optimized schedule for {len(optimized)} posts")
        return optimized

    def calculate_optimal_times(
        self, persona: str, platform: str, base_time: Optional[datetime] = None
    ) -> List[datetime]:
        """
        Calculate optimal posting times for a persona/platform combination.
        
        Args:
            persona: Persona key
            platform: Platform name
            base_time: Base time to calculate from (default: now)
            
        Returns:
            List of optimal posting times (next 7 days)
        """
        if base_time is None:
            base_time = datetime.now(timezone.utc)
        
        peak_hours = self.peak_hours.get(platform, [14, 15, 16, 17, 18, 19, 20, 21])
        optimal_times = []
        
        # Generate optimal times for next 7 days
        for day_offset in range(7):
            target_date = base_time + timedelta(days=day_offset)
            
            # Pick 2-3 peak hours per day
            for hour in peak_hours[:3]:  # Top 3 peak hours
                optimal_time = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
                if optimal_time > base_time:
                    optimal_times.append(optimal_time)
        
        return sorted(optimal_times)[:14]  # Return top 14 times (2 per day for 7 days)

    def balance_content_types(
        self, posts: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Balance content types across the schedule.
        
        Groups posts by time_sensitivity and ensures proper distribution.
        
        Args:
            posts: List of posts with time_sensitivity metadata
            
        Returns:
            Dictionary mapping content types to post lists
        """
        balanced = {
            "breaking": [],
            "trending": [],
            "timely": [],
            "evergreen": [],
        }
        
        for post in posts:
            time_sensitivity = post.get("time_sensitivity", "evergreen")
            if time_sensitivity in balanced:
                balanced[time_sensitivity].append(post)
            else:
                balanced["evergreen"].append(post)
        
        # Log distribution
        total = len(posts)
        if total > 0:
            logger.info("📊 Content type distribution:")
            for content_type, post_list in balanced.items():
                count = len(post_list)
                percentage = (count / total * 100) if total > 0 else 0
                logger.info(f"   {content_type}: {count} ({percentage:.1f}%)")
        
        return balanced

    def get_next_available_slot(
        self,
        persona: str,
        platform: str,
        min_time: datetime,
        existing_schedules: List[datetime],
    ) -> datetime:
        """
        Find next available time slot that respects minimum spacing.
        
        Args:
            persona: Persona key
            platform: Platform name
            min_time: Minimum time to schedule
            existing_schedules: List of already scheduled times for this persona/platform
            
        Returns:
            Next available datetime
        """
        if not existing_schedules:
            return min_time
        
        # Sort existing schedules
        sorted_schedules = sorted(existing_schedules)
        
        # Find first gap that's >= min_spacing_minutes
        for existing_time in sorted_schedules:
            if min_time < existing_time:
                gap = (existing_time - min_time).total_seconds() / 60
                if gap >= self.min_spacing_minutes:
                    return min_time
                # Need to schedule after this existing time
                min_time = existing_time + timedelta(minutes=self.min_spacing_minutes)
        
        # If we get here, schedule after the last existing time
        if sorted_schedules:
            last_time = sorted_schedules[-1]
            return last_time + timedelta(minutes=self.min_spacing_minutes)
        
        return min_time


class ContentPlanOptimizer:
    """
    Optimizes content scheduling to maximize engagement and avoid clustering.
    
    Features:
    - Redistributes posts across optimal engagement windows
    - Detects and prevents clustering (min 30 min between same persona/platform)
    - Calculates engagement windows per persona/platform
    - Balances content mix (breaking/trending/evergreen)
    - Integrates with scheduled_posts database table
    """
    
    def __init__(self):
        # Peak engagement hours by platform (UTC)
        # Based on research: Twitter/Threads peak at 2-9 PM UTC, Telegram 8 AM-5 PM UTC
        self.peak_hours = {
            "twitter": [14, 15, 16, 17, 18, 19, 20, 21],  # 2 PM - 9 PM UTC
            "threads": [14, 15, 16, 17, 18, 19, 20, 21],  # Similar to Twitter
            "telegram": [8, 9, 10, 11, 12, 13, 14, 15, 16, 17],  # 8 AM - 5 PM UTC
        }
        
        # Off-hours to avoid (2-6 AM local time)
        self.off_hours_local = [2, 3, 4, 5]  # 2 AM - 6 AM
        
        # Minimum spacing between posts (minutes)
        self.min_spacing_minutes = 30
        
        # Maximum posts per persona per day
        self.max_posts_per_persona_per_day = 3
        
        # Persona configurations cache
        self._persona_configs: Dict[str, Dict[str, Any]] = {}
        
        # Load persona configs
        self._load_persona_configs()
    
    def _load_persona_configs(self) -> None:
        """Load persona configurations from config/personas/ directory."""
        config_dir = Path(__file__).parent.parent.parent.parent / "config" / "personas"
        
        if not config_dir.exists():
            logger.warning(f"Persona config directory not found: {config_dir}")
            return
        
        for config_file in config_dir.glob("*.json"):
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    persona_key = config_file.stem  # filename without extension
                    self._persona_configs[persona_key] = config
                    logger.debug(f"Loaded persona config: {persona_key}")
            except Exception as e:
                logger.warning(f"Failed to load persona config {config_file}: {e}")
    
    def _get_persona_timezone(self, persona: str) -> Optional[str]:
        """Get timezone for persona from config, defaults to UTC."""
        config = self._persona_configs.get(persona, {})
        # Check for timezone in config (if added in future)
        return config.get("timezone", "UTC")
    
    def _get_persona_preferred_hours(self, persona: str, platform: str) -> Optional[List[int]]:
        """Get persona-specific preferred posting hours if configured."""
        config = self._persona_configs.get(persona, {})
        scheduling_prefs = config.get("scheduling_preferences", {})
        platform_prefs = scheduling_prefs.get(platform, {})
        return platform_prefs.get("preferred_hours")
    
    def detect_clustering(
        self, 
        posts: List[Dict[str, Any]], 
        window_minutes: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Detect posts that are clustered too closely together.
        
        Args:
            posts: List of posts with scheduled_at times
            window_minutes: Minimum window between posts (default: 30)
            
        Returns:
            List of clustering violations, each with:
            - post1: First post in cluster
            - post2: Second post in cluster
            - gap_minutes: Time gap between posts
            - persona: Persona key
            - platform: Platform name
        """
        if not posts or len(posts) < 2:
            return []
        
        violations = []
        
        # Group posts by (persona, platform)
        grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        
        for post in posts:
            persona = post.get("persona_key") or post.get("profile") or post.get("persona")
            platform = post.get("platform")
            
            if persona and platform:
                key = (persona, platform)
                grouped[key].append(post)
        
        # Check each group for clustering
        for (persona, platform), group_posts in grouped.items():
            # Parse and sort by scheduled_at or scheduled_time
            posts_with_times = []
            for post in group_posts:
                scheduled_time = post.get("scheduled_at") or post.get("scheduled_time")
                if not scheduled_time:
                    continue
                
                # Parse datetime
                if isinstance(scheduled_time, str):
                    try:
                        dt = datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
                    except Exception:
                        continue
                elif isinstance(scheduled_time, datetime):
                    dt = scheduled_time
                else:
                    continue
                
                posts_with_times.append((dt, post))
            
            # Sort by time
            posts_with_times.sort(key=lambda x: x[0])
            
            # Check for violations
            for i in range(len(posts_with_times) - 1):
                time1, post1 = posts_with_times[i]
                time2, post2 = posts_with_times[i + 1]
                
                gap_minutes = (time2 - time1).total_seconds() / 60
                
                if gap_minutes < window_minutes:
                    violations.append({
                        "post1": post1,
                        "post2": post2,
                        "gap_minutes": gap_minutes,
                        "persona": persona,
                        "platform": platform,
                        "time1": time1,
                        "time2": time2,
                    })
                    
                    logger.warning(
                        f"⚠️  Clustering detected: {persona}/{platform} posts scheduled "
                        f"{gap_minutes:.1f} minutes apart (min: {window_minutes} min)"
                    )
        
        return violations
    
    def calculate_engagement_windows(
        self, 
        persona: str, 
        platform: str,
        base_time: Optional[datetime] = None,
        days_ahead: int = 7
    ) -> List[datetime]:
        """
        Calculate optimal engagement windows for posting.
        
        Considers:
        - Platform-specific peak hours
        - Persona-specific preferences (if configured)
        - Avoids off-hours (2-6 AM local time)
        - Prefers peak engagement hours
        
        Args:
            persona: Persona key
            platform: Platform name
            base_time: Base time to calculate from (default: now)
            days_ahead: Number of days to calculate windows for (default: 7)
            
        Returns:
            List of optimal posting times (datetime objects in UTC)
        """
        if base_time is None:
            base_time = datetime.now(timezone.utc)
        
        # Get preferred hours (persona-specific or platform default)
        preferred_hours = self._get_persona_preferred_hours(persona, platform)
        if preferred_hours is None:
            preferred_hours = self.peak_hours.get(platform, [14, 15, 16, 17, 18, 19, 20, 21])
        
        optimal_windows = []
        
        # Get persona timezone (for off-hours calculation)
        persona_tz_str = self._get_persona_timezone(persona)
        # For now, assume UTC if not specified (can be enhanced with timezone conversion)
        persona_tz = timezone.utc
        
        # Generate windows for each day
        for day_offset in range(days_ahead):
            target_date = base_time.date() + timedelta(days=day_offset)
            
            # Calculate windows for preferred hours
            for hour in preferred_hours:
                window_time = datetime.combine(
                    target_date, 
                    time(hour, 0, 0), 
                    timezone.utc
                )
                
                # Skip if in the past
                if window_time <= base_time:
                    continue
                
                # Check if in off-hours (2-6 AM local)
                # Convert to local time for check
                local_hour = window_time.hour  # Simplified: assumes UTC == local for now
                # TODO: Add proper timezone conversion when persona timezones are configured
                
                # Skip off-hours
                if local_hour in self.off_hours_local:
                    continue
                
                optimal_windows.append(window_time)
                
                # Add a second window 30 minutes later for flexibility
                window_time_alt = window_time + timedelta(minutes=30)
                if window_time_alt.hour not in self.off_hours_local:
                    optimal_windows.append(window_time_alt)
        
        # Sort and limit to top windows
        optimal_windows.sort()
        
        # Log engagement windows
        logger.info(
            f"📊 Calculated {len(optimal_windows)} engagement windows for {persona}/{platform}"
        )
        
        return optimal_windows[:days_ahead * 2]  # Up to 2 per day
    
    def balance_content_mix(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Balance content mix to ensure variety.
        
        Groups posts by content type (breaking/trending/evergreen) and ensures
        proper distribution across the schedule.
        
        Args:
            posts: List of posts with content_type or time_sensitivity metadata
            
        Returns:
            Dictionary with:
            - balanced: Dict mapping content types to post lists
            - distribution: Distribution statistics
            - recommendations: List of recommendations for balancing
        """
        if not posts:
            return {
                "balanced": {},
                "distribution": {},
                "recommendations": []
            }
        
        # Group by content type
        content_types = {
            "breaking": [],
            "trending": [],
            "timely": [],
            "evergreen": [],
        }
        
        for post in posts:
            # Check multiple fields for content type
            content_type = (
                post.get("content_type") or 
                post.get("time_sensitivity") or 
                post.get("type") or
                "evergreen"
            )
            
            if content_type in content_types:
                content_types[content_type].append(post)
            else:
                # Default to evergreen for unknown types
                content_types["evergreen"].append(post)
        
        # Calculate distribution
        total = len(posts)
        distribution = {}
        recommendations = []
        
        for content_type, post_list in content_types.items():
            count = len(post_list)
            percentage = (count / total * 100) if total > 0 else 0
            distribution[content_type] = {
                "count": count,
                "percentage": percentage
            }
            
            # Generate recommendations
            if content_type == "breaking" and count == 0:
                recommendations.append("Consider adding breaking news content for immediate engagement")
            elif content_type == "trending" and percentage < 10:
                recommendations.append("Low trending content - consider adding more timely/trending posts")
            elif content_type == "evergreen" and percentage > 80:
                recommendations.append("High evergreen content - consider diversifying with more timely content")
        
        # Log distribution
        logger.info("📊 Content mix distribution:")
        for content_type, stats in distribution.items():
            logger.info(
                f"   {content_type}: {stats['count']} posts ({stats['percentage']:.1f}%)"
            )
        
        return {
            "balanced": content_types,
            "distribution": distribution,
            "recommendations": recommendations
        }
    
    def optimize_schedule(self, posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize post scheduling to maximize engagement and prevent clustering.
        
        Steps:
        1. Detect clustering violations
        2. Calculate engagement windows per persona/platform
        3. Redistribute posts to optimal times
        4. Balance content mix
        5. Enforce constraints (max posts per persona per day, min spacing)
        
        Args:
            posts: List of posts with scheduling information
                Each post should have:
                - persona_key or profile or persona
                - platform
                - scheduled_at (datetime or ISO string)
                - priority (optional, higher = more important)
                - content_type or time_sensitivity (optional)
                
        Returns:
            List of optimized posts with updated scheduled_at times
        """
        if not posts:
            logger.info("No posts to optimize")
            return []
        
        logger.info(f"🔧 Starting schedule optimization for {len(posts)} posts")
        
        # Step 1: Detect clustering
        violations = self.detect_clustering(posts, self.min_spacing_minutes)
        
        if violations:
            logger.info(f"⚠️  Detected {len(violations)} clustering violations")
        
        # Step 2: Balance content mix (for logging/reporting)
        mix_analysis = self.balance_content_mix(posts)
        if mix_analysis["recommendations"]:
            for rec in mix_analysis["recommendations"]:
                logger.info(f"💡 Recommendation: {rec}")
        
        # Step 3: Group posts by persona/platform and calculate engagement windows
        grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
        
        for post in posts:
            persona = post.get("persona_key") or post.get("profile") or post.get("persona")
            platform = post.get("platform")
            
            if persona and platform:
                key = (persona, platform)
                grouped[key].append(post)
            else:
                # Posts without persona/platform can't be optimized
                logger.warning(f"Post missing persona/platform: {post.get('id', 'unknown')}")
        
        # Step 4: Optimize each group
        optimized_posts = []
        optimization_log = []
        
        for (persona, platform), group_posts in grouped.items():
            # Calculate engagement windows
            engagement_windows = self.calculate_engagement_windows(persona, platform)
            
            if not engagement_windows:
                logger.warning(f"No engagement windows for {persona}/{platform}")
                optimized_posts.extend(group_posts)
                continue
            
            # Sort posts by priority (highest first)
            sorted_posts = sorted(
                group_posts,
                key=lambda p: p.get("priority", 0),
                reverse=True
            )
            
            # Limit to max posts per persona per day
            # Distribute across multiple days
            posts_per_day = self.max_posts_per_persona_per_day
            total_allowed = posts_per_day * 7  # 7 days
            if len(sorted_posts) > total_allowed:
                logger.warning(
                    f"⚠️  {persona}/{platform}: {len(sorted_posts)} posts exceeds max "
                    f"({total_allowed} over 7 days). Limiting to top {total_allowed}."
                )
                sorted_posts = sorted_posts[:total_allowed]
            
            # Assign posts to optimal windows
            used_windows = set()
            last_scheduled_time: Optional[datetime] = None
            window_index = 0
            
            for post in sorted_posts:
                # Handle both scheduled_at and scheduled_time field names
                original_time = post.get("scheduled_at") or post.get("scheduled_time")
                
                # Parse original time
                if isinstance(original_time, str):
                    try:
                        original_dt = datetime.fromisoformat(original_time.replace("Z", "+00:00"))
                    except Exception:
                        original_dt = datetime.now(timezone.utc)
                elif isinstance(original_time, datetime):
                    original_dt = original_time
                else:
                    original_dt = datetime.now(timezone.utc)
                
                # Find optimal time slot
                optimal_time = None
                
                # For breaking content, try to keep close to original time
                content_type = post.get("content_type") or post.get("time_sensitivity", "evergreen")
                if content_type == "breaking":
                    # Keep breaking news close to original time, but respect spacing
                    min_time = original_dt
                    if last_scheduled_time:
                        min_time = max(min_time, last_scheduled_time + timedelta(minutes=self.min_spacing_minutes))
                    
                    # Find nearest engagement window
                    for window in engagement_windows:
                        if window >= min_time and window not in used_windows:
                            optimal_time = window
                            break
                    
                    # If no window found, use minimum time
                    if optimal_time is None:
                        optimal_time = min_time
                
                else:
                    # For other content types, use engagement windows
                    # Find next available window that respects spacing
                    for i, window in enumerate(engagement_windows):
                        if window in used_windows:
                            continue
                        
                        if last_scheduled_time:
                            gap = (window - last_scheduled_time).total_seconds() / 60
                            if gap < self.min_spacing_minutes:
                                continue
                        
                        # Check spacing with other posts in same day
                        window_date = window.date()
                        same_day_posts = [
                            p for p in optimized_posts
                            if (p.get("persona_key") or p.get("profile") or p.get("persona")) == persona
                            and p.get("platform") == platform
                            and (
                                isinstance(p.get("scheduled_at"), datetime) and p["scheduled_at"].date() == window_date
                                or isinstance(p.get("scheduled_time"), datetime) and p["scheduled_time"].date() == window_date
                            )
                        ]
                        
                        # Limit posts per day
                        if len(same_day_posts) >= posts_per_day:
                            continue
                        
                        optimal_time = window
                        break
                    
                    # If no window found, use next available slot
                    if optimal_time is None:
                        if last_scheduled_time:
                            optimal_time = last_scheduled_time + timedelta(minutes=self.min_spacing_minutes)
                        else:
                            optimal_time = engagement_windows[0] if engagement_windows else datetime.now(timezone.utc)
                
                # Update post with optimized time (set both field names for compatibility)
                post["scheduled_at"] = optimal_time
                post["scheduled_time"] = optimal_time  # Database uses scheduled_time
                used_windows.add(optimal_time)
                last_scheduled_time = optimal_time
                
                # Log optimization decision
                time_diff = (optimal_time - original_dt).total_seconds() / 60
                if abs(time_diff) > 5:  # Only log if changed by more than 5 minutes
                    optimization_log.append({
                        "persona": persona,
                        "platform": platform,
                        "post_id": post.get("id"),
                        "original_time": original_dt,
                        "optimized_time": optimal_time,
                        "change_minutes": time_diff,
                        "reason": "engagement_window" if content_type != "breaking" else "spacing_adjustment"
                    })
                    
                    logger.debug(
                        f"   ⏱️  Optimized {persona}/{platform}: "
                        f"{original_dt.strftime('%Y-%m-%d %H:%M')} → "
                        f"{optimal_time.strftime('%Y-%m-%d %H:%M')} "
                        f"({time_diff:+.1f} min)"
                    )
                
                optimized_posts.append(post)
        
        # Add posts without persona/platform (unoptimized)
        for post in posts:
            persona = post.get("persona_key") or post.get("profile") or post.get("persona")
            platform = post.get("platform")
            if not persona or not platform:
                optimized_posts.append(post)
        
        logger.info(f"✅ Optimized {len(optimized_posts)} posts")
        logger.info(f"📝 Logged {len(optimization_log)} optimization decisions")
        
        # Store optimization log in posts metadata
        for post in optimized_posts:
            if "optimization_metadata" not in post:
                post["optimization_metadata"] = {}
            post["optimization_metadata"]["optimization_log"] = optimization_log
        
        return optimized_posts
    
    def update_scheduled_posts_database(
        self,
        optimized_posts: List[Dict[str, Any]],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Update scheduled_posts table with optimized times.
        
        Note: The scheduled_posts table uses 'scheduled_time' (not 'scheduled_at').
        This method handles both field names for compatibility.
        
        Args:
            optimized_posts: List of optimized posts with updated scheduled_at/scheduled_time
            dry_run: If True, only log what would be updated without making changes
            
        Returns:
            Dictionary with update results:
            - updated_count: Number of posts updated
            - errors: List of errors
            - updates: List of update details
        """
        results = {
            "updated_count": 0,
            "errors": [],
            "updates": []
        }
        
        if not optimized_posts:
            logger.info("No posts to update in database")
            return results
        
        if dry_run:
            logger.info(f"🔍 DRY RUN: Would update {len(optimized_posts)} posts in database")
            for post in optimized_posts:
                post_id = post.get("id")
                scheduled_time = post.get("scheduled_time") or post.get("scheduled_at")
                logger.info(f"   Would update post {post_id} to {scheduled_time}")
            return results
        
        try:
            from src.infrastructure.database.database_agent import get_database_agent
            
            db_agent = get_database_agent()
            
            # Update each post
            for post in optimized_posts:
                post_id = post.get("id")
                if not post_id:
                    error_msg = f"Post missing ID: {post.get('persona_key', 'unknown')}/{post.get('platform', 'unknown')}"
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)
                    continue
                
                # Handle both scheduled_at and scheduled_time field names
                scheduled_time = post.get("scheduled_time") or post.get("scheduled_at")
                if not scheduled_time:
                    error_msg = f"Post {post_id} missing scheduled_time/scheduled_at"
                    logger.warning(error_msg)
                    results["errors"].append(error_msg)
                    continue
                
                # Convert datetime to ISO string if needed
                if isinstance(scheduled_time, datetime):
                    scheduled_time_str = scheduled_time.isoformat()
                else:
                    scheduled_time_str = str(scheduled_time)
                
                # Update in database using DatabaseAgent
                try:
                    # Use update_scheduled_post method if available
                    if hasattr(db_agent, 'update_scheduled_post'):
                        update_data = {"scheduled_time": scheduled_time_str}
                        db_agent.update_scheduled_post(post_id, update_data)
                        
                        results["updates"].append({
                            "post_id": post_id,
                            "new_scheduled_time": scheduled_time_str,
                            "status": "updated"
                        })
                        results["updated_count"] += 1
                        
                        logger.debug(
                            f"   ✅ Updated post {post_id} scheduled_time to {scheduled_time_str}"
                        )
                    else:
                        # Fallback: direct Supabase update
                        if hasattr(db_agent, '_supabase') and db_agent._supabase:
                            db_agent._supabase.table("scheduled_posts").update({
                                "scheduled_time": scheduled_time_str,
                                "updated_at": datetime.now(timezone.utc).isoformat()
                            }).eq("id", post_id).execute()
                            
                            results["updates"].append({
                                "post_id": post_id,
                                "new_scheduled_time": scheduled_time_str,
                                "status": "updated"
                            })
                            results["updated_count"] += 1
                        else:
                            error_msg = f"DatabaseAgent update methods not available for post {post_id}"
                            logger.warning(error_msg)
                            results["errors"].append(error_msg)
                    
                except Exception as e:
                    error_msg = f"Failed to update post {post_id}: {e}"
                    logger.error(error_msg, exc_info=True)
                    results["errors"].append(error_msg)
            
            logger.info(
                f"✅ Updated {results['updated_count']} posts in scheduled_posts table"
            )
            if results["errors"]:
                logger.warning(f"⚠️  {len(results['errors'])} errors during database update")
            
        except ImportError:
            error_msg = "DatabaseAgent not available - skipping database update"
            logger.warning(error_msg)
            results["errors"].append(error_msg)
        except Exception as e:
            error_msg = f"Database update failed: {e}"
            logger.error(error_msg, exc_info=True)
            results["errors"].append(error_msg)
        
        return results
    
    def optimize_and_update(
        self,
        posts: List[Dict[str, Any]],
        update_database: bool = True,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Complete optimization workflow: optimize schedule and update database.
        
        This is the main entry point for running optimization after initial scheduling.
        
        Args:
            posts: List of posts with scheduling information
            update_database: If True, update scheduled_posts table (default: True)
            dry_run: If True, don't make database changes (default: False)
            
        Returns:
            Dictionary with optimization results:
            - optimized_posts: List of optimized posts
            - clustering_violations: List of detected clustering issues
            - content_mix: Content mix analysis
            - database_results: Database update results (if update_database=True)
            - optimization_log: List of optimization decisions
        """
        logger.info("🚀 Starting content plan optimization workflow")
        
        # Step 1: Optimize schedule
        optimized_posts = self.optimize_schedule(posts)
        
        # Step 2: Detect clustering (after optimization)
        remaining_violations = self.detect_clustering(optimized_posts, self.min_spacing_minutes)
        
        # Step 3: Balance content mix
        content_mix = self.balance_content_mix(optimized_posts)
        
        # Step 4: Update database if requested
        database_results = None
        if update_database:
            # Normalize field names: ensure all posts use scheduled_time for database
            for post in optimized_posts:
                if "scheduled_at" in post and "scheduled_time" not in post:
                    post["scheduled_time"] = post["scheduled_at"]
            
            database_results = self.update_scheduled_posts_database(optimized_posts, dry_run=dry_run)
        
        # Extract optimization log from posts metadata
        optimization_log = []
        for post in optimized_posts:
            if "optimization_metadata" in post:
                post_log = post["optimization_metadata"].get("optimization_log", [])
                optimization_log.extend(post_log)
        
        results = {
            "optimized_posts": optimized_posts,
            "clustering_violations": remaining_violations,
            "content_mix": content_mix,
            "optimization_log": optimization_log,
        }
        
        if database_results:
            results["database_results"] = database_results
        
        logger.info(
            f"✅ Optimization complete: {len(optimized_posts)} posts optimized, "
            f"{len(remaining_violations)} remaining violations"
        )
        
        return results

