#!/bin/bash

# PrisMind Startup Script
echo "🎯 Starting PrisMind Intelligent Bookmark System..."

# Activate virtual environment
source venv/bin/activate

# Find available port
find_available_port() {
    for port in 8509 8510 8511 8512 8513; do
        if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo $port
            return 0
        fi
    done
    echo "8509"  # fallback
}

# Get available port
PORT=$(find_available_port)
echo "🚀 Launching dashboard at http://localhost:$PORT..."

# Start the dashboard
streamlit run app.py --server.port $PORT 