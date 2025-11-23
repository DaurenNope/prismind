# RewriterAgent Quick Start Guide

## Overview

The `RewriterAgent` is a refactored version of `ContentRewriter` that inherits from `BaseAgent` and provides persona-based content rewriting with quality validation, multi-persona generation, and batch processing.

## Quick Start

### 1. Basic Usage

```python
from src.agents.rewriter_agent import get_rewriter_agent

# Get the agent (singleton)
rewriter = get_rewriter_agent()

# Initialize
await rewriter.initialize()

# Rewrite content
result = await rewriter.execute({
    "action": "rewrite",
    "analyzed_content": analyzed_content,
    "persona": "qronoya",
    "platform": "twitter"
})

print(result["rewritten_content"])
```

### 2. Multi-Persona Generation

```python
# Generate rewrites for multiple personas in parallel
result = await rewriter.execute({
    "action": "rewrite_multi_persona",
    "analyzed_content": analyzed_content,
    "personas": ["qronoya", "aspandead", "claimzilla"],
    "platform": "auto"
})

# Get best persona automatically selected
best_persona = result["best_persona"]
best_rewrite = result["persona_results"][best_persona]
```

### 3. Batch Processing

```python
# Process multiple posts in parallel
result = await rewriter.execute({
    "action": "batch_rewrite",
    "batch": [
        {"analyzed_content": content1, "persona": "qronoya"},
        {"analyzed_content": content2, "persona": "qronoya"},
    ],
    "platform": "twitter"
})

print(f"Processed: {result['successful']}/{result['total']}")
```

### 4. Quality Validation

```python
# Validate rewrite quality
validation = await rewriter.execute({
    "action": "validate_quality",
    "content": rewritten_content,
    "original_content": original_content,
    "persona": "qronoya"
})

if validation["overall_valid"]:
    print(f"Quality score: {validation['overall_score']}")
```

## Agent Registry Integration

```python
from src.agents.registry import get_registry

# Register agent
registry = get_registry()
rewriter = get_rewriter_agent()
registry.register(rewriter)

# Initialize through registry
await registry.initialize_agent("rewriter_agent")

# Check health
health = await rewriter.health_check()
print(f"Status: {health['status']}, Healthy: {health['healthy']}")
```

## Configuration

Configuration is loaded from `src/agents/config/rewriter_agent.yaml` or can be passed during initialization:

```python
config = {
    "batch_size": 5,
    "max_parallel_personas": 3,
    "min_quality_score": 70,
}

rewriter = RewriterAgent(config=config)
```

## Backward Compatibility

The agent maintains backward compatibility with `ContentRewriter`:

```python
# Old way (still works)
from src.publishing.rewriter import get_rewriter
rewriter = get_rewriter()
result = await rewriter.rewrite_analyzed_post(...)

# New way (recommended)
from src.agents.rewriter_agent import get_rewriter_agent
rewriter = get_rewriter_agent()
await rewriter.initialize()
result = await rewriter.rewrite_analyzed_post(...)  # Still works!
```

## Examples

See `examples/using_rewriter_agent.py` for complete examples.

## Migration

See `docs/agents/MIGRATION_REWRITER.md` for detailed migration guide.



