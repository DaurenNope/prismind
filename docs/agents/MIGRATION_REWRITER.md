# Migration Guide: ContentRewriter to RewriterAgent

## Overview

This guide helps you migrate from the legacy `ContentRewriter` class to the new `RewriterAgent` that inherits from `BaseAgent`.

## What Changed

### Architecture

**Before:**
- `ContentRewriter` was a standalone class in `src/publishing/rewriter.py`
- Direct instantiation and method calls
- No agent framework integration

**After:**
- `RewriterAgent` inherits from `BaseAgent` in `src/agents/rewriter_agent.py`
- Agent framework integration with lifecycle management
- Event publishing and metrics tracking
- Health checks and dependency management

### Key Features Added

1. **Agent Framework Integration**
   - Lifecycle management (initialize, execute, shutdown)
   - Status tracking (idle, running, error, stopped)
   - Metrics collection and health checks
   - Event publishing for observability

2. **Multi-Persona Generation**
   - Generate rewrites for multiple personas in parallel
   - Automatic best persona selection based on quality scores
   - Configurable parallel execution limits

3. **Enhanced Quality Validation**
   - Comprehensive quality validation with multiple checks
   - Fact accuracy validation
   - Voice consistency verification
   - Content appropriateness checking

4. **Batch Processing**
   - Process multiple posts in parallel
   - Configurable batch sizes
   - Progress tracking and error handling per item

## Migration Steps

### Step 1: Update Imports

**Before:**
```python
from src.publishing.rewriter import ContentRewriter

rewriter = ContentRewriter()
```

**After:**
```python
from src.agents.rewriter_agent import RewriterAgent, get_rewriter_agent

# Option 1: Use singleton
rewriter = get_rewriter_agent()

# Option 2: Create instance
rewriter = RewriterAgent(
    agent_id="my_rewriter",
    agent_name="My Rewriter",
    config={"batch_size": 5}
)
```

### Step 2: Initialize the Agent

**Before:**
```python
rewriter = ContentRewriter()
# Ready to use immediately
```

**After:**
```python
rewriter = get_rewriter_agent()
await rewriter.initialize()  # Must initialize first
```

### Step 3: Update Method Calls

#### Single Rewrite

**Before:**
```python
result = await rewriter.rewrite_analyzed_post(
    analyzed_content=content,
    persona="qronoya",
    platform="twitter"
)
```

**After:**
```python
# Option 1: Use execute method (recommended)
result = await rewriter.execute({
    "action": "rewrite",
    "analyzed_content": content,
    "persona": "qronoya",
    "platform": "twitter"
})

# Option 2: Direct method call (backward compatible)
result = await rewriter.rewrite_analyzed_post(
    analyzed_content=content,
    persona="qronoya",
    platform="twitter"
)
```

#### Multi-Persona Generation

**Before:**
```python
# Had to call multiple times manually
results = {}
for persona in ["qronoya", "aspandead"]:
    results[persona] = await rewriter.rewrite_analyzed_post(
        analyzed_content=content,
        persona=persona
    )
```

**After:**
```python
# Single call with parallel execution
result = await rewriter.execute({
    "action": "rewrite_multi_persona",
    "analyzed_content": content,
    "personas": ["qronoya", "aspandead"],
    "platform": "auto"
})

# Access results
persona_results = result["persona_results"]
best_persona = result["best_persona"]  # Automatically selected
best_score = result["best_score"]
```

#### Batch Processing

**Before:**
```python
# Manual loop
results = []
for item in batch:
    result = await rewriter.rewrite_analyzed_post(
        analyzed_content=item["analyzed_content"],
        persona=item["persona"]
    )
    results.append(result)
```

**After:**
```python
# Single batch call with progress tracking
result = await rewriter.execute({
    "action": "batch_rewrite",
    "batch": [
        {"analyzed_content": item, "persona": "qronoya"}
        for item in batch
    ],
    "platform": "twitter"
})

# Access results
successful = result["results"]
errors = result["errors"]
total = result["total"]
```

#### Quality Validation

**Before:**
```python
# No built-in validation method
# Had to manually check quality
```

**After:**
```python
# Built-in quality validation
validation = await rewriter.execute({
    "action": "validate_quality",
    "content": rewritten_content,
    "original_content": original_content,
    "persona": "qronoya"
})

# Check results
is_valid = validation["overall_valid"]
score = validation["overall_score"]
rewrite_quality = validation["rewrite_quality"]
fact_accuracy = validation["fact_accuracy"]
voice_match = validation["voice_match"]
```

### Step 4: Register with Agent Registry (Optional)

If you want to use the agent registry for discovery and health monitoring:

```python
from src.agents.registry import get_registry

registry = get_registry()
rewriter = get_rewriter_agent()
registry.register(rewriter)

# Initialize through registry
await registry.initialize_agent("rewriter_agent")

# Get health status
health = await registry.aggregate_health()
```

### Step 5: Update Configuration

**Before:**
- Configuration was hardcoded or via environment variables

**After:**
- Configuration via YAML file: `src/agents/config/rewriter_agent.yaml`
- Or pass config dictionary during initialization

```python
config = {
    "batch_size": 5,
    "max_parallel_personas": 3,
    "min_quality_score": 70,
    "min_voice_consistency": 80,
}

rewriter = RewriterAgent(config=config)
```

## Backward Compatibility

The `RewriterAgent` maintains backward compatibility with `ContentRewriter`:

1. **Direct Method Calls**: You can still call `rewrite_analyzed_post()` directly
2. **Same Return Format**: Results have the same structure
3. **Same Configuration**: Uses the same config files and environment variables

## Deprecation Notice

The `ContentRewriter` class in `src/publishing/rewriter.py` is now deprecated and will redirect to `RewriterAgent`. 

**Timeline:**
- **Phase 1 (Current)**: Both classes available, `ContentRewriter` redirects to `RewriterAgent`
- **Phase 2 (Future)**: `ContentRewriter` will be removed, only `RewriterAgent` available

## New Features

### 1. Health Checks

```python
health = await rewriter.health_check()

# Returns:
# {
#     "status": "idle",
#     "healthy": true,
#     "rewrite_metrics": {
#         "total_rewrites": 100,
#         "successful_rewrites": 95,
#         "success_rate": 95.0,
#         "avg_quality_score": 82.5,
#         ...
#     },
#     "personas_loaded": 5,
#     "components": {...}
# }
```

### 2. Event Publishing

The agent automatically publishes events for:
- `rewriter.rewrite_complete` - When a single rewrite completes
- `rewriter.multi_persona_complete` - When multi-persona generation completes
- `rewriter.batch_progress` - Progress updates during batch processing
- `rewriter.batch_complete` - When batch processing completes

### 3. Metrics Tracking

Metrics are automatically tracked:
- Total rewrites
- Success/failure rates
- Quality scores
- Voice consistency scores
- Fact preservation scores
- Execution times

### 4. Error Handling

Improved error handling with `AgentError` exceptions:
```python
try:
    result = await rewriter.execute(task)
except AgentError as e:
    print(f"Agent error: {e}")
    print(f"Details: {e.details}")
```

## Testing

### Unit Tests

Run unit tests:
```bash
pytest tests/agents/test_rewriter_agent.py -v
```

### Integration Tests

Run integration tests:
```bash
pytest tests/agents/integration/test_rewriter_flow.py -v
```

### Coverage

Target coverage: 95%+

```bash
pytest tests/agents/test_rewriter_agent.py --cov=src/agents/rewriter_agent --cov-report=html
```

## Performance Benchmarks

Expected performance:
- **Rewrite latency**: < 8 seconds per persona
- **Batch throughput**: > 5 posts/min
- **Quality validation latency**: < 2 seconds

## Troubleshooting

### Issue: Agent not initializing

**Solution:**
```python
try:
    await rewriter.initialize()
except AgentError as e:
    print(f"Initialization failed: {e}")
    # Check logs for specific error
```

### Issue: No personas loaded

**Solution:**
- Ensure `config/personas/` directory exists
- Check that persona JSON files are valid
- Verify file permissions

### Issue: API keys not found

**Solution:**
- Set `GEMINI_API_KEY` environment variable
- Or set `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, etc. for rotation

### Issue: Quality validation failing

**Solution:**
- Check quality thresholds in config
- Review validation results for specific issues
- Adjust `min_quality_score` if needed

## Examples

### Example 1: Simple Rewrite

```python
from src.agents.rewriter_agent import get_rewriter_agent

async def rewrite_post():
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    analyzed_content = {
        "post_id": "123",
        "content": "Original content...",
        "ai_summary": "Summary...",
        # ... other fields
    }
    
    result = await rewriter.execute({
        "action": "rewrite",
        "analyzed_content": analyzed_content,
        "persona": "qronoya",
        "platform": "twitter"
    })
    
    print(f"Rewritten: {result['rewritten_content']}")
    print(f"Quality: {result['quality_score']}")
```

### Example 2: Multi-Persona with Best Selection

```python
async def find_best_persona():
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    result = await rewriter.execute({
        "action": "rewrite_multi_persona",
        "analyzed_content": analyzed_content,
        "personas": ["qronoya", "aspandead", "claimzilla"],
        "platform": "auto"
    })
    
    print(f"Best persona: {result['best_persona']}")
    print(f"Best score: {result['best_score']}")
    
    # Access all results
    for persona, rewrite in result["persona_results"].items():
        print(f"{persona}: {rewrite['quality_score']}")
```

### Example 3: Batch Processing with Progress

```python
async def process_batch():
    rewriter = get_rewriter_agent()
    await rewriter.initialize()
    
    # Subscribe to progress events
    rewriter.subscribe_to_events(["rewriter.batch_progress"])
    
    batch = [
        {"analyzed_content": content1, "persona": "qronoya"},
        {"analyzed_content": content2, "persona": "qronoya"},
        # ... more items
    ]
    
    result = await rewriter.execute({
        "action": "batch_rewrite",
        "batch": batch,
        "platform": "twitter"
    })
    
    print(f"Processed: {result['total']}")
    print(f"Successful: {result['successful']}")
    print(f"Failed: {result['failed']}")
```

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Review the health check output
3. Consult the test files for usage examples
4. Check the agent registry for status

## Next Steps

1. ✅ Migrate imports to use `RewriterAgent`
2. ✅ Update initialization to call `await rewriter.initialize()`
3. ✅ Update method calls to use `execute()` method
4. ✅ Take advantage of new features (multi-persona, batch, validation)
5. ✅ Register with agent registry for monitoring
6. ✅ Update tests to use new agent

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0



