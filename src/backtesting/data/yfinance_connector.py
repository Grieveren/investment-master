"""
YFinance data connector for retrieving historical price data with advanced rate limiting and caching.
"""

import logging
import pandas as pd
import datetime
import time
import random
import os
import pickle
import threading
from typing import Dict, List, Optional, Union

# Import the required libraries for handling rate limiting and caching
try:
    import requests_cache
    from requests_ratelimiter import LimiterSession, RequestRate, Duration, Limiter
    RATE_LIMITER_AVAILABLE = True
except ImportError:
    RATE_LIMITER_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)

# List of User-Agents to rotate through to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 OPR/107.0.0.0",
]

class YFinanceConnector:
    """Connector for retrieving historical price data from Yahoo Finance with advanced rate limiting."""
    
    # Class-level lock for thread safety when accessing the cache
    _cache_lock = threading.Lock()
    
    def __init__(
        self, 
        use_cache=True, 
        cache_dir='data/cache',
        cache_expire_days=30,  # 30 days to reduce API calls
        max_retries=5, 
        rate_limit=0.2,  # 1 request every 5 seconds to be very conservative
        batch_size=1     # Process one ticker at a time to avoid batch failures
    ):
        """Initialize the YFinance connector.
        
        Args:
            use_cache: Whether to use local cache for data
            cache_dir: Directory for cached data
            cache_expire_days: Number of days before cache expires
            max_retries: Maximum number of retry attempts for rate-limited requests
            rate_limit: Rate limit in requests per second
            batch_size: Number of tickers to process in a single batch
        """
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.cache_expire_days = cache_expire_days
        self.max_retries = max_retries
        self.rate_limit = rate_limit
        self.batch_size = batch_size
        
        # Keep track of last request time to ensure rate limiting
        self.last_request_time = 0
        
        # Check for required packages
        if not YFINANCE_AVAILABLE:
            logger.error("yfinance package is not installed. Please install with 'pip install yfinance'")
            return
            
        if self.use_cache and not RATE_LIMITER_AVAILABLE:
            logger.warning("requests_ratelimiter or requests_cache not installed. Rate limiting and caching disabled.")
            self.use_cache = False
            
        # Create cache directory if it doesn't exist
        if self.use_cache and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Created cache directory: {self.cache_dir}")
        
        # Initialize session with cache and rate limiting
        self.session = self._create_session()
        
        # Log the yfinance version
        logger.info(f"Using yfinance version: {yf.__version__}")
    
    def _create_session(self):
        """Create a session with caching and rate limiting."""
        if not self.use_cache or not RATE_LIMITER_AVAILABLE:
            return None
            
        # Set up cache
        expire_after = datetime.timedelta(days=self.cache_expire_days)
        cache_name = os.path.join(self.cache_dir, 'yfinance_cache')
        
        # Create cache session
        cached_session = requests_cache.CachedSession(
            cache_name=cache_name,
            backend='sqlite',
            expire_after=expire_after
        )
        
        # Set up rate limiter
        rate = RequestRate(self.rate_limit, Duration.SECOND)
        limiter = Limiter(rate)
        
        # Create rate-limited session
        session = LimiterSession(
            limiter=limiter,
            session=cached_session
        )
        
        # Set a custom User-Agent to avoid being detected as a bot
        user_agent = random.choice(USER_AGENTS)
        
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://finance.yahoo.com/'
        })
        
        logger.info(f"Created session with rate limit of {self.rate_limit} req/sec and cache expiring after {self.cache_expire_days} days")
        logger.info(f"Using User-Agent: {user_agent}")
        return session
    
    def _rotate_user_agent(self):
        """Get a random user agent from the list."""
        return random.choice(USER_AGENTS)
    
    def _get_cache_path(self, ticker, start_date, end_date, interval):
        """Get the path to the cache file for the given parameters."""
        start_str = start_date.strftime('%Y%m%d')
        end_str = end_date.strftime('%Y%m%d')
        filename = f"{ticker}_{start_str}_{end_str}_{interval}.pkl"
        return os.path.join(self.cache_dir, filename)
    
    def _load_from_cache(self, ticker, start_date, end_date, interval):
        """Try to load data from the file cache."""
        if not self.use_cache:
            return None
            
        cache_path = self._get_cache_path(ticker, start_date, end_date, interval)
        
        with YFinanceConnector._cache_lock:
            if os.path.exists(cache_path):
                try:
                    # Check if the cache has expired
                    cache_time = os.path.getmtime(cache_path)
                    current_time = time.time()
                    cache_age_days = (current_time - cache_time) / (60 * 60 * 24)
                    
                    if cache_age_days <= self.cache_expire_days:
                        with open(cache_path, 'rb') as f:
                            data = pickle.load(f)
                        logger.info(f"Loaded cached data for {ticker} from {cache_path}")
                        return data
                    else:
                        logger.info(f"Cache for {ticker} has expired ({cache_age_days:.1f} days old)")
                        return None
                except Exception as e:
                    logger.warning(f"Failed to load cached data for {ticker}: {e}")
        
        return None
    
    def _save_to_cache(self, ticker, start_date, end_date, interval, data):
        """Save data to the file cache."""
        if not self.use_cache or data is None or data.empty:
            return
            
        cache_path = self._get_cache_path(ticker, start_date, end_date, interval)
        
        with YFinanceConnector._cache_lock:
            try:
                # Ensure the directory exists
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                
                with open(cache_path, 'wb') as f:
                    pickle.dump(data, f)
                logger.info(f"Saved {len(data)} data points for {ticker} to cache")
            except Exception as e:
                logger.warning(f"Failed to save data to cache for {ticker}: {e}")
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting by waiting if necessary."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        # Calculate how long to wait to respect the rate limit
        wait_time = max(0, (1.0 / self.rate_limit) - time_since_last_request)
        
        if wait_time > 0:
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        # Update the last request time
        self.last_request_time = time.time()
    
    def _get_ticker_data_with_retry(self, ticker, start_date, end_date, interval='1d'):
        """Get data for a single ticker with robust retry logic."""
        # First check cache
        data = self._load_from_cache(ticker, start_date, end_date, interval)
        if data is not None and not data.empty:
            return data
            
        # Apply rate limiting before making a request
        self._enforce_rate_limit()
        
        # Set up retry mechanism
        for retry in range(self.max_retries + 1):
            try:
                if retry > 0:
                    # Exponential backoff with jitter
                    delay = min(60, 2 ** retry) + random.uniform(0, 1)
                    logger.info(f"Retry {retry}/{self.max_retries} for {ticker}, waiting {delay:.2f} seconds...")
                    time.sleep(delay)
                    
                    # Rotate user agent on retries
                    if self.session:
                        user_agent = self._rotate_user_agent()
                        self.session.headers.update({'User-Agent': user_agent})
                        logger.info(f"Rotated User-Agent to: {user_agent}")
                
                # Use either Ticker method or download method based on retry number
                # In newer versions of yfinance, both methods accept a session parameter
                if retry % 2 == 0:
                    logger.info(f"Fetching {ticker} with Ticker.history() method")
                    ticker_obj = yf.Ticker(ticker, session=self.session)
                    hist = ticker_obj.history(start=start_date, end=end_date, interval=interval)
                else:
                    logger.info(f"Fetching {ticker} with yf.download() method")
                    hist = yf.download(
                        tickers=ticker,
                        start=start_date,
                        end=end_date,
                        interval=interval,
                        session=self.session,
                        progress=False,
                        threads=False,  # Disable threading for more stable requests
                        prepost=False,   # Don't include pre/post market data
                        auto_adjust=True # Adjust OHLC automatically
                    )
                
                if hist is not None and not hist.empty:
                    logger.info(f"Successfully retrieved {len(hist)} data points for {ticker}")
                    
                    # Save to cache
                    self._save_to_cache(ticker, start_date, end_date, interval, hist)
                    
                    return hist
                else:
                    logger.warning(f"Empty result for {ticker}")
                    if retry == self.max_retries:
                        logger.error(f"Max retries reached for {ticker} with empty results")
                        return pd.DataFrame()
            
            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"Error retrieving data for {ticker}: {e}")
                
                if 'too many requests' in error_msg or 'rate limit' in error_msg or '429' in error_msg:
                    # If we hit rate limits, increase backoff and retry
                    if retry == self.max_retries:
                        logger.error(f"Max retries reached for {ticker} due to rate limits")
                        return pd.DataFrame()
                else:
                    # For non-rate limit errors, we might not want to retry every type
                    if 'delisted' in error_msg or 'not found' in error_msg:
                        logger.error(f"Ticker {ticker} appears to be delisted or not found")
                        return pd.DataFrame()
        
        return pd.DataFrame()
    
    def get_historical_prices(
        self,
        tickers: List[str],
        start_date: datetime.date,
        end_date: datetime.date,
        interval: str = '1d'
    ) -> Dict[str, pd.DataFrame]:
        """Get historical price data for a list of tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval ('1d', '1wk', '1mo')
            
        Returns:
            Dictionary mapping ticker symbols to DataFrames with historical data
        """
        if not YFINANCE_AVAILABLE:
            logger.error("Cannot retrieve historical prices: yfinance not installed")
            return {}
            
        logger.info(f"Retrieving historical prices for {len(tickers)} tickers")
        
        result = {}
        
        # Process tickers in batches to avoid overwhelming the API
        for i in range(0, len(tickers), self.batch_size):
            batch = tickers[i:i+self.batch_size]
            logger.info(f"Processing batch {i//self.batch_size + 1}/{(len(tickers)-1)//self.batch_size + 1}: {batch}")
            
            for ticker in batch:
                # Process one ticker at a time for maximum reliability
                data = self._get_ticker_data_with_retry(ticker, start_date, end_date, interval)
                if not data.empty:
                    result[ticker] = data
                else:
                    logger.warning(f"No data returned for {ticker}")
            
            # Add a delay between batches
            if i + self.batch_size < len(tickers):
                delay = max(2.0, 1.0 / self.rate_limit * self.batch_size) + random.uniform(0, 1)
                logger.info(f"Waiting {delay:.2f} seconds before next batch...")
                time.sleep(delay)
        
        logger.info(f"Successfully retrieved data for {len(result)}/{len(tickers)} tickers")
        return result
    
    def get_benchmark_data(
        self,
        benchmark: str,
        start_date: datetime.date,
        end_date: datetime.date,
        interval: str = '1d'
    ) -> pd.DataFrame:
        """Get historical price data for a benchmark index.
        
        Args:
            benchmark: Ticker symbol for the benchmark (e.g., 'SPY' for S&P 500)
            start_date: Start date for historical data
            end_date: End date for historical data
            interval: Data interval ('1d', '1wk', '1mo')
            
        Returns:
            DataFrame with historical benchmark data
        """
        logger.info(f"Retrieving benchmark data for {benchmark}")
        
        # Simply use the single ticker method
        result = self._get_ticker_data_with_retry(benchmark, start_date, end_date, interval)
        return result 