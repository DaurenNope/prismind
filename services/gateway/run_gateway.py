#!/usr/bin/env python3
"""
API Gateway Runner for Beyondlines
Starts the API Gateway with all configurations
"""

import asyncio
import logging
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
os.environ["PYTHONPATH"] = str(project_root)

from src.gateway.api_gateway import create_gateway, create_gateway_config
from src.observability.tracing import trace_function, tracer
from src.resilience.circuit_breaker import (
    AI_SERVICES_BREAKER_CONFIG,
    DATABASE_BREAKER_CONFIG,
    EXTERNAL_API_BREAKER_CONFIG,
    circuit_breaker_registry,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def setup_circuit_breakers():
    """Set up circuit breakers for external services"""
    # AI Services Circuit Breaker
    await circuit_breaker_registry.get_breaker(
        "ai_services", AI_SERVICES_BREAKER_CONFIG
    )

    # Database Circuit Breaker
    await circuit_breaker_registry.get_breaker("database", DATABASE_BREAKER_CONFIG)

    # External API Circuit Breaker
    await circuit_breaker_registry.get_breaker(
        "external_apis", EXTERNAL_API_BREAKER_CONFIG
    )

    logger.info("Circuit breakers configured")


async def start_gateway():
    """Start the API Gateway"""
    try:
        # Set up circuit breakers
        await setup_circuit_breakers()

        # Get configuration from environment
        host = os.getenv("GATEWAY_HOST", "0.0.0.0")
        port = int(os.getenv("GATEWAY_PORT", "8080"))

        logger.info(f"Starting API Gateway on {host}:{port}")

        # Create and start gateway
        gateway = await create_gateway(host, port)

        # Keep the gateway running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down API Gateway...")
        finally:
            await gateway.stop()

    except Exception as e:
        logger.error(f"Failed to start API Gateway: {e}")
        raise


@trace_function("gateway_startup")
async def main():
    """Main entry point"""
    logger.info("🚀 Starting Beyondlines API Gateway...")

    try:
        await start_gateway()
    except Exception as e:
        logger.error(f"❌ API Gateway failed to start: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
