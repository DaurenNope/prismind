#!/bin/bash
# Start FastAPI Backend

cd "$(dirname "$0")/.."

echo "🚀 Starting FastAPI Backend..."
echo "📡 API will be available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo ""

python3 src/api/main.py
