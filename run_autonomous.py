#!/usr/bin/env python3
"""
Beyondlines Autonomous Mode Launcher
Starts the system in fully autonomous mode
"""

import argparse
import asyncio
import signal
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from src.orchestration.autonomous_manager import autonomous_manager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class AutonomousLauncher:
    """Launcher for autonomous mode"""

    def __init__(self):
        self.running = False
        self.manager = autonomous_manager

    async def start(self, mode: str = "production", health_check: bool = True):
        """Start autonomous operation"""
        logger.info("🚀 Starting Beyondlines in Autonomous Mode...")
        logger.info(f"Mode: {mode}")
        logger.info(f"Health Check: {'enabled' if health_check else 'disabled'}")

        if health_check:
            await self._pre_startup_health_check()

        # Set up signal handlers for graceful shutdown
        self._setup_signal_handlers()

        self.running = True
        try:
            await self.manager.start()
        except KeyboardInterrupt:
            logger.info("🛑 Received interrupt signal")
        except Exception as e:
            logger.error(f"❌ Autonomous mode failed: {e}")
            raise
        finally:
            await self._shutdown()

    async def _pre_startup_health_check(self):
        """Perform pre-startup health checks"""
        logger.info("🔍 Performing pre-startup health checks...")

        try:
            # Validate configuration
            from src.utils.config_validator import validate_config_at_startup

            config_result = validate_config_at_startup()

            if not config_result["valid"]:
                logger.error("❌ Configuration validation failed!")
                for error in config_result["errors"]:
                    logger.error(f"  • {error}")
                sys.exit(1)

            logger.info("✅ Configuration validation passed")

            # Test basic imports and dependencies
            await self._test_dependencies()

            logger.info("✅ All health checks passed")

        except Exception as e:
            logger.error(f"❌ Pre-startup health check failed: {e}")
            sys.exit(1)

    async def _test_dependencies(self):
        """Test critical dependencies"""
        dependencies = [
            ("Database", "src.services.new_database_manager"),
            ("AI Services", "src.core.analysis.ai_service_manager"),
            ("Publishing", "src.publishing.platforms"),
            ("API", "src.api.main"),
        ]

        for name, module_path in dependencies:
            try:
                module = __import__(module_path, fromlist=[""])
                logger.debug(f"✅ {name} module available")
            except ImportError as e:
                raise Exception(f"Critical dependency {name} not available: {e}")

    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown"""

        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}")
            self.running = False

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def _shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 Shutting down autonomous mode...")
        await self.manager.stop()
        logger.info("✅ Autonomous mode shutdown complete")

    def get_status(self):
        """Get current system status"""
        return self.manager.get_status_report()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Beyondlines Autonomous Mode")
    parser.add_argument(
        "--mode",
        choices=["development", "staging", "production"],
        default="production",
        help="Operation mode",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        default=True,
        help="Perform pre-startup health checks",
    )
    parser.add_argument(
        "--no-health-check",
        action="store_false",
        dest="health_check",
        help="Skip pre-startup health checks",
    )
    parser.add_argument(
        "--config-only",
        action="store_true",
        help="Only validate configuration and exit",
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current status and exit"
    )

    args = parser.parse_args()

    # Handle configuration-only mode
    if args.config_only:
        from src.utils.config_validator import validate_config_at_startup

        result = validate_config_at_startup()
        sys.exit(0 if result["valid"] else 1)

    # Handle status mode
    if args.status:
        launcher = AutonomousLauncher()
        try:
            status = launcher.get_status()
            print("\n" + "=" * 60)
            print("📊 Beyondlines Autonomous Status")
            print("=" * 60)
            print(f"Status: {status['status']}")
            print(f"Uptime: {status['uptime_seconds']:.1f} seconds")
            print(f"Start Time: {status['start_time']}")

            if status["health_checks"]:
                print("\nComponent Health:")
                for component, health in status["health_checks"].items():
                    status_icon = (
                        "✅"
                        if health["status"] == "healthy"
                        else "⚠️"
                        if health["status"] == "warning"
                        else "❌"
                    )
                    print(
                        f"  {status_icon} {component}: {health['status']} - {health['message']}"
                    )

            print("=" * 60)
        except Exception as e:
            logger.error(f"❌ Failed to get status: {e}")
            sys.exit(1)
        sys.exit(0)

    # Start autonomous mode
    launcher = AutonomousLauncher()
    await launcher.start(mode=args.mode, health_check=args.health_check)


if __name__ == "__main__":
    asyncio.run(main())
