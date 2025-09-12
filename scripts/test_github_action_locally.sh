#!/bin/bash

# This script simulates the GitHub Actions environment locally
# to test the Reddit collector script before pushing changes

echo "🔍 Testing GitHub Actions workflow locally"
echo "=========================================="

# Set up environment variables (replace with your actual values or use .env file)
if [ -f ".env" ]; then
  echo "📝 Loading environment variables from .env file"
  export $(grep -v '^#' .env | xargs)
else
  echo "⚠️ No .env file found. Make sure to set required environment variables manually."
fi

# Create required directories
mkdir -p data logs

# Print environment variables for debugging (without sensitive data)
echo "🔍 Environment Variables:"
env | grep -v 'PASSWORD\|SECRET\|TOKEN' | sort

# Print current directory and files
echo "🔍 Current Directory:"
pwd
ls -la

# Create an empty output file to ensure it exists
touch collection_output.txt

# Run the collector with debugging
echo "🔍 Running Reddit Collector with debugging..."

# Check Python version
echo "🔍 Python version:"
python3 --version

# Check directory structure
echo "🔍 Current directory structure:"
find . -type d -name "extraction" | xargs ls -la

# Check __init__.py files
echo "🔍 Checking __init__.py files:"
find . -name "__init__.py" | xargs cat

# Run the script with PYTHONPATH set
echo "🔍 Running with PYTHONPATH set:"
PYTHONPATH=$(pwd) python3 scripts/test_reddit_collector.py

# Check exit code
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
  echo "✅ Test completed successfully with exit code 0"
else
  echo "❌ Test failed with exit code $EXIT_CODE"
fi

echo "🔍 Test completed"