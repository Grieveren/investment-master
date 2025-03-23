"""
YFinance data connector for retrieving historical price data.
"""

import logging
import pandas as pd
import datetime
from typing import Dict, List, Optional, Union

# This is a placeholder - you'll need to install yfinance
# pip install yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

logger = logging.getLogger(__name__)

class YFinanceConnector:
    """Connector for retrieving historical price data from Yahoo Finance."""
    
    def __init__(self):
        """Initialize the YFinance connector."""
        if not YFINANCE_AVAILABLE:
            logger.warning("yfinance package is not installed. Please install with 'pip install yfinance'")
        
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
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(
                    start=start_date, 
                    end=end_date, 
                    interval=interval
                )
                
                if hist.empty:
                    logger.warning(f"No historical data found for {ticker}")
                else:
                    result[ticker] = hist
                    logger.info(f"Retrieved {len(hist)} data points for {ticker}")
                    
            except Exception as e:
                logger.error(f"Error retrieving data for {ticker}: {e}")
                
        return result
    
    def get_dividends(
        self,
        tickers: List[str],
        start_date: datetime.date,
        end_date: datetime.date
    ) -> Dict[str, pd.Series]:
        """Get dividend history for a list of tickers.
        
        Args:
            tickers: List of ticker symbols
            start_date: Start date for dividend history
            end_date: End date for dividend history
            
        Returns:
            Dictionary mapping ticker symbols to Series with dividend history
        """
        if not YFINANCE_AVAILABLE:
            logger.error("Cannot retrieve dividends: yfinance not installed")
            return {}
            
        logger.info(f"Retrieving dividend history for {len(tickers)} tickers")
        
        result = {}
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                dividends = stock.dividends
                
                # Filter by date range
                if not dividends.empty:
                    mask = (dividends.index >= pd.Timestamp(start_date)) & (dividends.index <= pd.Timestamp(end_date))
                    filtered_dividends = dividends[mask]
                    
                    if filtered_dividends.empty:
                        logger.info(f"No dividends in date range for {ticker}")
                    else:
                        result[ticker] = filtered_dividends
                        logger.info(f"Retrieved {len(filtered_dividends)} dividends for {ticker}")
                else:
                    logger.info(f"No dividend history found for {ticker}")
                    
            except Exception as e:
                logger.error(f"Error retrieving dividends for {ticker}: {e}")
                
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
        if not YFINANCE_AVAILABLE:
            logger.error("Cannot retrieve benchmark data: yfinance not installed")
            return pd.DataFrame()
            
        logger.info(f"Retrieving benchmark data for {benchmark}")
        
        try:
            index = yf.Ticker(benchmark)
            hist = index.history(
                start=start_date, 
                end=end_date, 
                interval=interval
            )
            
            if hist.empty:
                logger.warning(f"No historical data found for benchmark {benchmark}")
                return pd.DataFrame()
            
            logger.info(f"Retrieved {len(hist)} benchmark data points")
            return hist
                
        except Exception as e:
            logger.error(f"Error retrieving benchmark data for {benchmark}: {e}")
            return pd.DataFrame() 