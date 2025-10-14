#!/usr/bin/env python3
"""
Multi-Platform Bookmark Collection - Main Entry Point
Simplified orchestrator that delegates to specialized modules
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup paths
project_root = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(project_root))

# Import orchestrator
from src.pipeline.orchestrator import get_orchestrator

# Legacy compatibility exports  
from src.services.collection.platform_collectors import (
    collect_twitter_bookmarks,
    collect_reddit_bookmarks
)
from src.services.analysis.post_analyzer import analyze_and_store_post


async def main():
    """Main entry point for collection"""
    orch = get_orchestrator()
    return await orch.collect_all()


if __name__ == "__main__":
    asyncio.run(main())