#!/usr/bin/env python3
"""
BEYONDLINES - AI-Powered Social Media Intelligence Platform

Main entry point for the BEYONDLINES application.
Autonomous content collection, analysis, and publishing system.
"""

import argparse
import asyncio
import os
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
    """Validate configuration on startup"""
    try:
        from src.utils.config import get_config
        from src.utils.config_validator import validate_config

        config = get_config()

        # Convert config to dict for validation
        config_dict = {
            "supabase_url": config.supabase_url,
            "supabase_service_role_key": config.supabase_service_role_key,
            "supabase_enabled": config.flags.get("supabase_enabled", True),
            "enable_sqlite_cache": config.flags.get("enable_sqlite_cache", False),
            "enable_analysis": config.flags.get("enable_analysis", True),
            "enable_threads": config.flags.get("enable_threads", False),
            "auto_pipeline_batch_limit": config.flags.get(
                "auto_pipeline_batch_limit", 25
            ),
            "rewriter_min_quality_score": config.flags.get(
                "rewriter_min_quality_score", 5.0
            ),
        }

        result = validate_config(config_dict)

        if not result.is_valid:
            print("❌ Configuration validation failed:")
            for error in result.errors:
                print(f"   - {error}")

            # Show warnings too
            if result.warnings:
                print("\n⚠️ Configuration warnings:")
                for warning in result.warnings:
                    print(f"   - {warning}")

            print(
                "\n⚠️ Continuing with invalid configuration (some features may not work)"
            )
            return False

        if result.warnings:
            print("⚠️ Configuration warnings:")
            for warning in result.warnings:
                print(f"   - {warning}")

        print("✅ Configuration validated successfully")
        return True

    except Exception as e:
        print(f"⚠️ Configuration validation error: {e}")
        print("⚠️ Continuing without validation (some features may not work)")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="BEYONDLINES - Social Media Content Collection and Analysis Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py collect          # Run collection service
  python main.py --help           # Show this help message
        """,
    )

    parser.add_argument(
        "command",
        nargs="?",
        default="collect",
        choices=["collect"],
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
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
