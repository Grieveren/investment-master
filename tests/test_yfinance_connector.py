"""
Test script to demonstrate the improved YFinanceConnector with rate limiting and caching.
"""

import logging
import datetime
import os
import argparse
import numpy as np
import pandas as pd
from src.backtesting.data.yfinance_connector import YFinanceConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_yfinance_connector')

def create_mock_price_data(ticker, start_date, end_date, interval='1d'):
    """Create mock price data for testing."""
    # Create a date range
    if interval == '1d':
        date_range = pd.date_range(start=start_date, end=end_date, freq='B')  # Business days
    elif interval == '1wk':
        date_range = pd.date_range(start=start_date, end=end_date, freq='W')  # Weekly
    else:  # '1mo'
        date_range = pd.date_range(start=start_date, end=end_date, freq='MS')  # Monthly start
    
    # Set seed based on ticker name for reproducible but different data per ticker
    seed = sum(ord(c) for c in ticker)
    np.random.seed(seed)
    
    # Generate base price (different starting point for each ticker)
    base_price = 100 + (seed % 400)  # Base price between 100 and 500
    
    # Generate random price movements with a slight upward trend
    num_points = len(date_range)
    daily_returns = np.random.normal(0.0005, 0.01, num_points)  # Small positive drift
    
    # Cumulative returns
    cumulative_returns = np.cumprod(1 + daily_returns)
    prices = base_price * cumulative_returns
    
    # Create the DataFrame with OHLCV data
    data = pd.DataFrame({
        'Open': prices * (1 - np.random.uniform(0, 0.005, num_points)),
        'High': prices * (1 + np.random.uniform(0, 0.01, num_points)),
        'Low': prices * (1 - np.random.uniform(0, 0.01, num_points)),
        'Close': prices,
        'Volume': np.random.randint(100000, 10000000, num_points)
    }, index=date_range)
    
    return data

def test_connector(use_mock=False):
    """Test the YFinanceConnector with various tickers."""
    # Create cache directory if it doesn't exist
    cache_dir = 'data/yfinance_cache'
    os.makedirs(cache_dir, exist_ok=True)
    
    # Initialize connector with enhanced rate limiting and caching
    connector = YFinanceConnector(
        use_cache=True,
        cache_dir=cache_dir,
        cache_expire_days=7,
        max_retries=3,  # Reduced retries for faster testing
        rate_limit=0.25,  # 1 request every 4 seconds to be very conservative
        batch_size=1     # Single ticker at a time to minimize issues
    )
    
    # Test date range (last 14 days - shorter period for quicker tests)
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=14)
    
    logger.info(f"Testing date range: {start_date} to {end_date}")
    
    # Test with a small set of tickers (reduced for testing)
    test_tickers = ['AAPL', 'MSFT', 'GOOGL']
    benchmark = 'SPY'  # S&P 500 ETF
    
    logger.info(f"Fetching data for {len(test_tickers)} tickers: {', '.join(test_tickers)}")
    
    # If mock mode is enabled, use mock data instead of real API calls
    if use_mock:
        logger.info("Using mock data instead of real API calls")
        
        # Create mock benchmark data
        mock_benchmark_data = create_mock_price_data(benchmark, start_date, end_date)
        logger.info(f"Created mock benchmark data with {len(mock_benchmark_data)} data points")
        logger.info(f"Sample benchmark data:\n{mock_benchmark_data.head(3)}")
        
        # Create mock price data for test tickers
        mock_price_data = {}
        for ticker in test_tickers:
            mock_data = create_mock_price_data(ticker, start_date, end_date)
            mock_price_data[ticker] = mock_data
            logger.info(f"Created mock data for {ticker} with {len(mock_data)} data points")
            logger.info(f"Sample data for {ticker}:\n{mock_data.head(3)}")
        
        logger.info(f"Successfully created mock data for {len(mock_price_data)}/{len(test_tickers)} tickers")
        return True
    
    # First, try to fetch benchmark data
    logger.info(f"Fetching benchmark data for {benchmark}")
    benchmark_data = connector.get_benchmark_data(benchmark, start_date, end_date)
    
    if not benchmark_data.empty:
        logger.info(f"Successfully retrieved {len(benchmark_data)} data points for benchmark {benchmark}")
        logger.info(f"Sample benchmark data:\n{benchmark_data.head(3)}")
    else:
        logger.warning(f"Failed to retrieve benchmark data for {benchmark}")
    
    # Fetch historical prices for test tickers
    price_data = connector.get_historical_prices(test_tickers, start_date, end_date)
    
    # Check results
    success_count = 0
    for ticker, data in price_data.items():
        if not data.empty:
            success_count += 1
            logger.info(f"Successfully retrieved {len(data)} data points for {ticker}")
            logger.info(f"Sample data for {ticker}:\n{data.head(3)}")
        else:
            logger.warning(f"Failed to retrieve data for {ticker}")
    
    logger.info(f"Successfully retrieved data for {success_count}/{len(test_tickers)} tickers")
    
    # Test retrieving data for the same tickers again to test caching
    if success_count > 0:
        logger.info("Testing cache by retrieving the same data again...")
        
        # Get just one ticker from the successful ones to test cache
        cached_ticker = next(iter([t for t, d in price_data.items() if not d.empty]), None)
        if cached_ticker:
            logger.info(f"Testing cache with ticker {cached_ticker}")
            start_time = datetime.datetime.now()
            cached_data = connector.get_historical_prices([cached_ticker], start_date, end_date)
            end_time = datetime.datetime.now()
            
            if not cached_data.get(cached_ticker, pd.DataFrame()).empty:
                logger.info(f"Cache test successful for {cached_ticker}")
                logger.info(f"Cache retrieval took {(end_time - start_time).total_seconds():.2f} seconds")
                logger.info("Cache is working properly - retrieval was much faster")
            else:
                logger.warning(f"Cache test failed for {cached_ticker}")
    
    return success_count == len(test_tickers)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test the YFinanceConnector with improved rate limiting')
    parser.add_argument('--mock', action='store_true', help='Use mock data instead of real API calls')
    args = parser.parse_args()
    
    result = test_connector(use_mock=args.mock)
    
    if result:
        logger.info("YFinanceConnector test completed successfully!")
        exit(0)
    else:
        logger.error("YFinanceConnector test failed to retrieve all ticker data")
        exit(1) 