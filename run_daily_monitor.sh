#!/bin/bash
#
# run_daily_monitor.sh - Execute daily portfolio monitoring
#
# This script can be added to cron for daily execution:
# 0 9 * * * /path/to/investment-master/run_daily_monitor.sh
#

# Set working directory
cd "$(dirname "$0")"

# Set Python path
export PYTHONPATH="$(pwd):$PYTHONPATH"

# Create necessary directories
mkdir -p data/daily_reports
mkdir -p logs

# Run the daily monitor
echo "Starting daily portfolio monitor at $(date)"
python daily_portfolio_monitor.py

# Check if successful
if [ $? -eq 0 ]; then
    echo "Daily monitoring completed successfully at $(date)"
    
    # Optional: Copy latest report to a fixed location for easy access
    LATEST_REPORT=$(ls -t data/daily_reports/report_*.md | head -1)
    if [ -n "$LATEST_REPORT" ]; then
        cp "$LATEST_REPORT" data/latest_daily_report.md
    fi
else
    echo "Daily monitoring failed at $(date)"
    exit 1
fi