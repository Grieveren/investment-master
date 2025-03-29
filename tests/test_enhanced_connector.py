"""
Test script to demonstrate the enhanced YFinanceConnector with advanced rate limiting and caching.
"""

import logging
import datetime
import os
import argparse
import time
import pandas as pd
from src.backtesting.data.yfinance_connector import YFinanceConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_enhanced_connector')

def test_enhanced_connector(use_mock_data=False):
    """Test the enhanced YFinanceConnector with various tickers."""
    # Create cache directory if it doesn't exist
    cache_dir = 'data/yfinance_cache'
    mock_data_dir = 'data/mock_data'
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(mock_data_dir, exist_ok=True)
    
    # Initialize connector with enhanced settings
    connector = YFinanceConnector(
        use_cache=True,
        cache_dir=cache_dir,
        cache_expire_days=30,
        max_retries=3,
        rate_limit=0.2,  # 1 request every 5 seconds to be very conservative
        batch_size=1,    # One ticker at a time for better control
        use_mock_data=use_mock_data,
        mock_data_dir=mock_data_dir
    )
    
    # Test date range (last 7 days - shorter period for quicker tests)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=7)
    
    logger.info(f"Testing date range: {start_date} to {end_date}")
    logger.info(f"Using {'mock' if use_mock_data else 'real'} data")
    
    # Test with a small set of tickers
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    benchmark = 'SPY'  # S&P 500 ETF
    
    logger.info(f"Fetching data for {len(test_tickers)} tickers: {', '.join(test_tickers)}")
    
    # First, try to fetch benchmark data
    logger.info(f"Fetching benchmark data for {benchmark}")
    start_time = time.time()
    benchmark_data = connector.get_benchmark_data(benchmark, start_date, end_date)
    benchmark_time = time.time() - start_time
    
    if not benchmark_data.empty:
        logger.info(f"Successfully retrieved {len(benchmark_data)} data points for benchmark {benchmark} in {benchmark_time:.2f} seconds")
        logger.info(f"Sample benchmark data:\n{benchmark_data.head(3)}")
    else:
        logger.warning(f"Failed to retrieve benchmark data for {benchmark}")
    
    # Fetch historical prices for test tickers
    logger.info("Fetching historical prices for test tickers")
    start_time = time.time()
    price_data = connector.get_historical_prices(test_tickers, start_date, end_date)
    fetch_time = time.time() - start_time
    
    # Check results
    success_count = 0
    for ticker, data in price_data.items():
        if not data.empty:
            success_count += 1
            logger.info(f"Successfully retrieved {len(data)} data points for {ticker}")
            logger.info(f"Sample data for {ticker}:\n{data.head(3)}")
        else:
            logger.warning(f"Failed to retrieve data for {ticker}")
    
    logger.info(f"Successfully retrieved data for {success_count}/{len(test_tickers)} tickers in {fetch_time:.2f} seconds")
    
    # Test retrieving data for the same tickers again to test caching
    if success_count > 0:
        logger.info("Testing cache by retrieving the same data again...")
        
        start_time = time.time()
        cached_price_data = connector.get_historical_prices(test_tickers, start_date, end_date)
        cache_time = time.time() - start_time
        
        cached_success_count = 0
        for ticker, data in cached_price_data.items():
            if not data.empty:
                cached_success_count += 1
        
        logger.info(f"Cache test: Retrieved data for {cached_success_count}/{len(test_tickers)} tickers in {cache_time:.2f} seconds")
        if cache_time > 0:
            logger.info(f"Cache speedup: {fetch_time/cache_time:.2f}x faster")
    
    return success_count == len(test_tickers)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test the enhanced YFinanceConnector with advanced rate limiting')
    parser.add_argument('--mock', action='store_true', help='Use mock data instead of real API calls')
    args = parser.parse_args()
    
    logger.info("Starting enhanced connector test")
    
    result = test_enhanced_connector(use_mock_data=args.mock)
    
    if result:
        logger.info("Enhanced YFinanceConnector test completed successfully!")
        exit(0)
    else:
        logger.error("Enhanced YFinanceConnector test failed to retrieve all ticker data")
        exit(1) 