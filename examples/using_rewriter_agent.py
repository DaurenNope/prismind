#!/usr/bin/env python3
"""
Example: Using RewriterAgent

Demonstrates how to use the RewriterAgent for persona-based content rewriting.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.rewriter_agent import get_rewriter_agent
from src.agents.registry import get_registry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def example_single_rewrite():
    """Example: Rewrite content for a single persona"""
    logger.info("=" * 70)
    logger.info("Example 1: Single Persona Rewrite")
    logger.info("=" * 70)
    
    # Get the rewriter agent
    rewriter = get_rewriter_agent()
    
    # Initialize the agent
    await rewriter.initialize()
    
    # Sample analyzed content
    analyzed_content = {
        "post_id": "example_123",
        "platform": "twitter",
        "content": "This is a test post about artificial intelligence and machine learning. It discusses neural networks, deep learning, and their applications.",
        "ai_summary": "Post about AI and ML covering neural networks and deep learning applications.",
        "category": "technology",
        "topics": ["ai", "machine learning", "neural networks"],
        "key_concepts": ["artificial intelligence", "deep learning"],
        "value_score": 80,
        "quality_score": 85,
        "rewrite_suggestions": [
            {
                "angle": "Technical explanation",
                "tone": "professional",
                "approach": "Explain technical concepts clearly",
                "confidence": 0.9,
            }
        ],
    }
    
    # Execute rewrite task
    task = {
        "action": "rewrite",
        "analyzed_content": analyzed_content,
        "persona": "qronoya",  # Use first available persona
        "platform": "twitter",
    }
    
    result = await rewriter.execute(task)
    
    if "error" in result:
        logger.error(f"Rewrite failed: {result['error']}")
    else:
        logger.info(f"✅ Rewrite successful!")
        logger.info(f"Persona: {result.get('persona')}")
        logger.info(f"Quality Score: {result.get('quality_score')}")
        logger.info(f"Rewritten Content:\n{result.get('rewritten_content', '')[:200]}...")
    
    return result


async def example_multi_persona():
    """Example: Generate rewrites for multiple personas"""
    logger.info("\n" + "=" * 70)
    logger.info("Example 2: Multi-Persona Generation")
    logger.info("=" * 70)
    
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    # Get available personas
    personas = list(rewriter.personas.keys())[:3]  # Use first 3 personas
    if not personas:
        logger.warning("No personas available")
        return
    
    logger.info(f"Generating rewrites for {len(personas)} personas: {personas}")
    
    analyzed_content = {
        "post_id": "example_456",
        "platform": "twitter",
        "content": "New breakthrough in quantum computing: researchers achieve 99.9% error rate reduction.",
        "ai_summary": "Quantum computing breakthrough with 99.9% error reduction.",
        "category": "technology",
        "topics": ["quantum computing", "research"],
        "rewrite_suggestions": [{"angle": "Breakthrough news", "tone": "excited", "confidence": 0.95}],
    }
    
    task = {
        "action": "rewrite_multi_persona",
        "analyzed_content": analyzed_content,
        "personas": personas,
        "platform": "auto",
    }
    
    result = await rewriter.execute(task)
    
    logger.info(f"✅ Generated {len(result.get('persona_results', {}))} rewrites")
    logger.info(f"Best Persona: {result.get('best_persona')}")
    logger.info(f"Best Score: {result.get('best_score')}")
    
    # Show quality scores for each persona
    for persona, rewrite_result in result.get("persona_results", {}).items():
        if "error" not in rewrite_result:
            logger.info(f"  {persona}: Quality {rewrite_result.get('quality_score', 'N/A')}")
    
    return result


async def example_batch_processing():
    """Example: Process multiple posts in batch"""
    logger.info("\n" + "=" * 70)
    logger.info("Example 3: Batch Processing")
    logger.info("=" * 70)
    
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    # Get first available persona
    personas = list(rewriter.personas.keys())
    if not personas:
        logger.warning("No personas available")
        return
    
    persona = personas[0]
    
    # Create batch of analyzed content
    batch = [
        {
            "analyzed_content": {
                "post_id": f"batch_{i}",
                "platform": "twitter",
                "content": f"Test post {i} about technology and innovation.",
                "ai_summary": f"Post {i} about technology.",
                "category": "technology",
                "topics": ["tech"],
                "rewrite_suggestions": [{"angle": "Tech news", "confidence": 0.8}],
            },
            "persona": persona,
        }
        for i in range(3)  # Process 3 posts
    ]
    
    task = {
        "action": "batch_rewrite",
        "batch": batch,
        "platform": "twitter",
    }
    
    result = await rewriter.execute(task)
    
    logger.info(f"✅ Batch processing complete!")
    logger.info(f"Total: {result.get('total')}")
    logger.info(f"Successful: {result.get('successful')}")
    logger.info(f"Failed: {result.get('failed')}")
    
    return result


async def example_quality_validation():
    """Example: Validate rewrite quality"""
    logger.info("\n" + "=" * 70)
    logger.info("Example 4: Quality Validation")
    logger.info("=" * 70)
    
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    personas = list(rewriter.personas.keys())
    if not personas:
        logger.warning("No personas available")
        return
    
    persona = personas[0]
    
    task = {
        "action": "validate_quality",
        "content": "This is a test rewritten content that should be validated for quality, fact accuracy, and voice consistency.",
        "original_content": "This is the original content that was rewritten for validation purposes.",
        "persona": persona,
    }
    
    result = await rewriter.execute(task)
    
    logger.info(f"✅ Quality validation complete!")
    logger.info(f"Overall Valid: {result.get('overall_valid')}")
    logger.info(f"Overall Score: {result.get('overall_score')}")
    logger.info(f"Rewrite Quality: {result.get('rewrite_quality', {}).get('score', 'N/A')}")
    logger.info(f"Fact Accuracy: {result.get('fact_accuracy', {}).get('score', 'N/A')}")
    logger.info(f"Voice Match: {result.get('voice_match', {}).get('score', 'N/A')}")
    
    return result


async def example_with_registry():
    """Example: Register agent with registry and check health"""
    logger.info("\n" + "=" * 70)
    logger.info("Example 5: Agent Registry Integration")
    logger.info("=" * 70)
    
    # Get registry
    registry = get_registry()
    
    # Get and register rewriter agent
    rewriter = get_rewriter_agent()
    registry.register(rewriter)
    
    # Initialize through registry
    await registry.initialize_agent("rewriter_agent")
    
    # Check health
    health = await rewriter.health_check()
    logger.info(f"✅ Agent Health Check:")
    logger.info(f"  Status: {health.get('status')}")
    logger.info(f"  Healthy: {health.get('healthy')}")
    logger.info(f"  Personas Loaded: {health.get('personas_loaded')}")
    
    # Get aggregate health from registry
    aggregate_health = await registry.aggregate_health()
    logger.info(f"\n✅ Registry Health:")
    logger.info(f"  Total Agents: {aggregate_health.get('total_agents')}")
    logger.info(f"  Healthy Agents: {aggregate_health.get('healthy_agents')}")
    
    return health


async def main():
    """Run all examples"""
    try:
        # Example 1: Single rewrite
        await example_single_rewrite()
        
        # Example 2: Multi-persona
        await example_multi_persona()
        
        # Example 3: Batch processing
        await example_batch_processing()
        
        # Example 4: Quality validation
        await example_quality_validation()
        
        # Example 5: Registry integration
        await example_with_registry()
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ All examples completed successfully!")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Example failed: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())

