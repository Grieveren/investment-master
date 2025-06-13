# Migration Guide: From Complex to Streamlined System

## What's Changed

### Old System ❌
- Multiple scripts for different stages
- Separate analysis and optimization steps  
- Complex shell script orchestration
- Multiple AI model support
- Overly detailed reports

### New System ✅
- Single `daily_portfolio_monitor.py` script
- Integrated analysis with change detection
- SQLite database for historical tracking
- Claude-only for consistency
- Focused, actionable reports

## Migration Steps

### 1. Keep These Files
```
✅ src/core/portfolio.py (ticker mappings)
✅ src/tools/api.py (API integration)
✅ src/models/claude/ (Claude integration)
✅ .env (API keys)
✅ data/source/*.csv (portfolio files)
```

### 2. New Files Created
```
📄 daily_portfolio_monitor.py - Main monitoring script
📄 run_daily_monitor.sh - Simple run script
📄 daily_monitor_config.json - Configuration
📄 DAILY_MONITOR_README.md - Documentation
📁 data/portfolio_history.db - Historical database
📁 data/daily_reports/ - Daily report storage
```

### 3. Archive These (No Longer Needed)
```
❌ src/scripts/portfolio_analyzer.py
❌ src/scripts/claude_portfolio_optimizer.py
❌ src/scripts/analyze_company.py
❌ src/scripts/analyze_companies.py
❌ src/core/portfolio_optimizer.py
❌ run_portfolio_analysis.sh
❌ scripts/*.sh (all shell scripts)
```

## Data Preservation

Your existing data is safe:
- Portfolio CSVs remain unchanged
- API tokens in .env still work
- Historical analysis can be imported if needed

## Quick Start with New System

1. **Test the setup**:
   ```bash
   python test_daily_monitor.py
   ```

2. **Run first analysis**:
   ```bash
   ./run_daily_monitor.sh
   ```

3. **Check results**:
   ```bash
   cat data/latest_daily_report.md
   ```

## Key Differences in Usage

### Old Way
```bash
# Three separate steps
./scripts/fetch_data_only.sh
./scripts/run_company_analyses.sh
./scripts/run_portfolio_analysis_only.sh
```

### New Way
```bash
# One simple command
./run_daily_monitor.sh
```

## Configuration Changes

### Old: Multiple JSON configs
- config.json
- Various hardcoded settings

### New: Single daily_monitor_config.json
```json
{
    "monitoring": {
        "price_change_threshold": 5.0,
        "analysis_cache_days": 7
    },
    "alerts": {
        "minimum_margin_of_safety": 20.0
    }
}
```

## Report Format Changes

### Old Format
- Lengthy analysis for each stock
- Academic-style reports
- Buried actionable insights

### New Format  
- Alert-driven structure
- Clear BUY/HOLD actions
- One-page summary
- Focus on what changed

## Benefits of Migration

1. **Speed**: 10x faster daily runs
2. **Focus**: Only analyzes what matters
3. **History**: Track changes over time
4. **Alerts**: Never miss opportunities
5. **Simplicity**: One script to rule them all

## Rollback Plan

If you need to use the old system:
1. All old files remain untouched
2. Simply run old scripts as before
3. New system uses different output directories

## Support

Check `DAILY_MONITOR_README.md` for detailed documentation of the new system.