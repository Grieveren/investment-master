#!/usr/bin/env python3
"""
Simplified Daily Portfolio Monitor - Works without external dependencies
This version demonstrates the core functionality without requiring pip installs.
"""

import os
import json
import sqlite3
import datetime
from dataclasses import dataclass
from typing import Dict, List, Optional

# Simple logger
class SimpleLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

logger = SimpleLogger()

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

@dataclass  
class Alert:
    """Data structure for alerts"""
    type: str  # 'BUY', 'RISK', 'OPPORTUNITY', 'REVIEW'
    severity: str  # 'HIGH', 'MEDIUM', 'LOW'
    ticker: str
    message: str
    action: str

class PortfolioDatabase:
    """SQLite database for tracking portfolio history"""
    
    def __init__(self, db_path: str = "data/portfolio_history.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
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
                    action TEXT
                )
            """)
    
    def save_stock_data(self, date: str, stock: StockData):
        """Save stock data to history"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO stock_history 
                (date, ticker, name, shares, price, market_value, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                date, stock.ticker, stock.name, stock.shares, 
                stock.current_price, stock.market_value, stock.weight
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

def parse_portfolio_simple(csv_path: str) -> List[StockData]:
    """Simple CSV parser for portfolio data"""
    stocks = []
    
    if not os.path.exists(csv_path):
        logger.error(f"Portfolio file not found: {csv_path}")
        return stocks
    
    # Aggregate holdings by company
    holdings = {}
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Skip header
    for line in lines[1:]:
        if ',' in line:
            parts = line.strip().split(',')
            if len(parts) >= 6:
                try:
                    name = parts[0].strip().strip('"')
                    shares = int(parts[2]) if parts[2] else 0
                    price = float(parts[3]) if parts[3] else 0
                    value = float(parts[4]) if parts[4] else 0
                    weight_str = parts[5].replace('%', '').strip()
                    weight = float(weight_str) if weight_str else 0
                    
                    # Normalize company names and aggregate
                    key = None
                    if 'RHEINMETALL' in name.upper():
                        key = ('Rheinmetall', 'RHM')
                    elif 'BERKSH' in name.upper():
                        key = ('Berkshire Hathaway B', 'BRK.B')
                    elif 'ALLIANZ' in name.upper():
                        key = ('Allianz', 'ALV')
                    elif 'GITLAB' in name.upper():
                        key = ('GitLab', 'GTLB')
                    elif 'NVIDIA' in name.upper():
                        key = ('NVIDIA', 'NVDA')
                    elif 'MICROSOFT' in name.upper():
                        key = ('Microsoft', 'MSFT')
                    elif 'ALPHABET' in name.upper():
                        key = ('Alphabet C', 'GOOG')
                    elif 'CROWDSTRIKE' in name.upper():
                        key = ('CrowdStrike', 'CRWD')
                    elif 'ADVANCED MIC' in name.upper():
                        key = ('AMD', 'AMD')
                    elif 'NUTANIX' in name.upper():
                        key = ('Nutanix', 'NTNX')
                    elif 'ASML' in name.upper():
                        key = ('ASML', 'ASML')
                    elif 'TAIWAN' in name.upper():
                        key = ('Taiwan Semiconductor', 'TSM')
                    
                    if key and shares > 0:
                        if key not in holdings:
                            holdings[key] = {
                                'shares': 0,
                                'total_value': 0,
                                'price': price
                            }
                        holdings[key]['shares'] += shares
                        holdings[key]['total_value'] += value
                        
                except Exception as e:
                    logger.warning(f"Error parsing line: {e}")
    
    # Create stock objects from aggregated holdings
    total_value = sum(h['total_value'] for h in holdings.values())
    
    for (name, ticker), data in holdings.items():
        stock = StockData(
            ticker=ticker,
            name=name,
            shares=data['shares'],
            current_price=data['price'],
            market_value=data['total_value'],
            weight=(data['total_value'] / total_value * 100) if total_value > 0 else 0
        )
        stocks.append(stock)
    
    return stocks

def detect_changes(stocks: List[StockData], db: PortfolioDatabase) -> List[Alert]:
    """Detect significant changes and generate alerts"""
    alerts = []
    
    for stock in stocks:
        previous = db.get_previous_data(stock.ticker)
        
        if previous:
            # Calculate price change
            price_change = (stock.current_price - previous['price']) / previous['price'] * 100
            stock.previous_price = previous['price']
            stock.price_change_pct = price_change
            
            # Check for significant price drops (potential buy opportunities)
            if price_change < -5:
                alert = Alert(
                    type='BUY',
                    severity='HIGH' if price_change < -10 else 'MEDIUM',
                    ticker=stock.ticker,
                    message=f"{stock.name} down {abs(price_change):.1f}% - Potential buy opportunity",
                    action=f"Consider adding to {stock.ticker} position"
                )
                alerts.append(alert)
            
            # Check for concentration risk
            if stock.weight > 15:
                alert = Alert(
                    type='RISK',
                    severity='MEDIUM',
                    ticker=stock.ticker,
                    message=f"{stock.name} is {stock.weight:.1f}% of portfolio",
                    action="Consider diversifying"
                )
                alerts.append(alert)
    
    return alerts

def generate_report(stocks: List[StockData], alerts: List[Alert]) -> str:
    """Generate daily report"""
    report = f"""# Daily Portfolio Report - {datetime.date.today()}

## 🚨 Alerts ({len(alerts)})
"""
    
    for alert in alerts:
        report += f"- **{alert.type}** [{alert.ticker}]: {alert.message}\n"
        report += f"  - Action: {alert.action}\n\n"
    
    report += "\n## 📊 Position Summary\n"
    report += "| Stock | Shares | Price | Value | Weight | Change |\n"
    report += "|-------|--------|-------|-------|--------|--------|\n"
    
    for stock in sorted(stocks, key=lambda x: x.weight, reverse=True):
        change_str = f"{stock.price_change_pct:+.1f}%" if stock.price_change_pct else "New"
        report += f"| {stock.ticker} | {stock.shares} | ${stock.current_price:.2f} | "
        report += f"${stock.market_value:,.0f} | {stock.weight:.1f}% | {change_str} |\n"
    
    return report

def main():
    """Run simplified daily monitor"""
    print("🚀 Daily Portfolio Monitor (Simplified Version)")
    print("=" * 50)
    
    # Initialize database
    db = PortfolioDatabase()
    print("✅ Database initialized")
    
    # Parse portfolio
    csv_path = "data/source/combined_portfolio.csv"
    stocks = parse_portfolio_simple(csv_path)
    
    if not stocks:
        print("❌ No stocks found in portfolio")
        return
    
    print(f"✅ Found {len(stocks)} stocks in portfolio")
    
    # Detect changes and generate alerts
    alerts = detect_changes(stocks, db)
    print(f"📊 Generated {len(alerts)} alerts")
    
    # Save current data
    today = datetime.date.today().isoformat()
    for stock in stocks:
        db.save_stock_data(today, stock)
    
    # Generate report
    report = generate_report(stocks, alerts)
    
    # Save report
    report_dir = "data/daily_reports"
    os.makedirs(report_dir, exist_ok=True)
    report_path = f"{report_dir}/report_{today}.md"
    
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"✅ Report saved to: {report_path}")
    
    # Display alerts
    if alerts:
        print("\n⚠️  ALERTS:")
        for alert in alerts:
            print(f"   - {alert.message}")
    else:
        print("\n✅ No alerts today")

if __name__ == "__main__":
    main()