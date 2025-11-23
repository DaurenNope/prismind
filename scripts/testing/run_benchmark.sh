#!/bin/bash
# Quick benchmark runner script
# Runs performance benchmarks for analysis pipeline

set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Performance Benchmark Runner${NC}"
echo "================================"
echo ""

# Default values
POSTS=${POSTS:-50}
CONCURRENT=${CONCURRENT:-5}

echo "Configuration:"
echo "  Posts: $POSTS"
echo "  Concurrent: $CONCURRENT"
echo ""

# Run benchmark
python scripts/testing/benchmark_analysis_performance.py \
    --posts "$POSTS" \
    --concurrent "$CONCURRENT"

echo ""
echo -e "${GREEN}✓ Benchmark complete${NC}"






