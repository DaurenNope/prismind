# Migration Guide: IntelligentContentAnalyzer → AnalysisAgent

**Date**: January 2025  
**Status**: Complete  
**Priority**: P0 - Critical

---

## Overview

This guide helps you migrate from `IntelligentContentAnalyzer` to the new `AnalysisAgent` that inherits from `BaseAgent` and provides enhanced features including multi-provider fallback, improved caching, quality scoring, and batch processing.

---

## What Changed

### Architecture

**Before:**
```python
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer

analyzer = IntelligentContentAnalyzer()
result = analyzer.analyze_bookmark(post)
```

**After:**
```python
from src.agents.analysis_agent import AnalysisAgent

agent = AnalysisAgent()
await agent.initialize()
result = agent.analyze_bookmark(post)  # Still works!
```

### Key Improvements

1. **Agent Framework Integration**: Now inherits from `BaseAgent` with lifecycle management, metrics, and events
2. **Multi-Provider Fallback**: Automatic fallback with health monitoring and rotation
3. **Enhanced Caching**: Better cache management with metrics
4. **Quality Scoring**: Comprehensive scoring including confidence scores
5. **Batch Processing**: Process multiple posts in parallel
6. **Better Observability**: Health checks, metrics, and event publishing

---

## Migration Steps

### Step 1: Update Imports

**Before:**
```python
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer
```

**After:**
```python
from src.agents.analysis_agent import AnalysisAgent
```

### Step 2: Initialize Agent

**Before:**
```python
analyzer = IntelligentContentAnalyzer()
```

**After:**
```python
agent = AnalysisAgent()
await agent.initialize()  # New: async initialization
```

### Step 3: Use Existing Methods (Backward Compatible)

The `analyze_bookmark` method is **100% backward compatible**:

```python
# This still works exactly the same!
result = agent.analyze_bookmark(post, include_comments=True, include_media=True)
```

### Step 4: Use New Agent Features (Optional)

#### Batch Processing

**New Feature:**
```python
task = {
    "action": "analyze_batch",
    "posts": [post1, post2, post3],
    "include_comments": True,
    "include_media": False,
}

result = await agent.execute(task)
# Returns: {"results": [...], "errors": [...], "total": 3, "successful": 3, "failed": 0}
```

#### Health Checks

**New Feature:**
```python
health = await agent.health_check()
# Returns comprehensive health data including:
# - Agent status
# - Provider health
# - Cache metrics
# - Analysis metrics
```

#### Event Publishing

**New Feature:**
```python
# Set event publisher (from messaging integration)
agent.set_event_publisher(event_publisher)

# Events are automatically published:
# - agent.initialized
# - agent.status_change
# - analysis.complete
# - agent.shutdown
```

---

## Backward Compatibility

### ✅ Fully Compatible Methods

All these methods work exactly as before:

- `analyze_bookmark(post, include_comments=True, include_media=True)`
- `analyze_content(content_data)` (via `analyze_bookmark` internally)

### ✅ Same Return Format

Analysis results have the **exact same structure**:

```python
{
    "post_id": "...",
    "platform": "...",
    "analyzed_at": "...",
    "ai_summary": "...",
    "category": "...",
    "key_concepts": [...],
    "tags": [...],
    "intelligent_value_score": 7.5,
    "content_quality_score": 8.0,
    "is_rewrite_candidate": True,
    # ... all existing fields
}
```

### ✅ New Fields Added

Additional fields are added (backward compatible):

- `confidence_score`: 0-1 confidence in analysis
- `ai_service_used`: Which provider was used
- `ai_analysis_succeeded`: Boolean indicating AI success

---

## Configuration

### Environment Variables

All existing environment variables still work:

- `GEMINI_API_KEY`
- `MISTRAL_API_KEY`
- `OLLAMA_URL`
- `ANALYZER_PRIMARY`
- `ANALYZER_RPM`, `ANALYZER_TPM`, `ANALYZER_RPD`
- `DETERMINISTIC_ANALYSIS`
- `ENABLE_VISION_ANALYSIS`

### New Configuration File

Optional YAML configuration file at `src/agents/config/analysis_agent.yaml`:

```yaml
cache:
  ttl_hours: 1

rate_limit:
  rpm: 30
  tpm: 200000
  rpd: 250

batch_processing:
  batch_size: 5
  max_workers: 3

providers:
  primary: gemini
  fallback_enabled: true
```

---

## Code Examples

### Example 1: Simple Migration

**Before:**
```python
from src.core.analysis.intelligent_content_analyzer import IntelligentContentAnalyzer

analyzer = IntelligentContentAnalyzer()
result = analyzer.analyze_bookmark(post)
print(f"Value score: {result['intelligent_value_score']}")
```

**After:**
```python
from src.agents.analysis_agent import AnalysisAgent

agent = AnalysisAgent()
await agent.initialize()
result = agent.analyze_bookmark(post)
print(f"Value score: {result['intelligent_value_score']}")
```

### Example 2: Batch Processing

**New Feature:**
```python
from src.agents.analysis_agent import AnalysisAgent

agent = AnalysisAgent()
await agent.initialize()

posts = [post1, post2, post3, post4, post5]

task = {
    "action": "analyze_batch",
    "posts": posts,
    "include_comments": False,
    "include_media": True,
}

result = await agent.execute(task)

for item in result["results"]:
    print(f"Post {item['post_id']}: {item['analysis']['intelligent_value_score']}")

if result["errors"]:
    print(f"Errors: {len(result['errors'])}")
```

### Example 3: Health Monitoring

**New Feature:**
```python
from src.agents.analysis_agent import AnalysisAgent

agent = AnalysisAgent()
await agent.initialize()

# Check health
health = await agent.health_check()

print(f"Agent status: {health['status']}")
print(f"Provider health: {health['provider_health']}")
print(f"Cache hit rate: {health['cache_metrics']['hit_rate']}")
print(f"Total analyses: {health['analysis_metrics']['total_analyses']}")
```

### Example 4: Error Handling

**Improved:**
```python
from src.agents.analysis_agent import AnalysisAgent
from src.agents.base_agent import AgentError

agent = AnalysisAgent()
await agent.initialize()

try:
    task = {
        "action": "analyze",
        "post": post,
    }
    result = await agent.execute(task)
except AgentError as e:
    print(f"Analysis failed: {e}")
    # Agent automatically handles provider fallback
```

---

## Testing

### Running Tests

```bash
# Unit tests
pytest tests/agents/test_analysis_agent.py -v

# Integration tests
pytest tests/agents/integration/test_analysis_flow.py -v

# All agent tests
pytest tests/agents/ -v
```

### Test Coverage

Target: **95%+ coverage**

```bash
pytest tests/agents/ --cov=src/agents/analysis_agent --cov-report=html
```

---

## Performance

### Benchmarks

- **Analysis latency**: < 5 seconds per post (with AI providers)
- **Batch throughput**: > 10 posts/min
- **Cache hit rate**: > 80% (with repeated analyses)

### Monitoring

```python
health = await agent.health_check()

# Check performance metrics
metrics = health["analysis_metrics"]
print(f"Avg execution time: {metrics.get('execution_time_avg', 0)}")
print(f"Total analyses: {metrics['total_analyses']}")
```

---

## Troubleshooting

### Issue: Agent Not Initializing

**Solution:**
```python
try:
    await agent.initialize()
except AgentError as e:
    print(f"Initialization failed: {e}")
    # Check dependencies and configuration
```

### Issue: Provider Failures

**Solution:**
```python
# Check provider health
health = await agent.health_check()
for provider, status in health["provider_health"].items():
    if not status["healthy"]:
        print(f"Provider {provider} is unhealthy")
        # Agent will automatically use fallback
```

### Issue: Cache Not Working

**Solution:**
```python
# Check cache metrics
health = await agent.health_check()
cache_metrics = health["cache_metrics"]
print(f"Cache hit rate: {cache_metrics['hit_rate']}")

# Clear cache if needed
agent.cache.clear()
```

---

## Deprecation Notice

The `IntelligentContentAnalyzer` class is **deprecated** but still functional. It now redirects to `AnalysisAgent` internally for backward compatibility.

**Timeline:**
- **Phase 1** (Current): Both classes work, `IntelligentContentAnalyzer` redirects to `AnalysisAgent`
- **Phase 2** (Future): `IntelligentContentAnalyzer` will show deprecation warnings
- **Phase 3** (Future): `IntelligentContentAnalyzer` will be removed

**Recommendation**: Migrate to `AnalysisAgent` as soon as possible.

---

## Support

For issues or questions:

1. Check this migration guide
2. Review test files: `tests/agents/test_analysis_agent.py`
3. Check integration tests: `tests/agents/integration/test_analysis_flow.py`
4. Review agent code: `src/agents/analysis_agent.py`

---

## Summary

✅ **100% backward compatible** - existing code works without changes  
✅ **Enhanced features** - multi-provider fallback, batch processing, better caching  
✅ **Better observability** - health checks, metrics, events  
✅ **Improved performance** - parallel processing, smarter caching  

**Migration effort**: Minimal (just update imports and add `await initialize()`)



