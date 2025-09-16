# PrisMind Collection Scripts

## Trigger Collections

The `trigger_collections.py` script allows you to manually trigger both Twitter and Reddit collections at once.

### Usage

```bash
python3 scripts/trigger_collections.py
```

Or use the shell script:

```bash
./trigger_collections.sh
```

### What it does

1. Initializes the database connection
2. Runs Twitter collection using the `collect_twitter_bookmarks_sync` function
3. Runs Reddit collection using the `collect_reddit_bookmarks` function
4. Reports the total number of new posts collected

### Requirements

- Python 3.x
- All environment variables required for Twitter and Reddit authentication:
  - Twitter: `TWITTER_USERNAME`, `TWITTER_PASSWORD`
  - Reddit: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`

### GitHub Actions Integration

The collection process is also integrated with GitHub Actions:

- **Existing Workflow**: The `automated-collection.yml` workflow runs Reddit collection on a schedule
- **New Combined Workflow**: The `combined-collection.yml` workflow runs both Twitter and Reddit collections using the `trigger_collections.py` script

You can manually trigger either workflow from the GitHub Actions tab in the repository.

### Troubleshooting

If you encounter errors:

1. Check that all required environment variables are set
2. Verify that the database exists at `data/prismind.db`
3. Check the logs for specific error messages