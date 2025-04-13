#!/bin/bash

# fetch_data_only.sh
#
# This script only fetches fresh data for portfolio companies without running analysis
#
# Usage:
#   ./scripts/fetch_data_only.sh

# Set PYTHONPATH to prioritize the current directory
export PYTHONPATH="$(pwd):$PYTHONPATH"

echo "=== Investment Master Data Fetcher ==="
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Activated virtual environment"
fi

python src/scripts/fetch_portfolio_data.py

if [ $? -ne 0 ]; then
    echo "Error: Data fetching failed. Check logs for details."
    exit 1
fi

echo "Data fetching completed successfully."
echo "Results are available at: data/raw/api_data.json"
echo "" 