#!/bin/bash

# Setup Reddit Collector Cron Job
# This script sets up a cron job to run the Reddit collector every 6 hours

# Get the path to the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_PATH="$(which python3)"
SCRIPT_PATH="$PROJECT_ROOT/scripts/scheduled_reddit_collector.py"
LOG_DIR="$PROJECT_ROOT/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Create a temporary crontab entry
CRON_ENTRY="0 */6 * * * cd $PROJECT_ROOT && $PYTHON_PATH $SCRIPT_PATH --limit 50 >> $LOG_DIR/cron.log 2>&1"

# Add to crontab
(crontab -l 2>/dev/null | grep -v "$SCRIPT_PATH"; echo "$CRON_ENTRY") | crontab -

echo "Cron job has been set up to run every 6 hours"
echo "Python path: $PYTHON_PATH"
echo "Script path: $SCRIPT_PATH"
echo "Logs will be written to: $LOG_DIR"
echo ""
echo "Current crontab:"
crontab -l
