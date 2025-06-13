#!/bin/bash

# run_portfolio_analysis.sh
# 
# This script runs the complete portfolio analysis and optimization process,
# using Claude for both analysis and holistic portfolio optimization.
#
# Usage:
#   ./run_portfolio_analysis.sh [--skip-analysis]
#
# Options:
#   --skip-analysis  Skip the initial analysis and only run the optimization

# Set PYTHONPATH to prioritize the current directory
export PYTHONPATH="$(pwd):$PYTHONPATH"

echo "=== Investment Master Portfolio Analysis & Optimization ==="
echo ""

# Check if we should skip the analysis
if [[ "$1" != "--skip-analysis" ]]; then
    echo "Step 1: Running portfolio analysis with Claude..."
    python src/scripts/portfolio_analyzer.py --model claude-3-7
    
    if [ $? -ne 0 ]; then
        echo "Error: Portfolio analysis failed. Check logs for details."
        exit 1
    fi
    
    echo "Portfolio analysis completed successfully."
else
    echo "Skipping initial analysis as requested with --skip-analysis"
fi

echo ""
echo "Step 2: Running Claude holistic portfolio optimization..."
python src/scripts/claude_portfolio_optimizer.py

if [ $? -ne 0 ]; then
    echo "Error: Claude portfolio optimization failed. Check logs for details."
    exit 1
fi

echo "Claude portfolio optimization completed successfully."
echo ""

# Show the output locations
echo "=== Analysis & Optimization Complete ==="
echo ""
echo "Results are available at:"
echo "- Portfolio Analysis: data/processed/portfolio_analysis_claude.md"
echo "- Claude Holistic Optimization: data/processed/claude_portfolio_optimization.md"
echo ""
echo "Thank you for using Investment Master!" 