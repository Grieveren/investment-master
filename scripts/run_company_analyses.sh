#!/bin/bash

# run_company_analyses.sh
#
# This script runs company-level analyses using previously fetched API data
#
# Usage:
#   ./scripts/run_company_analyses.sh [--company COMPANY_NAME] [--model MODEL_NAME]
#
# Options:
#   --company COMPANY_NAME   Run analysis for a specific company only
#   --model MODEL_NAME       Specify the AI model to use (default: claude-3-7)

# Set PYTHONPATH to prioritize the current directory
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Default model
MODEL="claude-3-7"
COMPANY=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --company)
      COMPANY="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo "=== Investment Master Company Analyzer ==="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

# Check if analysis should be for a specific company or all
if [ -n "$COMPANY" ]; then
    echo "Running analysis for company: $COMPANY using model: $MODEL"
    python src/scripts/analyze_company.py --company "$COMPANY" --model "$MODEL"
else
    echo "Running analysis for all companies using model: $MODEL"
    python src/scripts/analyze_companies.py --model "$MODEL"
fi

if [ $? -ne 0 ]; then
    echo "Error: Company analysis failed. Check logs for details."
    exit 1
fi

echo "Company analysis completed successfully."
echo "Results are available in data/processed/ directory."
echo "" 