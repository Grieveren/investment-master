# Daily Portfolio Monitor - Streamlined Value Investing System

A focused, efficient daily monitoring system for your investment portfolio based on Warren Buffett's value investing principles.

## 🚀 Quick Start

1. **Setup** (one time only):
   ```bash
   # Install dependencies
   pip install -e .
   
   # Set your API keys in .env file
   echo "SWS_API_TOKEN=your_token" >> .env
   echo "ANTHROPIC_API_KEY=your_key" >> .env
   ```

2. **Run Daily Monitor**:
   ```bash
   ./run_daily_monitor.sh
   ```

3. **Set up Daily Automation** (optional):
   ```bash
   # Add to crontab for 9 AM daily execution
   crontab -e
   # Add this line:
   0 9 * * * /path/to/investment-master/run_daily_monitor.sh
   ```

## 📊 What It Does

### Daily Analysis
- Fetches latest market data for all positions
- Compares with historical data to detect changes
- Runs AI analysis on positions with significant changes
- Generates actionable alerts and recommendations

### Alert Types
1. **🟢 BUY Alerts**: Quality stocks at attractive prices
2. **🔴 RISK Alerts**: Concentration or portfolio risks
3. **🟡 OPPORTUNITY Alerts**: New positions to consider
4. **🔍 REVIEW Alerts**: Positions needing attention

### Key Features
- **Change Detection**: Analyzes only what's changed (efficient)
- **Smart Caching**: Weekly full review, daily change monitoring
- **Buy-Focused**: Never suggests selling, only buying opportunities
- **Tax-Efficient**: Avoids taxable events, focuses on new capital deployment
- **Historical Tracking**: SQLite database tracks all changes over time

## 📈 Output

Daily reports are saved to `data/daily_reports/` with:
- Portfolio summary and performance
- High-priority alerts requiring action
- Buy recommendations with margin of safety
- Position-level insights
- Risk analysis and diversification metrics

Latest report is always available at: `data/latest_daily_report.md`

## 🎯 Investment Philosophy

Based on Buffett's principles:
1. **Buy Quality**: Focus on companies with durable competitive advantages
2. **Price Discipline**: Only buy with adequate margin of safety (20%+)
3. **Hold Forever**: No sell recommendations unless fundamental deterioration
4. **Concentration**: OK to have large positions in best ideas (up to 20%)
5. **Patience**: Deploy cash gradually into opportunities

## 🔧 Configuration

Edit `daily_monitor_config.json` to customize:
- Price change thresholds for alerts
- Position concentration limits
- Analysis caching duration
- Email notification settings

## 📧 Email Alerts (Coming Soon)

To enable email notifications:
```bash
python daily_portfolio_monitor.py --email your@email.com
```

## 🗄️ Database Schema

The system maintains a SQLite database (`data/portfolio_history.db`) with:
- **stock_history**: Daily snapshots of all positions
- **alerts**: All generated alerts with timestamps
- **analysis_cache**: AI analysis results for efficiency

## 🏃 Performance

- Initial run: ~2-3 minutes (analyzes all positions)
- Daily runs: ~30 seconds (only analyzes changes)
- Database grows ~1MB per month of daily monitoring

## 🐛 Troubleshooting

1. **No API data**: Check your SWS_API_TOKEN in .env
2. **Analysis fails**: Verify ANTHROPIC_API_KEY is set
3. **Database locked**: Ensure only one instance runs at a time
4. **Missing positions**: Update ticker mappings in `src/core/portfolio.py`

## 💡 Tips

1. Run at market open for fresh data
2. Review high-priority alerts immediately
3. Keep some cash ready for opportunities
4. Don't override the system - trust the process
5. Review weekly summaries for trends

## 🚧 Future Enhancements

- [ ] Email/SMS notifications for high alerts
- [ ] Web dashboard for historical analysis
- [ ] Integration with broker APIs for execution
- [ ] Multi-portfolio support
- [ ] Custom screening for new positions