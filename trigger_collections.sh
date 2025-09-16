#!/bin/bash

# Script to trigger both Twitter and Reddit collections

echo "🚀 Triggering Twitter and Reddit collections..."

# Change to the project directory
cd "$(dirname "$0")"

# Run the Python script
python3 scripts/trigger_collections.py

echo "✅ Collection process complete!"