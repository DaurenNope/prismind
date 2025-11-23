#!/usr/bin/env python3
"""
Real-time system monitoring dashboard for Prismind.

Displays:
- Worker status
- Due posts count
- Recent posts (24h)
- Active agents
- System health (CPU, memory)
"""

import asyncio
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.infrastructure.database.publishing.bridge import MimesisDB
from src.domain.publishing.worker import get_publisher_worker
from src.domain.intelligence.agents.monitoring_agent import MonitoringAgent


async def monitor():
    """Main monitoring loop"""
    # Initialize components
    db = MimesisDB()
    worker = get_publisher_worker()
    monitoring = MonitoringAgent()
    
    # Initialize monitoring agent if needed
    try:
        from src.domain.intelligence.agents.base_agent import AgentStatus
        if monitoring.status != AgentStatus.INITIALIZED:
            await monitoring.initialize()
    except Exception as e:
        print(f"⚠️  Warning: Monitoring agent initialization failed: {e}")
        print("   Continuing with basic monitoring...\n")
    
    print("📊 Prismind System Monitor")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Get metrics
            try:
                due = db.list_due_posts()
            except Exception as e:
                print(f"⚠️  Error getting due posts: {e}")
                due = []
            
            try:
                recent = db.get_recent_posts(hours=24)
            except Exception as e:
                print(f"⚠️  Error getting recent posts: {e}")
                recent = []
            
            # Get health check
            try:
                health = await monitoring.health_check()
            except Exception as e:
                print(f"⚠️  Error getting health check: {e}")
                health = {}
            
            # Get system resources from health check
            system_data = {}
            try:
                # Try to get system resources using monitoring agent's health check
                health_data = await monitoring.execute({
                    "action": "health_check"
                })
                if health_data.get("success"):
                    result = health_data.get("result", {})
                    system_data = result.get("system_resources", {})
            except Exception:
                # Fallback: try to get system resources using psutil directly
                try:
                    import psutil
                    system_data = {
                        "cpu": {"percent": psutil.cpu_percent(interval=0.1)},
                        "memory": {"percent": psutil.virtual_memory().percent}
                    }
                except ImportError:
                    # psutil not available, use empty data
                    system_data = {}
            
            # Get active agents count
            active_agents = 0
            try:
                if hasattr(monitoring, 'registry') and monitoring.registry:
                    active_agents = len(monitoring.registry._agents) if hasattr(monitoring.registry, '_agents') else 0
            except Exception:
                pass
            
            # Clear screen (optional - commented out for better compatibility)
            # os.system('clear' if os.name != 'nt' else 'cls')
            
            # Print metrics
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print("\r" + "=" * 70)
            print(f"Timestamp: {timestamp}")
            print(f"Worker: {'✅ RUNNING' if worker._started else '❌ STOPPED'}")
            print(f"Due Posts: {len(due)}")
            print(f"Posted (24h): {len(recent)}")
            print(f"Active Agents: {active_agents}")
            
            # System metrics
            cpu_percent = system_data.get("cpu", {}).get("percent", 0)
            memory_percent = system_data.get("memory", {}).get("percent", 0)
            print(f"CPU: {cpu_percent:.1f}%")
            print(f"Memory: {memory_percent:.1f}%")
            
            # Additional health info if available
            if health:
                overall_healthy = health.get("overall_healthy", True)
                status_emoji = "✅" if overall_healthy else "⚠️"
                print(f"System Health: {status_emoji} {'HEALTHY' if overall_healthy else 'DEGRADED'}")
            
            print("=" * 70, end="", flush=True)
            
            await asyncio.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Monitoring stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Monitoring error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(monitor())

