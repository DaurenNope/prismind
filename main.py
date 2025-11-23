#!/usr/bin/env python3
"""
BEYONDLINES - AI-Powered Social Media Intelligence Platform

Main entry point for the BEYONDLINES application.
Autonomous content collection, analysis, and publishing system.
"""

import argparse
import asyncio
import os
import signal
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def run_collector():
    """Run the collection service"""
    try:
        from scripts.run_collector import main as collector_main

        print("🔄 Starting collection service...")
        collector_main()
    except ImportError as e:
        print(f"❌ Could not import collector: {e}")
        sys.exit(1)


def verify_posting():
    """Run posting verification script"""
    try:
        import asyncio
        from scripts.verify_posting import verify

        asyncio.run(verify())
    except ImportError as e:
        print(f"❌ Could not import verification script: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        sys.exit(1)


def run_monitor():
    """Run system monitoring dashboard"""
    try:
        import asyncio
        from scripts.monitor_system import monitor

        asyncio.run(monitor())
    except ImportError as e:
        print(f"❌ Could not import monitoring script: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Monitoring failed: {e}")
        sys.exit(1)


def run_qa():
    """Run QA checks"""
    try:
        import json
        from src.agents.specialized.qa_agent import QAAgent

        qa = QAAgent()
        asyncio.run(qa.initialize())
        results = asyncio.run(qa._run_qa_suite())

        print("\n" + "=" * 80)
        print("🔍 QA REPORT")
        print("=" * 80)
        print(f"Overall Score: {results['overall_score']:.1f}%")
        print(f"Summary: {results['summary']}")
        print("\nDetails:")
        print(json.dumps(results, indent=2))
    except ImportError as e:
        print(f"❌ Could not import QA agent: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ QA check failed: {e}")
        sys.exit(1)


def start_integrated_automation():
    """Start integrated automation system"""
    from src.core.orchestration.integrated_automation import (
        IntegratedAutomationOrchestrator,
    )

    orchestrator = IntegratedAutomationOrchestrator()

    # Setup signal handlers
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        orchestrator.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run forever
    asyncio.run(orchestrator.run_forever(interval_minutes=60, use_agent_graph=True))


def setup_environment():
    """Check and setup environment"""
    env_file = Path(__file__).parent / ".env"
    env_example = Path(__file__).parent / ".env.example"

    if not env_file.exists() and env_example.exists():
        print(
            "⚠️ No .env file found. Please copy .env.example to .env and configure your settings."
        )
        return False

    return True


def validate_startup_config():
    """Validate configuration at startup"""
    from src.utils.config import get_config
    from src.utils.logging_config import get_logger

    logger = get_logger(__name__)

    try:
        config = get_config()
        is_valid, missing = config.validate_startup_config()

        if not is_valid:
            print("❌ CRITICAL: Missing required configuration:")
            for var in missing:
                print(f"   - {var}")
            print("\nPlease set these in your .env file or environment.")
            print("See docs/PRODUCTION_RUNBOOK.md for configuration guide.")

            # Log errors
            for var in missing:
                logger.error(f"Configuration error: Missing {var}")

            sys.exit(1)

        # Optional: Warning for Redis URL (non-fatal)
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            logger.warning("REDIS_URL not set - workers may not function properly")

        print("✅ Configuration validated successfully")
        logger.info("✅ Startup configuration validation passed")

    except Exception as e:
        print(f"\n❌ Configuration validation error: {e}")
        logger.exception("Configuration validation failed with exception")
        print("Please check your configuration and try again.\n")
        sys.exit(1)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="BEYONDLINES - Social Media Content Collection and Analysis Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py collect          # Run collection service
  python main.py integrated       # Run integrated automation (AgentGraph + FullAutomationLoop)
  python main.py verify-posting   # Verify content posting is working
  python main.py monitor          # Run real-time system monitoring dashboard
  python main.py qa               # Run QA checks and quality assurance
  python main.py --help          # Show this help message
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="collect",
        choices=["collect", "integrated", "verify-posting", "monitor", "qa"],
        help="Command to run (default: collect)",
    )

    parser.add_argument("--version", action="version", version="BEYONDLINES 1.0.0")

    args = parser.parse_args()

    # Setup environment
    if not setup_environment():
        sys.exit(1)

    # Validate configuration
    validate_startup_config()

    # Route to appropriate function
    if args.command == "collect":
        run_collector()
    elif args.command == "integrated":
        start_integrated_automation()
    elif args.command == "verify-posting":
        verify_posting()
    elif args.command == "monitor":
        run_monitor()
    elif args.command == "qa":
        run_qa()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
