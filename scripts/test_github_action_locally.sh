#!/bin/bash

# This script simulates the GitHub Actions environment locally
# to test the Reddit collector script before pushing changes

set -e  # Exit on error

echo "🔍 Testing GitHub Actions workflow locally"
echo "================================="

# Set up environment variables
echo "🔧 Setting up environment variables..."
export REDDIT_CLIENT_ID="test_client_id"
export REDDIT_CLIENT_SECRET="test_client_secret"
export REDDIT_USER_AGENT="prismind/1.0"
export REDDIT_USERNAME="test_username"
export REDDIT_PASSWORD="test_password"

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

# Debug Python environment
echo "🔍 Python environment:"
python3 -c "import sys; print(sys.path)"

# Debug directory structure
echo "🔍 Current directory structure:"
find . -type d | sort

# Check for extraction directory and its contents
echo "🔍 Extraction directory contents:"
find . -type d -name "extraction" | xargs ls -la

# Check for working_reddit_extractor.py
echo "🔍 Looking for working_reddit_extractor.py:"
find . -name "working_reddit_extractor.py"

# Check __init__.py files
echo "🔍 Checking __init__.py files:"
find . -name "__init__.py" | xargs cat

# Create any missing __init__.py files
echo "🔍 Ensuring __init__.py files exist in all directories:"
mkdir -p src/core/extraction
touch src/__init__.py
touch src/core/__init__.py
touch src/core/extraction/__init__.py

# Copy WorkingRedditExtractor if needed
echo "🔍 Ensuring WorkingRedditExtractor is available:"
if [ -f "src/core/extraction/working_reddit_extractor.py" ]; then
  echo "✅ working_reddit_extractor.py exists"
else
  echo "⚠️ working_reddit_extractor.py not found, checking for alternative locations"
  find . -name "working_reddit_extractor.py" -exec cp {} src/core/extraction/ \;
  echo "✅ Copied working_reddit_extractor.py to src/core/extraction/"
fi

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