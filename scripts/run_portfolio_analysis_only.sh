#!/bin/bash

# run_portfolio_analysis_only.sh
#
# This script runs only the portfolio-level analysis using previously
# generated company analyses.
#
# Usage:
#   ./scripts/run_portfolio_analysis_only.sh [--model MODEL_NAME]
#
# Options:
#   --model MODEL_NAME       Specify the AI model to use (default: claude-3-7)

# Set PYTHONPATH to prioritize the current directory
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Default model
MODEL="claude-3-7"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --model)
      MODEL="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "=== Investment Master Portfolio Analysis ==="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

echo "Running portfolio analysis using model: $MODEL"
python src/scripts/claude_portfolio_optimizer.py --model "$MODEL"

if [ $? -ne 0 ]; then
    echo "Error: Portfolio analysis failed. Check logs for details."
    exit 1
fi

echo "Portfolio analysis completed successfully."
echo "Results are available at: data/processed/claude_portfolio_optimization.md"
echo "" 