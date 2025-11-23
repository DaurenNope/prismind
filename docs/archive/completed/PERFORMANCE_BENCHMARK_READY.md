# Performance Benchmark - Ready to Run

**Status**: ✅ ALL TOOLS READY  
**Date**: 2025-01-XX

---

## Quick Start

### Run Full Performance Benchmark

```bash
# Standard benchmark (50 posts)
cd /Users/mac/Documents/Development/prismind
python scripts/testing/benchmark_analysis_performance.py

# With 100 posts
python scripts/testing/benchmark_analysis_performance.py --posts 100

# With custom concurrent limit
python scripts/testing/benchmark_analysis_performance.py --posts 100 --concurrent 10
```

### Monitor Production Metrics

```bash
# One-time metrics report
python scripts/testing/monitor_analysis_metrics.py

# Continuous monitoring (updates every 60s)
python scripts/testing/monitor_analysis_metrics.py --watch

# Custom update interval
python scripts/testing/monitor_analysis_metrics.py --watch --interval 30
```

---

## What's Implemented

### ✅ Performance Optimizations

1. **Batch Duplicate Checks**
   - Single query for multiple posts
   - Location: `src/storage/db.py::check_batch_duplicates()`
   - Status: ✅ Implemented and tested

2. **Parallel Processing**
   - 5 concurrent posts with semaphore
   - Location: `src/pipeline/orchestrator.py::analyze_batch()`
   - Status: ✅ Implemented and tested

3. **Caching Layer**
   - 1-hour TTL cache
   - Location: `src/core/analysis/intelligent_content_analyzer.py`
   - Status: ✅ Implemented and tested

### ✅ Benchmarking Tools

1. **Benchmark Script**
   - File: `scripts/testing/benchmark_analysis_performance.py`
   - Tests all three optimizations
   - Provides detailed performance metrics
   - Status: ✅ Ready to run

2. **Monitoring Script**
   - File: `scripts/testing/monitor_analysis_metrics.py`
   - Monitors cache statistics
   - Tracks analysis metrics
   - Detects rate limiting issues
   - Status: ✅ Ready to run

---

## Benchmark Test Plan

### Test 1: Batch Size 50 Posts

```bash
python scripts/testing/benchmark_analysis_performance.py --posts 50 --concurrent 5
```

**Expected Results:**
- Time per post: < 3s
- Total time: < 150s (2.5 minutes)
- Cache entries created: 50

### Test 2: Batch Size 100 Posts

```bash
python scripts/testing/benchmark_analysis_performance.py --posts 100 --concurrent 5
```

**Expected Results:**
- Time per post: < 3s
- Total time: < 300s (5 minutes)
- Cache entries created: 100

### Test 3: Cache Effectiveness

```bash
python scripts/testing/benchmark_analysis_performance.py --posts 20
```

**Expected Results:**
- First pass: ~2-3s per post
- Second pass: < 1s per post (cache hits)
- Speedup: 2-5x

### Test 4: Higher Concurrency

```bash
python scripts/testing/benchmark_analysis_performance.py --posts 50 --concurrent 10
```

**Expected Results:**
- Time per post: < 2s (if not rate limited)
- Monitor for rate limiting errors

---

## Monitoring Checklist

### Before Benchmark:

- [ ] Verify environment variables are set
- [ ] Check database connectivity
- [ ] Ensure AI service keys are configured
- [ ] Verify enough unanalyzed posts exist

### During Benchmark:

- [ ] Monitor cache hit rates
- [ ] Watch for rate limiting errors
- [ ] Check system resource usage
- [ ] Track error rates

### After Benchmark:

- [ ] Review time per post metrics
- [ ] Analyze cache effectiveness
- [ ] Check for bottlenecks
- [ ] Compare with baseline (30s/post)

---

## Key Metrics to Monitor

### 1. Time per Post

**Target**: < 3 seconds  
**Measure**: From benchmark output  
**Action if > 3s**: Increase concurrent limit or investigate bottlenecks

### 2. Cache Hit Rate

**Target**: > 50%  
**Measure**: From monitoring script  
**Action if < 50%**: Increase cache TTL or check content similarity

### 3. Error Rate

**Target**: < 5%  
**Measure**: From monitoring script  
**Action if > 5%**: Reduce concurrent limit or check API quotas

### 4. Rate Limiting

**Target**: 0 errors  
**Measure**: Watch for 429 errors  
**Action if occurring**: Reduce concurrent limit

---

## Fine-Tuning Guide

### If Time per Post > 3s:

1. **Increase Concurrent Limit** (if not rate limited)
   ```python
   # In src/pipeline/orchestrator.py line 663
   semaphore = asyncio.Semaphore(10)  # From 5 to 10
   ```

2. **Check AI Service Response Times**
   ```bash
   # Monitor via health endpoint
   curl http://localhost:8000/health/metrics | jq '.database_performance'
   ```

3. **Verify Caching is Working**
   ```bash
   # Check cache statistics
   python scripts/testing/monitor_analysis_metrics.py
   ```

### If Cache Hit Rate < 30%:

1. **Increase Cache TTL**
   ```python
   # In src/core/analysis/intelligent_content_analyzer.py line 72
   _analysis_cache = AnalysisCache(ttl_hours=2)  # From 1 to 2 hours
   ```

2. **Review Content Similarity**
   - Low cache hits may indicate diverse content
   - This is normal if content is highly unique

### If Rate Limiting Occurs:

1. **Reduce Concurrent Limit**
   ```python
   # In src/pipeline/orchestrator.py line 663
   semaphore = asyncio.Semaphore(3)  # From 5 to 3
   ```

2. **Add Delays Between Batches**
   - Implement exponential backoff
   - Monitor API quota limits

---

## Expected Performance

### Baseline (Before Optimizations):
- Sequential processing: 30s/post
- 211 posts: 2+ hours
- No caching

### Target (After Optimizations):
- Parallel + caching: < 3s/post
- 211 posts: < 15 minutes
- 10x improvement

### Actual Results:
*Run benchmarks to measure actual performance*

---

## Production Monitoring Setup

### Continuous Monitoring

```bash
# Run in background
nohup python scripts/testing/monitor_analysis_metrics.py --watch --interval 300 > /var/log/prismind/metrics.log 2>&1 &
```

### Metrics Endpoint

```bash
# Via API
curl http://localhost:8000/health/metrics | jq

# Specific metrics
curl http://localhost:8000/health/metrics | jq '.database_performance.by_operation.db_analyze_post'
```

### Alerting

Set up alerts for:
- Time per post > 5s
- Error rate > 10%
- Cache hit rate < 30%
- Rate limiting errors

---

## Troubleshooting

### Benchmark Fails to Run

**Issue**: Import errors  
**Solution**: Ensure you're in project root, verify PYTHONPATH

### No Posts Available

**Issue**: Benchmark reports no posts  
**Solution**: 
- Check database has posts
- Use `--force` flag to re-analyze existing posts
- Create test posts if needed

### High Error Rate

**Issue**: Many failed analyses  
**Solution**:
- Check AI service keys/quota
- Reduce concurrent limit
- Review error logs

---

## Next Steps

1. ✅ **Implementation Complete** - All optimizations implemented
2. ⏳ **Run Benchmarks** - Execute benchmark scripts with production data
3. ⏳ **Monitor Metrics** - Set up continuous monitoring
4. ⏳ **Fine-Tune** - Adjust settings based on results
5. ⏳ **Deploy** - Roll out to production after validation

---

**Status**: ✅ READY FOR BENCHMARKING  
**Tools Available**: ✅ YES  
**Documentation**: ✅ COMPLETE






