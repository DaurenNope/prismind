# Posting Verification Script

## Overview

The posting verification script (`scripts/verify_posting.py`) provides a quick way to check if content posting is working correctly. It verifies the publisher worker status, checks for scheduled posts, and shows recent posting activity.

## Usage

### Via main.py (Recommended)

```bash
python main.py verify-posting
```

### Direct Execution

```bash
python scripts/verify_posting.py
```

## What It Checks

The verification script checks three key aspects of the posting system:

1. **Worker Status**: Verifies if the publisher worker is running
2. **Scheduled Posts**: Lists posts that are due to be posted
3. **Recent Posts**: Shows posts that were successfully posted in the last 24 hours

## Output Format

### Successful Verification

```
📊 Posting Verification Report
==================================================
Worker running: ✅
Due posts: 3
Posted in last 24h: 5

✅ POSTING IS WORKING!
Latest post: This is a sample post content...
  Platform: twitter
  Posted at: 2024-01-15T10:30:00Z
  URL: https://twitter.com/user/123456

Next 3 scheduled posts:
  - [twitter] 2024-01-15T11:00:00Z: Scheduled post 1... (status: pending)
  - [threads] 2024-01-15T12:00:00Z: Scheduled post 2... (status: pending)
  - [telegram] 2024-01-15T13:00:00Z: Scheduled post 3... (status: pending)
```

### No Recent Posts

```
📊 Posting Verification Report
==================================================
Worker running: ✅
Due posts: 0
Posted in last 24h: 0

⚠️ No posts found - check worker logs
```

### Worker Not Running

```
📊 Posting Verification Report
==================================================
Worker running: ❌
Due posts: 5
Posted in last 24h: 0

⚠️ No posts found - check worker logs
```

## Components

### Publisher Worker

The script checks the `PublisherWorker` instance to see if it's running:
- `worker._started`: Boolean indicating if the worker thread is active
- The worker is responsible for periodically checking and posting due items

### MimesisDB

The script uses `MimesisDB` to query posting data:

- **`list_due_posts()`**: Returns posts that are scheduled and due to be posted
  - Filters by `scheduled_time <= now()`
  - Only includes posts with status `pending` or `retry`
  - Ordered by scheduled time (earliest first)

- **`get_recent_posts(hours=24)`**: Returns posts posted in the last 24 hours
  - Queries the `posted_content` table
  - Filters by `posted_at >= (now - hours)`
  - Ordered by posted time (most recent first)

## Troubleshooting

### Worker Not Running

If the worker shows as not running:
1. Check if the worker was started: `get_publisher_worker().start()`
2. Check worker logs for errors
3. Verify Redis/database connectivity if using background workers

### No Recent Posts

If no recent posts are found:
1. Check if posts are being scheduled correctly
2. Verify the worker is processing due posts
3. Check platform API credentials and connectivity
4. Review worker logs for posting errors

### No Due Posts

If no due posts are found:
1. Check if content is being transformed and scheduled
2. Verify scheduled times are in the future
3. Check if posts were already posted (status = "posted")

## Integration

The verification script is integrated into the main CLI:

```python
# In main.py
python main.py verify-posting
```

This ensures:
- Environment is set up correctly
- Configuration is validated
- Proper error handling and exit codes

## Testing

Tests are located in `tests/integration/test_posting_verification.py`:

- `test_verify_posting_with_recent_posts`: Verifies output when posts exist
- `test_verify_posting_no_recent_posts`: Tests warning when no posts found
- `test_verify_posting_with_due_posts`: Checks scheduled posts display
- `test_verify_posting_worker_not_running`: Tests worker status check
- `test_verify_posting_no_due_posts`: Tests empty scheduled posts
- `test_verify_posting_handles_errors_gracefully`: Tests error handling

Run tests with:
```bash
pytest tests/integration/test_posting_verification.py -v
```

## Database Schema

The script queries these tables:

### scheduled_posts
- `id`: Post ID
- `scheduled_time`: When the post should be published
- `content`: Post content
- `platform`: Target platform (twitter, threads, telegram)
- `status`: Post status (pending, retry, posted)

### posted_content
- `id`: Posted content ID
- `platform`: Platform where it was posted
- `platform_post_id`: ID on the platform
- `posted_at`: When it was posted
- `post_url`: URL to the posted content
- `content`: Posted content

## Related Documentation

- [Publishing Pipeline Architecture](PUBLISHING_PIPELINE_ARCHITECTURE.md)
- [Publishing Integration](PUBLISHING_INTEGRATION_COMPLETE.md)
- [Production Runbook](PRODUCTION_RUNBOOK.md)

