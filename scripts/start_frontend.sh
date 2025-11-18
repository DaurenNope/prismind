#!/bin/bash
# Start Svelte Frontend

cd "$(dirname "$0")/../frontend"

echo "🚀 Starting Svelte Frontend..."
echo "🌐 UI will be available at: http://localhost:5173"
echo ""

npm run dev
