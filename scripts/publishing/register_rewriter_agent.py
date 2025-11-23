#!/usr/bin/env python3
"""
Register RewriterAgent with the Agent Registry

This script registers the RewriterAgent with the global agent registry
and initializes it for use in the application.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.domain.intelligence.agents.rewriter_agent import get_rewriter_agent
from src.domain.intelligence.agents.registry import get_registry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def register_rewriter_agent():
    """Register and initialize the RewriterAgent"""
    try:
        logger.info("=" * 70)
        logger.info("Registering RewriterAgent with Agent Registry")
        logger.info("=" * 70)
        
        # Get registry
        registry = get_registry()
        logger.info("✅ Agent registry retrieved")
        
        # Get rewriter agent
        rewriter = get_rewriter_agent()
        logger.info("✅ RewriterAgent instance created")
        
        # Register agent
        registry.register(rewriter)
        logger.info(f"✅ RewriterAgent registered (ID: {rewriter.agent_id})")
        
        # Initialize agent
        logger.info("Initializing RewriterAgent...")
        success = await registry.initialize_agent(rewriter.agent_id)
        
        if success:
            logger.info("✅ RewriterAgent initialized successfully")
        else:
            logger.error("❌ Failed to initialize RewriterAgent")
            return False
        
        # Check health
        logger.info("\nChecking agent health...")
        health = await rewriter.health_check()
        
        logger.info(f"  Status: {health.get('status')}")
        logger.info(f"  Healthy: {health.get('healthy')}")
        logger.info(f"  Personas Loaded: {health.get('personas_loaded', 0)}")
        
        # Show components status
        components = health.get("components", {})
        logger.info("\n  Components:")
        for component, available in components.items():
            status = "✅" if available else "❌"
            logger.info(f"    {status} {component}")
        
        # Show metrics
        metrics = health.get("rewrite_metrics", {})
        if metrics:
            logger.info("\n  Metrics:")
            logger.info(f"    Total Rewrites: {metrics.get('total_rewrites', 0)}")
            logger.info(f"    Successful: {metrics.get('successful_rewrites', 0)}")
            logger.info(f"    Failed: {metrics.get('failed_rewrites', 0)}")
            if metrics.get("total_rewrites", 0) > 0:
                logger.info(
                    f"    Success Rate: {metrics.get('success_rate', 0):.1f}%"
                )
        
        # Get registry stats
        logger.info("\nRegistry Statistics:")
        stats = registry.get_registry_stats()
        logger.info(f"  Total Agents: {stats.get('total_agents', 0)}")
        logger.info(f"  Initialized: {stats.get('initialized_agents', 0)}")
        logger.info(f"  Status Breakdown: {stats.get('status_breakdown', {})}")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ RewriterAgent registration complete!")
        logger.info("=" * 70)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Registration failed: {e}", exc_info=True)
        return False


async def main():
    """Main entry point"""
    success = await register_rewriter_agent()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())



