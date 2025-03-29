"""
Test script for verifying YFinanceConnector functionality in the BacktestEngine.

This is a simplified test focusing only on the data retrieval and caching functionality
of the YFinanceConnector within the BacktestEngine context.
"""

import os
import sys
import logging
import datetime
import pandas as pd
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backtesting.core.engine import BacktestEngine
from src.backtesting.data.yfinance_connector import YFinanceConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_connector_in_engine():
    """Test the YFinanceConnector functionality within the BacktestEngine."""
    logger.info("Starting test of YFinanceConnector in BacktestEngine")
    
    # Use a very limited time range and minimal tickers for quick testing
    end_date = datetime.datetime.now().date()
    start_date = end_date - datetime.timedelta(days=14)  # Just 2 weeks of data
    
    # Create the engine with default YFinanceConnector
    engine = BacktestEngine(
        start_date=start_date,
        end_date=end_date,
        initial_capital=100000.0,
        benchmark='SPY'
    )
    
    # Test loading price data for a small set of tickers
    test_tickers = ['AAPL', 'MSFT']
    logger.info(f"Testing data loading for tickers: {test_tickers}")
    
    success = engine.load_price_data(test_tickers)
    
    if success:
        logger.info("Successfully loaded price data")
        
        # Display what was loaded
        for ticker, data in engine.price_data.items():
            logger.info(f"{ticker}: Loaded {len(data)} data points")
            logger.info(f"{ticker} sample data:\n{data.head(1)}")
        
        # Display benchmark data
        if engine.benchmark_data is not None and not engine.benchmark_data.empty:
            logger.info(f"Benchmark ({engine.benchmark}): Loaded {len(engine.benchmark_data)} data points")
            logger.info(f"Benchmark sample data:\n{engine.benchmark_data.head(1)}")
        else:
            logger.error(f"Failed to load benchmark data for {engine.benchmark}")
            
        # Set initial portfolio with equal weights
        portfolio = {ticker: 1.0 / len(test_tickers) for ticker in test_tickers}
        engine.set_initial_portfolio(portfolio)
        
        # Verify the portfolio was set correctly
        logger.info(f"Portfolio initialized with {len(engine.portfolio.positions)} positions")
        for position in engine.portfolio.positions:
            logger.info(f"Position: {position.ticker}, Shares: {position.shares}, Value: {position.shares * position.entry_price}")
        
        return True
    else:
        logger.error("Failed to load price data")
        return False

if __name__ == "__main__":
    success = test_connector_in_engine()
    if success:
        logger.info("Test completed successfully")
        sys.exit(0)
    else:
        logger.error("Test failed")
        sys.exit(1) 