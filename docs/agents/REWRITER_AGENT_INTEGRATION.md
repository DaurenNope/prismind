# RewriterAgent Integration Guide

## Overview

This guide shows how to integrate the `RewriterAgent` into your application and register it with the agent registry for monitoring and management.

## Quick Integration

### 1. Register Agent on Startup

Add this to your application startup code:

```python
from src.agents.rewriter_agent import get_rewriter_agent
from src.agents.registry import get_registry

async def setup_agents():
    """Setup and register all agents"""
    registry = get_registry()
    
    # Register RewriterAgent
    rewriter = get_rewriter_agent()
    registry.register(rewriter)
    
    # Initialize
    await registry.initialize_agent("rewriter_agent")
    
    return registry
```

### 2. Use Registration Script

Run the provided registration script:

```bash
python scripts/register_rewriter_agent.py
```

This will:
- Register the agent with the registry
- Initialize the agent
- Check health status
- Display metrics and component status

### 3. Integration in Main Application

#### Option A: Standalone Usage

```python
from src.agents.rewriter_agent import get_rewriter_agent

async def rewrite_content(analyzed_content, persona="qronoya"):
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    result = await rewriter.execute({
        "action": "rewrite",
        "analyzed_content": analyzed_content,
        "persona": persona,
        "platform": "twitter"
    })
    
    return result
```

#### Option B: Registry-Based Usage

```python
from src.agents.registry import get_registry

async def rewrite_content(analyzed_content, persona="qronoya"):
    registry = get_registry()
    rewriter = registry.get_agent("rewriter_agent")
    
    if not rewriter:
        raise RuntimeError("RewriterAgent not registered")
    
    result = await rewriter.execute({
        "action": "rewrite",
        "analyzed_content": analyzed_content,
        "persona": persona,
        "platform": "twitter"
    })
    
    return result
```

## Integration Points

### 1. Update Existing Code

The agent maintains backward compatibility, so existing code using `ContentRewriter` will continue to work. However, you can gradually migrate:

**Before:**
```python
from src.publishing.rewriter import get_rewriter

rewriter = get_rewriter()
result = await rewriter.rewrite_analyzed_post(...)
```

**After:**
```python
from src.agents.rewriter_agent import get_rewriter_agent

rewriter = get_rewriter_agent()
await rewriter.initialize()
result = await rewriter.rewrite_analyzed_post(...)  # Still works!
# Or use execute method:
result = await rewriter.execute({"action": "rewrite", ...})
```

### 2. Update Scheduler

The `PublishingScheduler` can be updated to use the agent:

```python
from src.agents.rewriter_agent import get_rewriter_agent

class PublishingScheduler:
    def __init__(self):
        self.rewriter = get_rewriter_agent()
        # Initialize on first use or in setup
        self._rewriter_initialized = False
    
    async def _ensure_rewriter_initialized(self):
        if not self._rewriter_initialized:
            await self.rewriter.initialize()
            self._rewriter_initialized = True
    
    async def schedule_all_persona_versions(self, analyzed_content, personas=None):
        await self._ensure_rewriter_initialized()
        
        # Use multi-persona generation
        result = await self.rewriter.execute({
            "action": "rewrite_multi_persona",
            "analyzed_content": analyzed_content,
            "personas": personas or list(self.rewriter.personas.keys()),
            "platform": "auto"
        })
        
        # Process results...
        return decisions
```

### 3. Update Telegram Bot

The Telegram bot can use the agent:

```python
from src.agents.rewriter_agent import get_rewriter_agent

async def rewrite_command(update, context):
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    # Use agent execute method
    result = await rewriter.execute({
        "action": "rewrite",
        "analyzed_content": analyzed_content,
        "persona": persona,
        "platform": platform
    })
    
    # Handle result...
```

## Health Monitoring

### Check Agent Health

```python
from src.agents.registry import get_registry

async def check_agent_health():
    registry = get_registry()
    health = await registry.aggregate_health()
    
    rewriter_health = health["agents"].get("rewriter_agent")
    if rewriter_health:
        print(f"Status: {rewriter_health['status']}")
        print(f"Healthy: {rewriter_health['healthy']}")
        print(f"Metrics: {rewriter_health.get('rewrite_metrics', {})}")
```

### Health Check Endpoint

If you have a health check endpoint:

```python
@app.get("/health/agents")
async def agent_health():
    registry = get_registry()
    health = await registry.aggregate_health()
    return health
```

## Event Subscriptions

Subscribe to agent events for monitoring:

```python
from src.agents.rewriter_agent import get_rewriter_agent

rewriter = get_rewriter_agent()
rewriter.subscribe_to_events([
    "rewriter.rewrite_complete",
    "rewriter.multi_persona_complete",
    "rewriter.batch_progress",
    "rewriter.batch_complete"
])

# Events will be published to the message queue
```

## Configuration

### Environment Variables

The agent uses the same environment variables as `ContentRewriter`:
- `GEMINI_API_KEY` or `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, etc.
- `VECTOR_DB_PATH` (default: `data/vector_db`)

### Configuration File

Edit `src/agents/config/rewriter_agent.yaml` to customize:
- Batch sizes
- Quality thresholds
- Performance settings
- Validation options

## Testing Integration

### Test Agent Registration

```python
import pytest
from src.agents.rewriter_agent import get_rewriter_agent
from src.agents.registry import get_registry

@pytest.mark.asyncio
async def test_agent_registration():
    registry = get_registry()
    rewriter = get_rewriter_agent()
    
    registry.register(rewriter)
    await registry.initialize_agent("rewriter_agent")
    
    assert registry.get_agent("rewriter_agent") is not None
    health = await rewriter.health_check()
    assert health["healthy"] is True
```

### Test Agent Usage

```python
@pytest.mark.asyncio
async def test_agent_usage():
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    result = await rewriter.execute({
        "action": "rewrite",
        "analyzed_content": sample_content,
        "persona": "qronoya"
    })
    
    assert "rewritten_content" in result or "error" in result
```

## Troubleshooting

### Agent Not Initializing

1. Check that personas are loaded from `config/personas/`
2. Verify API keys are set
3. Check logs for specific errors

### Agent Not Found in Registry

1. Ensure agent is registered: `registry.register(rewriter)`
2. Check agent ID matches: `rewriter.agent_id == "rewriter_agent"`

### Health Check Failing

1. Check component status in health check output
2. Verify all dependencies are available
3. Review error logs

## Next Steps

1. ✅ Register agent with registry
2. ✅ Update existing code to use agent
3. ✅ Set up health monitoring
4. ✅ Configure event subscriptions
5. ✅ Add to application startup

See `docs/agents/MIGRATION_REWRITER.md` for detailed migration guide.



