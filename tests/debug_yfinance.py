"""
Debug script for testing yfinance data retrieval with improved rate limiting and caching.

This script tests the enhanced YFinanceConnector with real data retrieval,
focusing on optimal caching and rate limiting to handle Yahoo Finance API restrictions.
"""

import os
import sys
import logging
import datetime
import pandas as pd
import time
import argparse
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.backtesting.data.yfinance_connector import YFinanceConnector
import yfinance as yf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug_yfinance.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_directories():
    """Set up cache directories"""
    cache_dir = Path('data/cache')
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Setup completed. Cache directory: {cache_dir}")
    return cache_dir

def test_direct_yfinance():
    """Test direct yfinance functionality without our connector"""
    logger.info("----- Testing direct yfinance functionality -----")
    
    # Test Ticker.history() method
    logger.info("Testing Ticker.history() method for AAPL")
    try:
        ticker = yf.Ticker("AAPL")
        data = ticker.history(period="5d")
        logger.info(f"Successfully retrieved {len(data)} rows with Ticker.history()")
        logger.info(f"Sample data:\n{data.head(2)}")
    except Exception as e:
        logger.error(f"Error with Ticker.history(): {e}")
    
    # Test yf.download() method
    logger.info("Testing yf.download() method for MSFT")
    try:
        data = yf.download("MSFT", period="5d", progress=False)
        logger.info(f"Successfully retrieved {len(data)} rows with yf.download()")
        logger.info(f"Sample data:\n{data.head(2)}")
    except Exception as e:
        logger.error(f"Error with yf.download(): {e}")
    
    # Print yfinance version
    logger.info(f"Using yfinance version: {yf.__version__}")

def test_enhanced_connector(test_tickers=None):
    """Test the enhanced YFinanceConnector with real data"""
    logger.info("----- Testing enhanced YFinanceConnector -----")
    
    # Define test parameters
    if test_tickers is None:
        test_tickers = ['AAPL', 'MSFT', 'GOOGL']  # Use only 3 tickers for testing
    
    # Time range - use recent dates to ensure data availability
    end_date = datetime.datetime.now().date()
    start_date = end_date - datetime.timedelta(days=30)  # 30 days of data
    
    logger.info(f"Test parameters:")
    logger.info(f"  - Tickers: {test_tickers}")
    logger.info(f"  - Start date: {start_date}")
    logger.info(f"  - End date: {end_date}")
    
    # Create connector with conservative rate limiting
    connector = YFinanceConnector(
        use_cache=True,
        cache_dir='data/cache',
        cache_expire_days=30,
        max_retries=5,
        rate_limit=0.1,  # Very conservative: 1 request per 10 seconds
        batch_size=1     # Process one ticker at a time
    )
    
    # Time the operation
    start_time = time.time()
    
    # Retrieve benchmark data (S&P 500)
    logger.info("Retrieving benchmark data (SPY)...")
    benchmark_data = connector.get_benchmark_data('SPY', start_date, end_date)
    
    if benchmark_data is not None and not benchmark_data.empty:
        logger.info(f"Successfully retrieved benchmark data ({len(benchmark_data)} rows)")
        logger.info(f"Sample benchmark data:\n{benchmark_data.head(2)}")
    else:
        logger.error("Failed to retrieve benchmark data")
    
    # Retrieve historical prices for test tickers
    logger.info(f"Retrieving historical prices for {len(test_tickers)} tickers...")
    historical_prices = connector.get_historical_prices(test_tickers, start_date, end_date)
    
    # Calculate the elapsed time
    elapsed_time = time.time() - start_time
    logger.info(f"Data retrieval completed in {elapsed_time:.2f} seconds")
    
    # Report results
    successful_tickers = list(historical_prices.keys())
    logger.info(f"Successfully retrieved data for {len(successful_tickers)}/{len(test_tickers)} tickers")
    
    for ticker in successful_tickers:
        data = historical_prices[ticker]
        logger.info(f"{ticker}: Retrieved {len(data)} rows of data")
        if not data.empty:
            logger.info(f"{ticker} sample data:\n{data.head(2)}")
    
    failed_tickers = [t for t in test_tickers if t not in successful_tickers]
    if failed_tickers:
        logger.warning(f"Failed to retrieve data for {len(failed_tickers)} tickers: {failed_tickers}")
    
    # Test retrieving data again (from cache)
    if successful_tickers:
        logger.info("----- Testing cache retrieval -----")
        cache_start_time = time.time()
        
        # Try to retrieve the same data again (should come from cache)
        cache_test_ticker = successful_tickers[0]
        logger.info(f"Retrieving cached data for {cache_test_ticker}...")
        cached_data = connector.get_historical_prices([cache_test_ticker], start_date, end_date)
        
        cache_elapsed_time = time.time() - cache_start_time
        logger.info(f"Cache retrieval completed in {cache_elapsed_time:.2f} seconds")
        
        if cache_test_ticker in cached_data and not cached_data[cache_test_ticker].empty:
            logger.info(f"Successfully retrieved cached data for {cache_test_ticker} ({len(cached_data[cache_test_ticker])} rows)")
            speedup = elapsed_time / cache_elapsed_time if cache_elapsed_time > 0 else float('inf')
            logger.info(f"Cache speedup: {speedup:.2f}x")
        else:
            logger.error(f"Failed to retrieve cached data for {cache_test_ticker}")

def main():
    """Main function to run the debug tests"""
    parser = argparse.ArgumentParser(description='Debug yfinance data retrieval')
    parser.add_argument('--tickers', type=str, nargs='+', help='List of tickers to test')
    args = parser.parse_args()
    
    logger.info("Starting yfinance debug tests")
    
    # Setup directories
    setup_directories()
    
    # Test direct yfinance functionality
    test_direct_yfinance()
    
    # Test enhanced connector
    test_enhanced_connector(args.tickers)
    
    logger.info("Debug tests completed")

if __name__ == "__main__":
    main() 