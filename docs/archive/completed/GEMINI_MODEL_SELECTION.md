# Gemini Model Selection Strategy

## Overview
Updated model selection based on [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits) to prevent key exhaustion.

## Free Tier Rate Limits

### Best Models for Different Use Cases:

1. **Gemini 2.5 Flash-Lite** (RECOMMENDED for most operations)
   - **RPM**: 15 requests/minute
   - **TPM**: 250,000 tokens/minute
   - **RPD**: 1,000 requests/day ⭐ (BEST daily limit)
   - **Use for**: Content rewriting, analysis, most operations
   - **With 4 keys**: 4,000 RPD total capacity

2. **Gemini 2.0 Flash** (For high token usage)
   - **RPM**: 15 requests/minute
   - **TPM**: 1,000,000 tokens/minute ⭐ (BEST token limit)
   - **RPD**: 200 requests/day
   - **Use for**: Long-form content, high token requirements
   - **With 4 keys**: 800 RPD total capacity

3. **Gemini 2.5 Flash** (Balanced)
   - **RPM**: 10 requests/minute
   - **TPM**: 250,000 tokens/minute
   - **RPD**: 250 requests/day
   - **Use for**: General purpose (not recommended - lower limits)

### Models to AVOID:
- ❌ **Experimental models** (`gemini-2.0-flash-exp`): More restricted limits
- ❌ **Deprecated models** (`gemini-1.5-flash`): Lower limits, being phased out
- ❌ **Gemini 2.5 Pro**: Only 2 RPM, 50 RPD on Free Tier (too restrictive)

## Implementation

### Updated Files:
1. **`src/publishing/rewriter.py`**
   - Changed from: `gemini-2.0-flash-exp` (experimental)
   - Changed to: `gemini-2.5-flash-lite` (1,000 RPD)
   - Configurable via `GEMINI_MODEL` env var

2. **`src/core/analysis/intelligent_content_analyzer.py`**
   - Changed from: `gemini-2.0-flash` (200 RPD)
   - Changed to: `gemini-2.5-flash-lite` (1,000 RPD)
   - Configurable via `ANALYZER_GEMINI_MODEL` env var

3. **`src/core/analysis/ai_service_manager.py`**
   - Changed from: `gemini-1.5-flash` (deprecated)
   - Changed to: `gemini-2.5-flash-lite` (1,000 RPD)

## Configuration

### Environment Variables:
```bash
# Default model for rewriter (can override)
GEMINI_MODEL=gemini-2.5-flash-lite

# Override for analyzer if needed
ANALYZER_GEMINI_MODEL=gemini-2.5-flash-lite

# For high token usage, switch to:
# GEMINI_MODEL=gemini-2.0-flash  # 1M TPM but only 200 RPD
```

## Capacity Calculation

With 4 Gemini keys using `gemini-2.5-flash-lite`:
- **Daily capacity**: 4 × 1,000 = **4,000 requests/day**
- **Per-minute capacity**: 4 × 15 = **60 requests/minute** (distributed)
- **Token capacity**: 4 × 250,000 = **1,000,000 tokens/minute**

This should be sufficient for most workloads without exhausting keys.

## Monitoring

Watch for rate limit errors in logs:
- `429 Too Many Requests`: RPM limit hit
- `429 Resource Exhausted`: TPM limit hit
- `429 Quota Exceeded`: RPD limit hit

If hitting limits frequently, consider:
1. Upgrading to Tier 1 (requires billing)
2. Using `gemini-2.0-flash` for higher TPM (but lower RPD)
3. Adding more API keys for rotation
