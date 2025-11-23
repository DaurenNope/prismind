# Performance Benchmark Guide

**Analysis Pipeline Performance Testing**

This guide explains how to run performance benchmarks and monitor the optimized analysis pipeline.

---

## Quick Start

### Run Full Benchmark

```bash
# Benchmark with 50 posts (default)
python scripts/testing/benchmark_analysis_performance.py

# Benchmark with 100 posts
python scripts/testing/benchmark_analysis_performance.py --posts 100

# Benchmark with custom concurrent limit
python scripts/testing/benchmark_analysis_performance.py --posts 100 --concurrent 10
```

### Monitor Metrics

```bash
# One-time metrics report
python scripts/testing/monitor_analysis_metrics.py

# Continuous monitoring (updates every 60s)
python scripts/testing/monitor_analysis_metrics.py --watch

# Custom interval
python scripts/testing/monitor_analysis_metrics.py --watch --interval 30
```

---

## Benchmark Tests

### Test 1: Batch Duplicate Checks

**What it tests:**
- Efficiency of batch duplicate checking
- Single query performance vs individual checks

**Expected results:**
- < 5ms per post
- Significant improvement over individual checks

**Run:**
```bash
python scripts/testing/benchmark_analysis_performance.py --overall-only
```

### Test 2: Parallel Processing

**What it tests:**
- Concurrent processing performance
- Throughput with 5 concurrent posts
- Time per post with parallelization

**Expected results:**
- < 3 seconds per post average
- 5-10x improvement over sequential processing

**Run:**
```bash
python scripts/testing/benchmark_analysis_performance.py --posts 50 --concurrent 5
```

### Test 3: Caching Layer

**What it tests:**
- Cache hit rates
- Performance improvement with caching
- Cache effectiveness

**Expected results:**
- 2-5x speedup on cached content
- > 50% cache hit rate (if similar content)

**Run:**
```bash
python scripts/testing/benchmark_analysis_performance.py --posts 20
```

### Test 4: Overall Performance

**What it tests:**
- End-to-end pipeline performance
- Combined optimizations
- Real-world performance

**Expected results:**
- < 3 seconds per post average
- All optimizations working together

**Run:**
```bash
python scripts/testing/benchmark_analysis_performance.py --posts 100
```

---

## Performance Targets

### Target Metrics

| Metric | Target | Excellent | Needs Improvement |
|--------|--------|-----------|-------------------|
| Time per post | < 3s | < 2s | > 5s |
| Posts per second | > 0.3 | > 0.5 | < 0.2 |
| Cache hit rate | > 50% | > 80% | < 30% |
| Duplicate check | < 5ms/post | < 2ms/post | > 10ms/post |

### Interpreting Results

**Time per post < 3s:**
- ✅ Target met - system is performing well
- Consider: Current configuration is optimal

**Time per post 3-5s:**
- ⚠️ Above target but acceptable
- Consider: Increasing concurrent limit to 10

**Time per post > 5s:**
- ❌ Needs improvement
- Actions:
  - Increase concurrent limit
  - Check for rate limiting
  - Review AI service response times
  - Investigate bottlenecks

---

## Monitoring in Production

### Key Metrics to Monitor

1. **orchestrator.analyze_batch.post_success**
   - Success rate of analysis operations
   - Target: > 95%

2. **Cache Hit Rate**
   - Percentage of cached analysis results
   - Target: > 50%

3. **Time per Post**
   - Average analysis time
   - Target: < 3s

4. **Error Rate**
   - Failed analysis operations
   - Target: < 5%

### Monitor Commands

```bash
# Check current metrics
python scripts/testing/monitor_analysis_metrics.py

# Watch metrics in real-time
python scripts/testing/monitor_analysis_metrics.py --watch

# Check last 24 hours
python scripts/testing/monitor_analysis_metrics.py --hours 24
```

### Metrics Dashboard

Access via API:
```bash
# Get metrics summary
curl http://localhost:8000/health/metrics | jq

# Get performance data
curl http://localhost:8000/health/metrics | jq '.database_performance'
```

---

## Fine-Tuning

### Adjust Concurrent Limit

**Current:** 5 concurrent posts

**To increase throughput:**
```python
# In src/pipeline/orchestrator.py, line 663
semaphore = asyncio.Semaphore(10)  # Increase from 5 to 10
```

**Monitor impact:**
- Run benchmark before/after
- Watch for rate limiting errors
- Check AI service quotas

**Recommended:**
- Start with 5
- Test with 10 if < 3s/post
- Don't exceed 10 (may hit rate limits)

### Tune Cache TTL

**Current:** 1 hour

**To increase cache hit rate:**
```python
# In src/core/analysis/intelligent_content_analyzer.py, line 72
_analysis_cache = AnalysisCache(ttl_hours=2)  # Increase from 1 to 2 hours
```

**Consider:**
- Longer TTL = more cache hits but less fresh results
- Shorter TTL = fresher results but more AI calls

### Optimize Batch Sizes

**Duplicate Check Batch Size:**
- Current: 100 posts per query
- Adjust if needed based on database performance

**Analysis Batch Size:**
- Controlled by `limit` parameter in `analyze_batch()`
- Recommended: 50-100 posts per batch

---

## Troubleshooting

### High Error Rate (> 10%)

**Symptoms:**
- Many failed analyses
- API errors in logs

**Solutions:**
1. Check AI service API keys/quota
2. Reduce concurrent limit
3. Check network connectivity
4. Review error logs

### Slow Performance (> 5s/post)

**Symptoms:**
- Analysis taking too long
- High average duration

**Solutions:**
1. Increase concurrent limit (if not rate limited)
2. Check AI service response times
3. Verify caching is working
4. Review database query performance

### Low Cache Hit Rate (< 30%)

**Symptoms:**
- Cache not being used effectively
- Many cache misses

**Solutions:**
1. Increase cache TTL
2. Review content similarity
3. Check cache is being populated
4. Verify cache check logic

### Rate Limiting Issues

**Symptoms:**
- 429 errors from AI services
- Timeout errors

**Solutions:**
1. Reduce concurrent limit
2. Add delays between batches
3. Use multiple AI service keys
4. Implement exponential backoff

---

## Example Benchmark Output

```
============================================================
Performance Benchmark: Analysis Pipeline
============================================================
Posts: 50
Concurrent: 5

============================================================
📊 Benchmark 1: Batch Duplicate Checks
============================================================
   Posts checked: 100
   Batch check time: 0.125s
   Time per post: 1.25ms
   Duplicates found: 0

============================================================
📊 Benchmark 2: Parallel Processing
============================================================
   Posts to analyze: 50
   Concurrent limit: 5
   Actual posts found: 50
   Total time: 120.50s
   Posts analyzed: 50
   Time per post: 2.410s
   Posts per second: 0.41
   Cache entries created: 50

============================================================
📊 Benchmark 3: Caching Layer
============================================================
   Posts to test: 20

   First pass (warm cache)...
   Time: 48.30s
   Cache entries: 20

   Second pass (with cache)...
   Time: 12.50s
   Speedup: 3.86x
   Cache hit rate: 100.0%
   Cache entries: 20

============================================================
📊 Overall Performance Benchmark
============================================================
   Batch size: 100 posts
   Actual posts: 100

   Results:
   Total time: 245.80s
   Posts analyzed: 98
   Time per post: 2.458s
   Duplicate check time: 0.156s
   Cache entries: 98

   Performance Evaluation:
   ✅ GOOD: 2.458s/post (target: <3s)

============================================================
📊 Benchmark Summary
============================================================
...

   Status: ✅ TARGET MET
```

---

## Next Steps

1. **Run Benchmarks**: Execute benchmark script with your data
2. **Monitor Production**: Set up continuous monitoring
3. **Fine-Tune**: Adjust settings based on results
4. **Document Results**: Keep track of performance improvements

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0






