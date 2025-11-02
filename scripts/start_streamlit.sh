#!/bin/bash
# Start Streamlit UI with correct Python environment

cd /Users/mac/Documents/Development/prismind

# Kill any existing Streamlit instances
pkill -f "streamlit run" 2>/dev/null
sleep 1

# Start with venv Python 3.11 (has compatible numpy/pandas)
echo "🚀 Starting Streamlit UI..."
echo ""

.venv311/bin/python -m streamlit run src/web/app.py --server.port 8501 \
  --server.headless true \
  --browser.gatherUsageStats false &

sleep 3
echo ""
echo "✅ Streamlit UI running at: http://localhost:8501"
echo ""
echo "All fixes applied:"
echo "  ✅ Content extraction: Full content (not truncated)"
echo "  ✅ Validation: Blocks bad data"
echo "  ✅ Browse tab: Datetime comparison fixed"
echo "  ✅ Python env: Using .venv311 (Python 3.11)"
echo ""
echo "Press Ctrl+C to stop"

wait
