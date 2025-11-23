#!/bin/bash
# Start FastAPI Backend

# Get the absolute path of the script directory, then go up two levels to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_ROOT"

# Activate virtual environment if it exists
PYTHON_CMD="python"
if [ -d ".venv311" ]; then
    source .venv311/bin/activate
    PYTHON_CMD=".venv311/bin/python"
elif [ -d "venv" ]; then
    source venv/bin/activate
    PYTHON_CMD="venv/bin/python"
fi

echo "🚀 Starting FastAPI Backend..."
echo "📡 API will be available at: http://localhost:8000"
echo "📚 API docs at: http://localhost:8000/docs"
echo ""

$PYTHON_CMD src/api/main.py
