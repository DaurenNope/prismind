# Usable Posts Table - Documentation

## Overview

The `usable_posts` table is a curated table containing only high-quality, evergreen or fresh time-sensitive posts suitable for rewriting. This table is maintained by the curation agent and automatically refreshed.

## Criteria for Inclusion

### 1. Truly Evergreen Posts (<6 months)
- `relevance_window = 'evergreen'`
- `urgency_score < 0.35` (low urgency)
- `time_sensitive = False` (not explicitly time-sensitive)
- `category != 'NEWS'` (not news)
- `category != 'DEPRECATED'` (not deprecated)
- Age < 6 months
- Has good analysis (scores > 0)

### 2. Fresh Time-Sensitive Posts (≤7 days)
- `relevance_window IN ('same-day', '24-72h', 'this-week')`
- Age ≤ 7 days
- `category != 'DEPRECATED'` (not deprecated)
- Has good analysis (scores > 0)

### 3. Commentary-Worthy Posts (manual override)
- `commentary_worthy = TRUE` (manual flag)
- Old posts that are still valuable for commentary/rewriting
- Can override age restrictions

## Exclusion Criteria

- All DEPRECATED posts
- Time-sensitive posts > 7 days old
- Evergreen posts > 6 months old
- Posts with high urgency (≥ 0.35) marked as evergreen
- Posts with `time_sensitive = True` marked as evergreen
- NEWS category posts marked as evergreen
- Posts without good analysis (scores = 0)

## Usage

### 1. Apply Migration

First, apply the migration to create the `usable_posts` table in Supabase:

```sql
-- Run migrations/2025_11_06_usable_posts_table.sql in Supabase SQL Editor
```

### 2. Populate Table

Run the curation script to populate the table:

```bash
# Dry run (test without syncing to Supabase)
python scripts/curate_usable_posts.py --dry-run

# Actually sync to Supabase
python scripts/curate_usable_posts.py
```

### 3. Auto-Refresh

The table should be refreshed:
- **On new analysis**: When a new post is analyzed, check if it should be included
- **Daily**: Run a daily cleanup job to remove expired posts and add new ones
- **On-demand**: Run the curation script manually when needed

## Table Schema

See `migrations/2025_11_06_usable_posts_table.sql` for the full schema.

Key fields:
- `inclusion_reason`: Why this post was included ('truly_evergreen', 'fresh_time_sensitive', 'commentary_worthy')
- `commentary_worthy`: Manual flag for old but valuable posts
- All fields from the `posts` table that are relevant for rewriting

## Validation

Run the validation script to check data quality:

```bash
python scripts/validate_evergreen_posts.py
```

This will show:
- How many posts are truly evergreen vs false positives
- How many time-sensitive posts are fresh vs deprecated
- Total usable posts count
- Category distribution
- Age distribution

## Expected Results

Based on current data:
- **Total usable posts**: ~238 (58.9% of analyzed posts)
- **Truly evergreen**: ~211 posts
- **Fresh time-sensitive**: ~27 posts
- **Category distribution**: TECH (135), CRYPTO (57), OTHER (25), DATING (8), BUSINESS (7), LEARNING (4), ENTERTAINMENT (2)

## Maintenance

### Daily Cleanup

Run the curation script daily to:
1. Remove expired time-sensitive posts (>7 days)
2. Remove evergreen posts that are now >6 months old
3. Add newly analyzed posts that meet the criteria
4. Update posts that have been re-analyzed

### Manual Flags

Use the `commentary_worthy` flag in the `posts` table to mark old posts that are still valuable for commentary/rewriting. These will be included in `usable_posts` even if they're older than 6 months.

## Integration

The `usable_posts` table can be used by:
1. **Rewriter**: Query for posts to rewrite based on persona, category, etc.
2. **Discovery**: Query for high-quality content to discover
3. **Scheduler**: Query for posts to schedule for publishing
4. **Analytics**: Query for quality metrics and trends

## Future Enhancements

- Auto-refresh trigger on new analysis
- Scheduled daily cleanup job
- Quality metrics dashboard
- Persona-specific views
- Category-specific views




