# Setting Up the Reddit Collector Cron Job

This guide explains how to set up a scheduled task to run the Reddit collector script periodically on macOS.

## Prerequisites

1. Python 3.7 or higher installed
2. Required Python packages installed (install with `pip install -r requirements.txt`)
3. Reddit API credentials configured in `.env` file

## Manual Cron Job Setup

### Step 1: Make the Script Executable

```bash
chmod +x /path/to/prismind/scripts/scheduled_reddit_collector.py
```

### Step 2: Edit the Crontab

1. Open your crontab for editing:
   ```bash
   crontab -e
   ```

2. Add the following line to run the script every 6 hours:
   ```
   0 */6 * * * cd /path/to/prismind && /usr/bin/python3 /path/to/prismind/scripts/scheduled_reddit_collector.py --limit 50 >> /path/to/prismind/logs/reddit_collector.log 2>&1
   ```

   Replace `/path/to/prismind` with the actual path to your project directory.

3. Save and exit the editor (in vim, press `Esc` then type `:wq` and press `Enter`).

### Step 3: Verify the Cron Job

1. List your current cron jobs:
   ```bash
   crontab -l
   ```

2. Check the log file for output:
   ```bash
   tail -f /path/to/prismind/logs/reddit_collector.log
   ```

## Troubleshooting

### Common Issues

1. **Environment Variables Not Loaded**
   - Ensure the `.env` file exists in the project root
   - Make sure the crontab command changes to the project directory before running the script

2. **Python Path Issues**
   - Use the full path to the Python executable (find it with `which python3`)
   - Ensure all required packages are installed in the Python environment

3. **Permission Issues**
   - Make sure the script is executable
   - Ensure the log directory exists and is writable

### Checking Logs

Logs are written to:
- Standard output/error: As specified in crontab (default: `/path/to/prismind/logs/reddit_collector.log`)
- Application logs: `/path/to/prismind/logs/reddit_collector_*.log`

## Next Steps

1. Monitor the logs to ensure the job is running as expected
2. Consider setting up log rotation for the log files
3. Add error notifications (e.g., email alerts) for failed runs
