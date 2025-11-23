# Database Sync Architecture

## Current Implementation (SQLite-First with Async Supabase Sync)

### Architecture
- **SQLite**: PRIMARY storage (always saves first, data never lost)
- **Supabase**: ASYNC SYNC destination (best-effort, tracked in SQLite)
- **Sync Tracking**: All sync status tracked in SQLite (`synced_to_supabase`, `synced_at`, `sync_error`)

### Save Flow (DatabaseAgent.save_post)
1. Normalize and validate post data
2. **Save to SQLite FIRST** (primary storage)
   - Always succeeds (local database)
   - Initialize sync status (not synced yet)
   - If SQLite save fails → Log error but continue to Supabase
3. Check for duplicates (best-effort)
4. Validate for Supabase schema (strict)
5. **Sync to Supabase** (best-effort, async)
   - Try to sync with retries (default: 3 attempts with backoff)
   - If succeeds → Mark as synced in SQLite
   - If fails → Mark as failed in SQLite with error message
6. Auto-curate to usable_posts (only if synced to Supabase and has analysis)

### Key Benefits

✅ **No Data Loss**: Posts are always saved to SQLite first
✅ **Visibility**: Can see sync status in SQLite (`synced_to_supabase`, `sync_error`)
✅ **Retry Mechanism**: Failed syncs can be retried later
✅ **Resilience**: System works even if Supabase is down
✅ **Latest Version**: Supabase gets the latest data eventually (via retry)

### Sync Status Tracking

SQLite posts table includes:
- `synced_to_supabase` (BOOLEAN): Whether post is synced to Supabase
- `synced_at` (TIMESTAMP): When post was successfully synced
- `sync_error` (TEXT): Error message if sync failed

These columns are automatically added to the SQLite schema when needed.

### Visibility and Reporting

**Check Sync Status**:
```bash
python scripts/check_sync_status.py
```

**Retry Failed Syncs**:
```bash
python scripts/retry_failed_syncs.py --limit 100
```

**Programmatic Access**:
```python
from src.database.database_agent import DatabaseAgent

db_agent = DatabaseAgent()

# Get sync status report
status = db_agent.get_sync_status_report()
print(f"Total: {status['total']}, Synced: {status['synced']}, Unsynced: {status['unsynced']}")

# Retry failed syncs
results = db_agent.retry_failed_syncs(limit=100)
print(f"Succeeded: {results['succeeded']}, Failed: {results['failed']}")

# Health report (includes sync status)
health = db_agent.health_report()
print(f"Sync status: {health['sync_status']}")
```

### Migration from Previous Architecture

The previous architecture (Supabase-primary) had these issues:
- ❌ Data loss risk if Supabase fails
- ❌ No visibility into sync status
- ❌ No retry mechanism

The new architecture (SQLite-first) fixes these:
- ✅ Data always saved to SQLite first
- ✅ Sync status tracked in SQLite
- ✅ Retry mechanism for failed syncs
- ✅ Full visibility into what's synced and what's not

### Implementation Details

#### SQLite Adapter (`src/storage/sqlite_adapter.py`)
- `_ensure_sync_columns()`: Automatically adds sync tracking columns if missing
- `mark_synced_to_supabase()`: Marks a post as synced or failed
- `get_unsynced_posts()`: Gets posts that haven't been synced
- `get_sync_status()`: Returns sync statistics

#### Database Agent (`src/database/database_agent.py`)
- `save_post()`: Saves to SQLite first, then syncs to Supabase
- `retry_failed_syncs()`: Retries syncing unsynced posts
- `get_sync_status_report()`: Returns detailed sync status with samples
- `health_report()`: Includes sync status in health check

### Testing

Tests are in `tests/test_database_sync.py`:
- ✅ Verifies SQLite-first save behavior
- ✅ Verifies sync status tracking
- ✅ Verifies retry mechanism
- ✅ Verifies visibility methods

### Monitoring

Sync status can be monitored via:
1. **Scripts**: `check_sync_status.py` and `retry_failed_syncs.py`
2. **Health Report**: `db_agent.health_report()['sync_status']`
3. **Sync Status Report**: `db_agent.get_sync_status_report()`

### Best Practices

1. **Regular Monitoring**: Check sync status regularly to ensure posts are syncing
2. **Retry Failed Syncs**: Run `retry_failed_syncs()` periodically to sync failed posts
3. **Investigate Errors**: Review `sync_error` messages for patterns indicating issues
4. **Supabase Health**: Ensure Supabase is accessible and schema is up-to-date

### Future Improvements

- [ ] Background sync job to automatically retry failed syncs
- [ ] Sync status dashboard in UI
- [ ] Alerts for high failure rates
- [ ] Batch sync optimization
- [ ] Conflict resolution for concurrent updates
