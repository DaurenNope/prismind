# PrisMind Component Testing Guide

This guide explains how to test individual components of the PrisMind system to ensure they work properly.

## Individual Test Scripts

We've created separate test scripts for each component:

1. `test_reddit_collector.py` - Tests the Reddit bookmark collector
2. `test_twitter_collector.py` - Tests the Twitter bookmark collector
3. `test_threads_collector.py` - Tests the Threads bookmark collector
4. `test_ai_analyzer.py` - Tests the AI content analyzer
5. `test_post_analyzer.py` - Tests the post analyzer that combines AI analysis with database storage
6. `test_orchestrator.py` - Tests the main orchestrator
7. `test_all_components.py` - Runs all tests in sequence

## New Collect-then-Analyze Approach

We've implemented a new approach that separates data collection from AI analysis:

1. `collect_then_analyze.py` - First collects all data, then analyzes it
2. `check_existing_posts.py` - Checks what posts already exist in the database

This approach ensures:
- All data is collected first without interruption from AI analysis failures
- AI analysis can be run separately and retried if needed
- Better error handling and recovery

### Run Collect-then-Analyze

```bash
# Collect from all platforms, then analyze
python collect_then_analyze.py

# Collect from specific platforms only
python collect_then_analyze.py --platforms twitter,reddit

# Limit analysis to a specific number of posts
python collect_then_analyze.py --limit 10
```

### Check Existing Posts

```bash
# Check what posts already exist in the database
python check_existing_posts.py
```

## How to Run Tests

### Run Individual Tests

```bash
# Test Reddit collector
python test_reddit_collector.py

# Test Twitter collector
python test_twitter_collector.py

# Test Threads collector
python test_threads_collector.py

# Test AI analyzer
python test_ai_analyzer.py

# Test post analyzer
python test_post_analyzer.py

# Test orchestrator
python test_orchestrator.py
```

### Run All Tests

```bash
# Run all component tests
python test_all_components.py
```

## What Each Test Does

### Collector Tests
- Initialize a real database manager (not mock) to properly check for existing posts
- Run the collector function with actual existing IDs/URLs sets from the database
- Count how many posts are collected (should be 0 if all posts already exist)
- Report success or failure

### AI Analyzer Test
- Initialize the IntelligentContentAnalyzer
- Create a test SocialPost object
- Run the analysis on the test post
- Display key results like value score and AI service used

### Post Analyzer Test
- Initialize a real database manager
- Create a test post dictionary
- Run the analyze_and_store_post function
- Verify the post is saved to the database

### Orchestrator Test
- Initialize the main orchestrator
- Run the collect_all function
- Display results from all platforms

## Expected Results

### Successful Tests
- Each test should complete without errors
- Collectors should return a count of posts collected (may be 0 if no new bookmarks exist)
- AI analyzer should return analysis results with scores
- Post analyzer should successfully save posts to the database
- Orchestrator should return results from all platforms

### Common Failure Points
- Missing environment variables (credentials)
- Network connectivity issues
- AI service timeouts
- Database connection problems
- API key issues

## Duplicate Checking

The collectors properly check for existing posts to avoid duplicates:
- They query the database for all existing post IDs and URLs
- During collection, they skip any posts that already exist in the database
- This is confirmed by log messages like "Skipping duplicate post ID: [id]"

The new collect-then-analyze approach is even more efficient:
- The collector passes existing IDs directly to the extractor to skip during collection
- It stops collection when it reaches the last collected post ID
- It stores raw data first, then enhances it with AI analysis in a separate phase

## Troubleshooting

### Environment Variables
Make sure you have the required environment variables set in your `.env` file:
- Reddit: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`
- Twitter: `TWITTER_USERNAME`, `TWITTER_PASSWORD` (or cookie file)
- Threads: Cookie file at `config/threads_cookies.json`
- AI Services: `OLLAMA_URL`, `MISTRAL_API_KEY`, `GEMINI_API_KEY`

### AI Service Configuration
If you want to use the faster Qwen 1.5B model instead of the default 7B model:
```
OLLAMA_MODEL=qwen2.5:1.5b
```

### Timeout Issues
If you experience timeout issues with AI analysis, you can skip AI analysis for testing:
1. Set `skip_ai_analysis=true` in your collection configuration
2. Or temporarily disable AI services by not setting their environment variables

### API Key Issues
If you see authentication errors with AI services:
1. Check that your API keys are correctly set in the `.env` file
2. Verify that the keys are valid and have not expired
3. For Ollama, make sure the service is running locally

## Test Output

Each test will output:
- Test name and status
- Success or error messages
- Key metrics (post counts, scores, etc.)
- Final summary of all tests

A successful test run will show:
```
✅ [Component] completed successfully
```

A failed test will show:
```
❌ [Component] failed: [error message]
```