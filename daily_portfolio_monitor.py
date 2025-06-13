#!/usr/bin/env python3
"""
Daily Portfolio Monitor - Streamlined Value Investing Analysis System

This script provides daily monitoring of your investment portfolio with:
- Automatic data fetching and analysis
- Change detection and alerts
- Buy-focused recommendations based on Buffett principles
- Risk management without selling
- Tax-efficient portfolio growth strategies

Usage:
    python daily_portfolio_monitor.py [--email recipient@example.com]
"""

import os
import sys
import json
import sqlite3
import argparse
import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import necessary modules
from src.core.logger import logger
from src.core.portfolio import get_stock_ticker_and_exchange
from src.core.portfolio_parser_english import parse_portfolio_csv_english
from src.tools.finnhub_api import fetch_company_data_finnhub as fetch_company_data
from src.models.claude.claude_analysis import analyze_with_claude
from src.models.clients import create_anthropic_client


@dataclass
class StockData:
    """Data structure for stock information"""
    ticker: str
    name: str
    shares: int
    current_price: float
    market_value: float
    weight: float
    previous_price: Optional[float] = None
    price_change_pct: Optional[float] = None
    intrinsic_value: Optional[float] = None
    margin_of_safety: Optional[float] = None
    recommendation: Optional[str] = None
    last_analysis_date: Optional[str] = None
    

@dataclass
class Alert:
    """Data structure for alerts"""
    type: str  # 'BUY', 'RISK', 'OPPORTUNITY', 'REVIEW'
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    ticker: str
    message: str
    action: str
    rationale: str


class PortfolioDatabase:
    """SQLite database for tracking portfolio history and analysis"""
    
    def __init__(self, db_path: str = "data/portfolio_history.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stock_history (
                    date TEXT,
                    ticker TEXT,
                    name TEXT,
                    shares INTEGER,
                    price REAL,
                    market_value REAL,
                    weight REAL,
                    intrinsic_value REAL,
                    margin_of_safety REAL,
                    recommendation TEXT,
                    PRIMARY KEY (date, ticker)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT,
                    type TEXT,
                    severity TEXT,
                    ticker TEXT,
                    message TEXT,
                    action TEXT,
                    rationale TEXT,
                    processed BOOLEAN DEFAULT FALSE
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_cache (
                    ticker TEXT PRIMARY KEY,
                    analysis_date TEXT,
                    analysis_content TEXT,
                    intrinsic_value REAL,
                    recommendation TEXT
                )
            """)
    
    def save_stock_data(self, date: str, stock: StockData):
        """Save stock data to history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO stock_history 
                (date, ticker, name, shares, price, market_value, weight, 
                 intrinsic_value, margin_of_safety, recommendation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date, stock.ticker, stock.name, stock.shares, 
                stock.current_price, stock.market_value, stock.weight,
                stock.intrinsic_value, stock.margin_of_safety, stock.recommendation
            ))
    
    def get_previous_data(self, ticker: str) -> Optional[Dict]:
        """Get most recent data for a stock"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM stock_history 
                WHERE ticker = ? 
                ORDER BY date DESC 
                LIMIT 1
            """, (ticker,))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
        return None
    
    def save_alert(self, alert: Alert):
        """Save alert to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alerts (date, type, severity, ticker, message, action, rationale)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.datetime.now().isoformat(),
                alert.type, alert.severity, alert.ticker,
                alert.message, alert.action, alert.rationale
            ))
    
    def get_cached_analysis(self, ticker: str, max_age_days: int = 7) -> Optional[Dict]:
        """Get cached analysis if recent enough"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM analysis_cache
                WHERE ticker = ? 
                AND julianday('now') - julianday(analysis_date) < ?
            """, (ticker, max_age_days))
            
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
        return None
    
    def save_analysis_cache(self, ticker: str, analysis_content: str, 
                          intrinsic_value: float, recommendation: str):
        """Save analysis to cache"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO analysis_cache 
                (ticker, analysis_date, analysis_content, intrinsic_value, recommendation)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ticker, datetime.datetime.now().isoformat(),
                analysis_content, intrinsic_value, recommendation
            ))


class ChangeDetector:
    """Detect significant changes in portfolio positions"""
    
    def __init__(self, db: PortfolioDatabase):
        self.db = db
        self.alerts = []
    
    def analyze_changes(self, current_stocks: List[StockData]) -> List[Alert]:
        """Analyze changes and generate alerts"""
        self.alerts = []
        
        for stock in current_stocks:
            previous = self.db.get_previous_data(stock.ticker)
            
            if previous:
                # Calculate price change
                price_change = (stock.current_price - previous['price']) / previous['price'] * 100
                stock.previous_price = previous['price']
                stock.price_change_pct = price_change
                
                # Check for significant price drops (potential buy opportunities)
                if price_change < -5:
                    self._add_buy_alert(stock, price_change)
                
                # Check for concentration risk
                if stock.weight > 15:
                    self._add_risk_alert(stock)
        
        return self.alerts
    
    def _add_buy_alert(self, stock: StockData, price_change: float):
        """Add buy opportunity alert"""
        alert = Alert(
            type='BUY',
            severity='HIGH' if price_change < -10 else 'MEDIUM',
            ticker=stock.ticker,
            message=f"{stock.name} down {abs(price_change):.1f}% - Potential buy opportunity",
            action=f"Consider adding to {stock.ticker} position",
            rationale=f"Quality company experiencing temporary price weakness. "
                     f"Current price ${stock.current_price:.2f} vs previous ${stock.previous_price:.2f}"
        )
        self.alerts.append(alert)
        self.db.save_alert(alert)
    
    def _add_risk_alert(self, stock: StockData):
        """Add concentration risk alert"""
        alert = Alert(
            type='RISK',
            severity='MEDIUM',
            ticker=stock.ticker,
            message=f"{stock.name} is {stock.weight:.1f}% of portfolio - Concentration risk",
            action="Consider diversifying by adding to other positions",
            rationale="Position size exceeds 15% threshold. Reduce risk through diversification"
        )
        self.alerts.append(alert)
        self.db.save_alert(alert)


class ValueInvestingAnalyzer:
    """Simplified value investing analysis using Claude"""
    
    def __init__(self, anthropic_client):
        self.client = anthropic_client
        self.db = PortfolioDatabase()
    
    def analyze_stock(self, stock: StockData, api_data: Dict, force_new: bool = False) -> Dict:
        """Analyze a single stock or use cached analysis"""
        
        # Check cache first unless forced
        if not force_new:
            cached = self.db.get_cached_analysis(stock.ticker)
            if cached:
                logger.info(f"Using cached analysis for {stock.ticker}")
                return {
                    'content': cached['analysis_content'],
                    'intrinsic_value': cached['intrinsic_value'],
                    'recommendation': cached['recommendation']
                }
        
        # Prepare focused prompt for daily monitoring
        prompt = self._create_analysis_prompt(stock, api_data)
        
        # Get analysis from Claude
        logger.info(f"Analyzing {stock.ticker} with Claude...")
        response = analyze_with_claude(prompt, self.client)
        
        # Parse response
        analysis = self._parse_analysis(response)
        
        # Cache the analysis
        self.db.save_analysis_cache(
            stock.ticker, 
            response,
            analysis.get('intrinsic_value', 0),
            analysis.get('recommendation', 'HOLD')
        )
        
        return analysis
    
    def _create_analysis_prompt(self, stock: StockData, api_data: Dict) -> str:
        """Create focused prompt for daily monitoring"""
        return f"""
You are a value investing expert conducting a daily portfolio review. Analyze {stock.name} ({stock.ticker}) 
for actionable insights based on Warren Buffett's principles.

Current Position:
- Shares: {stock.shares}
- Current Price: ${stock.current_price:.2f}
- Market Value: ${stock.market_value:,.2f}
- Portfolio Weight: {stock.weight:.1f}%
- Price Change: {stock.price_change_pct:.1f}% (if available)

Financial Data:
{json.dumps(api_data, indent=2)}

Provide a FOCUSED analysis answering:
1. Has anything fundamentally changed with this business?
2. What is the current intrinsic value per share?
3. Is there a buying opportunity at current prices?
4. Are there any risks to monitor?
5. Specific action: BUY MORE, HOLD, or REVIEW (never SELL unless fundamental deterioration)

Format your response with:
- INTRINSIC_VALUE: $XX.XX
- RECOMMENDATION: [BUY/HOLD/REVIEW]
- MARGIN_OF_SAFETY: XX%
- KEY_INSIGHT: One sentence summary
- ACTION_RATIONALE: Why take this action now
"""
    
    def _parse_analysis(self, response: str) -> Dict:
        """Parse Claude's response for key metrics"""
        analysis = {
            'content': response,
            'intrinsic_value': 0,
            'recommendation': 'HOLD',
            'margin_of_safety': 0
        }
        
        # Extract intrinsic value
        if 'INTRINSIC_VALUE:' in response:
            try:
                value_line = [line for line in response.split('\n') if 'INTRINSIC_VALUE:' in line][0]
                value_str = value_line.split('$')[1].split()[0].replace(',', '')
                analysis['intrinsic_value'] = float(value_str)
            except:
                pass
        
        # Extract recommendation
        if 'RECOMMENDATION:' in response:
            rec_line = [line for line in response.split('\n') if 'RECOMMENDATION:' in line][0]
            if 'BUY' in rec_line:
                analysis['recommendation'] = 'BUY'
            elif 'REVIEW' in rec_line:
                analysis['recommendation'] = 'REVIEW'
        
        return analysis


class DailyPortfolioMonitor:
    """Main class for daily portfolio monitoring"""
    
    def __init__(self):
        self.db = PortfolioDatabase()
        self.anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not self.anthropic_key:
            raise ValueError("Missing API token. Please set ANTHROPIC_API_KEY")
        
        self.anthropic_client = create_anthropic_client(self.anthropic_key)
        self.change_detector = ChangeDetector(self.db)
        self.analyzer = ValueInvestingAnalyzer(self.anthropic_client)
    
    def run_daily_analysis(self, portfolio_csv: str = "data/source/combined_portfolio.csv") -> Dict:
        """Run complete daily analysis"""
        logger.info("Starting daily portfolio analysis...")
        
        # 1. Parse current portfolio
        portfolio_data = parse_portfolio_csv_english(portfolio_csv)
        if not portfolio_data or not portfolio_data.get('stocks'):
            raise ValueError("No portfolio data found")
        
        current_stocks = []
        alerts = []
        recommendations = []
        
        # 2. Process each stock
        for i, stock_data in enumerate(portfolio_data['stocks']):
            try:
                stock = StockData(
                    ticker=stock_data.get('ticker', ''),
                    name=stock_data.get('name', ''),
                    shares=stock_data.get('shares', 0),
                    current_price=stock_data.get('price', 0),
                    market_value=stock_data.get('value', 0),
                    weight=stock_data.get('weight', 0)
                )
            except Exception as e:
                logger.error(f"Error creating StockData for index {i}: {e}")
                logger.error(f"Stock data: {stock_data}")
                continue
            
            # Get ticker mapping
            ticker_info = get_stock_ticker_and_exchange(stock.name)
            if not ticker_info:
                logger.warning(f"No ticker mapping for {stock.name}")
                continue
            
            stock.ticker = ticker_info['ticker']
            exchange = ticker_info['exchange']
            
            current_stocks.append(stock)
            
            # Fetch latest data
            logger.info(f"Fetching data for {stock.ticker}...")
            api_data = fetch_company_data(
                stock.ticker, 
                exchange
            )
            
            if not api_data:
                logger.warning(f"No API data for {stock.ticker}")
                continue
            
            # Analyze if significant change or weekly review
            should_analyze = self._should_analyze(stock)
            
            if should_analyze:
                analysis = self.analyzer.analyze_stock(stock, api_data)
                stock.intrinsic_value = analysis.get('intrinsic_value')
                stock.recommendation = analysis.get('recommendation')
                
                # Calculate margin of safety
                if stock.intrinsic_value > 0:
                    stock.margin_of_safety = ((stock.intrinsic_value - stock.current_price) 
                                            / stock.intrinsic_value * 100)
                
                # Generate recommendations
                if stock.recommendation == 'BUY' and stock.margin_of_safety > 20:
                    recommendations.append({
                        'ticker': stock.ticker,
                        'action': 'BUY',
                        'current_price': stock.current_price,
                        'intrinsic_value': stock.intrinsic_value or 0,
                        'margin_of_safety': stock.margin_of_safety or 0
                    })
            
            # Save to database
            self.db.save_stock_data(datetime.date.today().isoformat(), stock)
        
        # 3. Detect changes and generate alerts
        change_alerts = self.change_detector.analyze_changes(current_stocks)
        alerts.extend(change_alerts)
        
        # 4. Portfolio-level analysis
        portfolio_alerts = self._analyze_portfolio_health(current_stocks, portfolio_data)
        alerts.extend(portfolio_alerts)
        
        # 5. Generate report
        report = self._generate_daily_report(
            current_stocks, 
            alerts, 
            recommendations,
            portfolio_data
        )
        
        # 6. Save report
        report_path = f"data/daily_reports/report_{datetime.date.today().isoformat()}.md"
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Daily report saved to {report_path}")
        
        return {
            'stocks': current_stocks,
            'alerts': alerts,
            'recommendations': recommendations,
            'report_path': report_path
        }
    
    def _should_analyze(self, stock: StockData) -> bool:
        """Determine if stock needs analysis"""
        # Always analyze if significant price change
        if stock.price_change_pct and abs(stock.price_change_pct) > 5:
            return True
        
        # Weekly review for all positions
        cached = self.db.get_cached_analysis(stock.ticker, max_age_days=7)
        return cached is None
    
    def _analyze_portfolio_health(self, stocks: List[StockData], 
                                portfolio_data: Dict) -> List[Alert]:
        """Analyze overall portfolio health"""
        alerts = []
        
        # Check cash position
        cash_weight = portfolio_data.get('cash_percentage', 0)
        if cash_weight > 10:
            alert = Alert(
                type='OPPORTUNITY',
                severity='MEDIUM',
                ticker='CASH',
                message=f"Cash position is {cash_weight:.1f}% - Consider deploying capital",
                action="Look for quality companies trading below intrinsic value",
                rationale="Excess cash reduces long-term returns. Deploy into undervalued positions"
            )
            alerts.append(alert)
            self.db.save_alert(alert)
        
        # Check diversification
        max_weight = max(stock.weight for stock in stocks)
        if max_weight > 20:
            alert = Alert(
                type='RISK',
                severity='HIGH',
                ticker='PORTFOLIO',
                message=f"Largest position exceeds 20% - Concentration risk",
                action="Add to smaller positions to improve diversification",
                rationale="Buffett advocates concentration but 20%+ in one stock adds risk"
            )
            alerts.append(alert)
            self.db.save_alert(alert)
        
        return alerts
    
    def _generate_daily_report(self, stocks: List[StockData], alerts: List[Alert],
                             recommendations: List[Dict], portfolio_data: Dict) -> str:
        """Generate markdown report"""
        total_value = portfolio_data.get('total_value', 0) or 0
        cash_amount = portfolio_data.get('cash_amount', 0) or 0
        cash_percentage = portfolio_data.get('cash_percentage', 0) or 0
        
        report = f"""# Daily Portfolio Report - {datetime.date.today()}

## Portfolio Summary
- Total Value: ${total_value:,.2f}
- Number of Positions: {len(stocks)}
- Cash Available: ${cash_amount:,.2f} ({cash_percentage:.1f}%)

## 🚨 Alerts ({len(alerts)})
"""
        
        # Group alerts by severity
        high_alerts = [a for a in alerts if a.severity == 'HIGH']
        medium_alerts = [a for a in alerts if a.severity == 'MEDIUM']
        
        if high_alerts:
            report += "\n### High Priority\n"
            for alert in high_alerts:
                report += f"- **{alert.type}** [{alert.ticker}]: {alert.message}\n"
                report += f"  - Action: {alert.action}\n"
                report += f"  - Rationale: {alert.rationale}\n\n"
        
        if medium_alerts:
            report += "\n### Medium Priority\n"
            for alert in medium_alerts:
                report += f"- **{alert.type}** [{alert.ticker}]: {alert.message}\n"
                report += f"  - Action: {alert.action}\n\n"
        
        # Recommendations
        if recommendations:
            report += f"\n## 💡 Buy Recommendations\n"
            for rec in recommendations:
                report += f"\n### {rec['ticker']}\n"
                report += f"- Current Price: ${rec['current_price']:.2f}\n"
                report += f"- Intrinsic Value: ${rec.get('intrinsic_value', 0):.2f}\n"
                report += f"- Margin of Safety: {rec.get('margin_of_safety', 0):.1f}%\n"
        
        # Position Summary
        report += "\n## 📊 Position Summary\n"
        report += "| Stock | Shares | Price | Value | Weight | Change | Action |\n"
        report += "|-------|--------|-------|-------|--------|--------|--------|\n"
        
        for stock in sorted(stocks, key=lambda x: x.weight, reverse=True):
            change_str = f"{stock.price_change_pct:+.1f}%" if stock.price_change_pct else "N/A"
            action = stock.recommendation or "HOLD"
            report += f"| {stock.ticker} | {stock.shares} | ${stock.current_price:.2f} | "
            report += f"${stock.market_value:,.0f} | {stock.weight:.1f}% | {change_str} | {action} |\n"
        
        # Key Insights
        report += "\n## 🔍 Key Insights\n"
        report += "- Focus on adding to existing quality positions when they decline\n"
        report += "- Maintain long-term perspective - temporary price weakness creates opportunity\n"
        report += "- Deploy cash gradually into undervalued positions\n"
        report += "- Monitor concentration risk but don't sell winners\n"
        
        return report


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Daily Portfolio Monitor")
    parser.add_argument("--email", help="Email address for alerts")
    parser.add_argument("--force", action="store_true", help="Force new analysis for all positions")
    parser.add_argument("--dry-run", action="store_true", help="Run without making API calls")
    args = parser.parse_args()
    
    try:
        monitor = DailyPortfolioMonitor()
        results = monitor.run_daily_analysis()
        
        # Print summary
        print(f"\n✅ Daily analysis complete!")
        print(f"📊 Analyzed {len(results['stocks'])} positions")
        print(f"🚨 Generated {len(results['alerts'])} alerts")
        print(f"💡 Found {len(results['recommendations'])} buy opportunities")
        print(f"📄 Report saved to: {results['report_path']}")
        
        # Show high priority alerts
        high_alerts = [a for a in results['alerts'] if a.severity == 'HIGH']
        if high_alerts:
            print("\n⚠️  HIGH PRIORITY ALERTS:")
            for alert in high_alerts:
                print(f"   - {alert.message}")
        
        # Email if requested
        if args.email:
            # TODO: Implement email functionality
            print(f"\n📧 Email would be sent to: {args.email}")
            
    except Exception as e:
        logger.error(f"Error in daily monitoring: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()