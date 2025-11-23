# Ticket #8.1: Optimize Analysis Pipeline Performance

**Priority**: P0 — CRITICAL  
**Status**: ASSIGNED  
**Estimated Time**: 1 week  
**Date**: 2025-01-XX

---

## Problem Statement

**Current Performance:**
- 30 seconds per post analysis
- 2+ hours for 211 posts
- Sequential processing creates severe bottleneck
- Per-post duplicate checks are inefficient

**Root Causes:**
1. Sequential processing - one post at a time
2. Individual duplicate checks - one database query per post
3. No caching - repeated AI calls for similar content

---

## Requirements

### 1. Batch Duplicate Checks
- Single database query for multiple posts
- Check both post_id and URL duplicates
- Return mapping of post_id → is_duplicate

### 2. Parallel Processing
- Process 5-10 posts concurrently
- Use asyncio semaphore for concurrency control
- Maintain error handling and metrics

### 3. Caching Layer
- TTL: 1 hour for duplicate checks and AI responses
- Content-based hashing for cache keys
- In-memory cache with automatic expiration

---

## Implementation Plan

### Part 1: Batch Duplicate Checks ✅
**File**: `src/storage/db.py`  
**Location**: Add method after `save_post` (around line 95)

**Method**: `check_batch_duplicates(posts: List[Dict]) -> Dict[str, bool]`
- Batch query Supabase for post_ids and URLs
- Return mapping of post_id → is_duplicate
- Handle errors gracefully

### Part 2: Parallel Processing ✅
**File**: `src/pipeline/orchestrator.py`  
**Location**: `analyze_batch` method (line 664-699)

**Changes**:
- Replace sequential loop with `asyncio.gather()`
- Use semaphore to limit concurrent requests (5-10)
- Maintain error handling and metrics

### Part 3: Caching Layer ✅
**File**: `src/core/analysis/intelligent_content_analyzer.py`  
**Location**: After imports (around line 30)

**Changes**:
- Add `AnalysisCache` class with TTL support
- Cache check before AI call
- Cache store after successful analysis

---

## Acceptance Criteria

- [x] Batch duplicate checks implemented and tested
- [x] Parallel processing working (5-10 concurrent)
- [x] Caching layer active with 1-hour TTL
- [ ] Performance improved to <3 seconds per post average (requires runtime testing)
- [ ] All existing tests pass (requires test suite run)
- [x] No functionality lost (implementation maintains existing behavior)

---

## Testing Requirements

1. **Unit Tests**
   - Batch duplicate check accuracy
   - Cache hit/miss behavior
   - Parallel processing concurrency limits

2. **Integration Tests**
   - End-to-end batch analysis
   - Performance benchmarks
   - Cache effectiveness

3. **Performance Benchmarks**
   - Measure before/after performance
   - Target: <3 seconds per post average
   - Monitor cache hit rates

---

## Expected Impact

**Before:**
- 30 seconds per post
- 2+ hours for 211 posts
- Sequential processing

**After:**
- <3 seconds per post (with caching)
- <15 minutes for 211 posts (with parallel processing)
- 10x performance improvement

---

## Implementation Notes

- Maintain backward compatibility
- Ensure error handling doesn't break pipeline
- Monitor cache memory usage
- Consider Redis for distributed cache in future

---

**Status**: ✅ Implementation Complete  
**Next Steps**: Testing and Performance Validation

