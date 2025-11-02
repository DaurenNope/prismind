#!/usr/bin/env python3
"""
Health Monitor for PrisMind
System health checks, performance metrics, and alerting
"""

import os
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import deque

from src.services.new_database_manager import get_database_manager


class HealthMonitor:
    """Monitor system health and performance"""
    
    def __init__(self):
        self.db = get_database_manager()
        self.start_time = datetime.now()
        
        # Metrics tracking
        self.metrics_history = {
            "discoveries": deque(maxlen=100),
            "errors": deque(maxlen=100),
            "response_times": deque(maxlen=100)
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get comprehensive system health report
        
        Returns:
            Health status with all metrics
        """
        
        health = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": self._get_uptime(),
            "components": self._check_components(),
            "performance": self._get_performance_metrics(),
            "database": self._check_database(),
            "recent_activity": self._get_recent_activity(),
            "alerts": []
        }
        
        # Determine overall status
        component_statuses = [c["status"] for c in health["components"].values()]
        
        if "critical" in component_statuses:
            health["status"] = "critical"
            health["alerts"].append("⚠️ Critical component failure")
        elif "degraded" in component_statuses:
            health["status"] = "degraded"
            health["alerts"].append("⚠️ Some components degraded")
        else:
            health["status"] = "healthy"
        
        return health
    
    def _get_uptime(self) -> str:
        """Get system uptime"""
        uptime = datetime.now() - self.start_time
        
        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m {seconds}s"
    
    def _check_components(self) -> Dict[str, Dict[str, Any]]:
        """Check status of all system components"""
        
        components = {}
        
        # Database
        try:
            posts = self.db.get_posts(limit=1)
            components["database"] = {
                "status": "healthy",
                "message": "Connected and responsive"
            }
        except Exception as e:
            components["database"] = {
                "status": "critical",
                "message": f"Database error: {e}"
            }
        
        # Ollama (AI)
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=3)
            if response.status_code == 200:
                components["ollama"] = {
                    "status": "healthy",
                    "message": "AI service available"
                }
            else:
                components["ollama"] = {
                    "status": "degraded",
                    "message": "AI service responding with errors"
                }
        except Exception as e:
            components["ollama"] = {
                "status": "degraded",
                "message": "AI service offline (optional)"
            }
        
        # Profile Manager
        try:
            from src.core.discovery.profile_manager import ProfileManager
            manager = ProfileManager()
            profiles = manager.list_profiles()
            
            components["profiles"] = {
                "status": "healthy",
                "message": f"{len(profiles)} profiles loaded"
            }
        except Exception as e:
            components["profiles"] = {
                "status": "critical",
                "message": f"Profile error: {e}"
            }
        
        # Telegram Bot
        try:
            bot_pid_file = "/tmp/prismind_bot.pid"
            if os.path.exists(bot_pid_file):
                with open(bot_pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                if psutil.pid_exists(pid):
                    components["telegram_bot"] = {
                        "status": "healthy",
                        "message": f"Bot running (PID: {pid})"
                    }
                else:
                    components["telegram_bot"] = {
                        "status": "critical",
                        "message": "Bot process not found"
                    }
            else:
                components["telegram_bot"] = {
                    "status": "degraded",
                    "message": "Bot PID file not found"
                }
        except Exception as e:
            components["telegram_bot"] = {
                "status": "degraded",
                "message": f"Bot status unknown: {e}"
            }
        
        return components
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        
        # System resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "status": "normal" if cpu_percent < 80 else "high"
            },
            "memory": {
                "used_gb": round(memory.used / (1024**3), 2),
                "total_gb": round(memory.total / (1024**3), 2),
                "percent": memory.percent,
                "status": "normal" if memory.percent < 80 else "high"
            },
            "disk": {
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": disk.percent,
                "status": "normal" if disk.percent < 90 else "low"
            }
        }
    
    def _check_database(self) -> Dict[str, Any]:
        """Check database health and statistics"""
        
        try:
            # Get post counts
            all_posts = self.db.get_posts(limit=10000)
            
            # Count by source
            bookmarks = len([p for p in all_posts if hasattr(p, 'metadata') and 
                           isinstance(p.metadata, dict) and 
                           p.metadata.get('source') == 'bookmark'])
            
            discovered = len([p for p in all_posts if hasattr(p, 'metadata') and 
                            isinstance(p.metadata, dict) and 
                            p.metadata.get('source') == 'discovered'])
            
            # Count by platform
            platforms = {}
            for post in all_posts:
                platform = post.platform if hasattr(post, 'platform') else 'unknown'
                platforms[platform] = platforms.get(platform, 0) + 1
            
            # Get recent activity (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            recent = 0
            for post in all_posts:
                if hasattr(post, 'created_at'):
                    try:
                        post_time = datetime.fromisoformat(str(post.created_at))
                        if post_time > cutoff:
                            recent += 1
                    except (ValueError, TypeError) as e:
                        pass
            
            return {
                "status": "healthy",
                "total_posts": len(all_posts),
                "bookmarks": bookmarks,
                "discovered": discovered,
                "platforms": platforms,
                "last_24h": recent
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _get_recent_activity(self) -> Dict[str, Any]:
        """Get recent system activity"""
        
        return {
            "discoveries_today": len([d for d in self.metrics_history["discoveries"] 
                                     if d.get("timestamp", datetime.min) > 
                                     datetime.now() - timedelta(days=1)]),
            "errors_today": len([e for e in self.metrics_history["errors"]
                               if e.get("timestamp", datetime.min) >
                               datetime.now() - timedelta(days=1)]),
            "avg_response_time": self._calculate_avg_response_time()
        }
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time"""
        
        if not self.metrics_history["response_times"]:
            return 0.0
        
        times = [rt["duration"] for rt in self.metrics_history["response_times"]]
        return round(sum(times) / len(times), 2)
    
    def record_discovery(self, profile: str, count: int, duration: float):
        """Record a discovery run"""
        
        self.metrics_history["discoveries"].append({
            "timestamp": datetime.now(),
            "profile": profile,
            "count": count,
            "duration": duration
        })
    
    def record_error(self, component: str, error: str):
        """Record an error"""
        
        self.metrics_history["errors"].append({
            "timestamp": datetime.now(),
            "component": component,
            "error": error
        })
    
    def record_response_time(self, operation: str, duration: float):
        """Record operation response time"""
        
        self.metrics_history["response_times"].append({
            "timestamp": datetime.now(),
            "operation": operation,
            "duration": duration
        })
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get active alerts"""
        
        alerts = []
        
        # Check for high error rate
        recent_errors = [e for e in self.metrics_history["errors"]
                        if e.get("timestamp", datetime.min) >
                        datetime.now() - timedelta(hours=1)]
        
        if len(recent_errors) > 5:
            alerts.append({
                "level": "warning",
                "message": f"High error rate: {len(recent_errors)} errors in last hour",
                "component": "system"
            })
        
        # Check for low discovery rate
        recent_discoveries = [d for d in self.metrics_history["discoveries"]
                             if d.get("timestamp", datetime.min) >
                             datetime.now() - timedelta(hours=4)]
        
        if len(recent_discoveries) == 0:
            alerts.append({
                "level": "info",
                "message": "No discoveries in last 4 hours",
                "component": "discovery"
            })
        
        # Check system resources
        health = self.get_system_health()
        perf = health.get("performance", {})
        
        if perf.get("memory", {}).get("percent", 0) > 90:
            alerts.append({
                "level": "critical",
                "message": f"Memory usage critical: {perf['memory']['percent']}%",
                "component": "system"
            })
        
        if perf.get("disk", {}).get("percent", 0) > 95:
            alerts.append({
                "level": "critical",
                "message": f"Disk space critical: {perf['disk']['percent']}%",
                "component": "system"
            })
        
        return alerts
    
    def format_health_report(self, health: Dict[str, Any]) -> str:
        """Format health report for display"""
        
        lines = [
            "╔════════════════════════════════╗",
            "║  🏥 SYSTEM HEALTH REPORT      ║",
            "╚════════════════════════════════╝\n",
            f"Status: {self._status_emoji(health['status'])} {health['status'].upper()}",
            f"Uptime: {health['uptime']}\n",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "COMPONENTS:",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        ]
        
        for name, comp in health["components"].items():
            status_emoji = self._status_emoji(comp["status"])
            lines.append(f"{status_emoji} {name.replace('_', ' ').title()}")
            lines.append(f"  {comp['message']}\n")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("PERFORMANCE:")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        perf = health["performance"]
        lines.append(f"CPU: {perf['cpu']['percent']}% ({perf['cpu']['status']})")
        lines.append(f"Memory: {perf['memory']['used_gb']}/{perf['memory']['total_gb']} GB "
                    f"({perf['memory']['percent']}%)")
        lines.append(f"Disk: {perf['disk']['free_gb']} GB free ({perf['disk']['percent']}% used)\n")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("DATABASE:")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        
        db = health["database"]
        if db["status"] == "healthy":
            lines.append(f"Total Posts: {db['total_posts']}")
            lines.append(f"Bookmarks: {db['bookmarks']}")
            lines.append(f"Discovered: {db['discovered']}")
            lines.append(f"Last 24h: {db['last_24h']}\n")
        else:
            lines.append(f"Error: {db.get('error', 'Unknown')}\n")
        
        if health["alerts"]:
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("⚠️  ALERTS:")
            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
            for alert in health["alerts"]:
                lines.append(f"• {alert}")
        
        return "\n".join(lines)
    
    def _status_emoji(self, status: str) -> str:
        """Get emoji for status"""
        return {
            "healthy": "✅",
            "degraded": "⚠️",
            "critical": "🔴",
            "normal": "✅",
            "high": "⚠️",
            "low": "🔴"
        }.get(status, "❓")


# Global instance
_health_monitor = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def test_health_monitor():
    """Test health monitor"""
    
    print("🧪 Testing Health Monitor\n")
    
    monitor = HealthMonitor()
    
    # Get health report
    health = monitor.get_system_health()
    
    # Format and display
    report = monitor.format_health_report(health)
    print(report)
    
    print("\n✅ Health monitor working!")


if __name__ == "__main__":
    test_health_monitor()
