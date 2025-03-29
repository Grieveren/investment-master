"""
Unit tests for the YFinanceConnector class.
"""

import unittest
import datetime
import pandas as pd
from unittest.mock import patch, MagicMock
from src.backtesting.data.yfinance_connector import YFinanceConnector

class TestYFinanceConnector(unittest.TestCase):
    """Test cases for the YFinanceConnector class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.connector = YFinanceConnector()
        
        self.tickers = ['AAPL', 'MSFT', 'GOOGL']
        self.start_date = datetime.date(2023, 1, 1)
        self.end_date = datetime.date(2023, 12, 31)
        self.benchmark = 'SPY'
    
    @patch('src.backtesting.data.yfinance_connector.YFINANCE_AVAILABLE', True)
    @patch('src.backtesting.data.yfinance_connector.yf')
    def test_get_historical_prices(self, mock_yf):
        """Test getting historical prices."""
        # Create mock Ticker objects
        mock_tickers = {}
        mock_data = {}
        
        for ticker in self.tickers:
            # Create mock history DataFrame
            history = pd.DataFrame({
                'Open': [100.0, 101.0, 102.0],
                'High': [105.0, 106.0, 107.0],
                'Low': [98.0, 99.0, 100.0],
                'Close': [103.0, 104.0, 105.0],
                'Volume': [1000000, 1100000, 1200000]
            })
            
            # Create mock Ticker
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = history
            
            # Store mocks
            mock_tickers[ticker] = mock_ticker
            mock_data[ticker] = history
            
            # Configure yf.Ticker to return our mock
            mock_yf.Ticker.side_effect = lambda t: mock_tickers.get(t)
        
        # Call the method
        result = self.connector.get_historical_prices(
            tickers=self.tickers,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        # Check that yf.Ticker was called for each ticker
        self.assertEqual(mock_yf.Ticker.call_count, len(self.tickers))
        
        # Check that history was called for each ticker
        for ticker in self.tickers:
            mock_tickers[ticker].history.assert_called_once_with(
                start=self.start_date,
                end=self.end_date,
                interval='1d'
            )
        
        # Check the result
        self.assertEqual(len(result), len(self.tickers))
        for ticker in self.tickers:
            self.assertIn(ticker, result)
            pd.testing.assert_frame_equal(result[ticker], mock_data[ticker])
    
    @patch('src.backtesting.data.yfinance_connector.YFINANCE_AVAILABLE', True)
    @patch('src.backtesting.data.yfinance_connector.yf')
    def test_get_dividends(self, mock_yf):
        """Test getting dividend history."""
        # Create mock Ticker objects
        mock_tickers = {}
        mock_dividends = {}
        
        for ticker in self.tickers:
            # Create mock dividends Series
            # Create dates within our test range
            dates = pd.date_range(self.start_date, self.end_date, periods=4)
            dividends = pd.Series([0.5, 0.5, 0.6, 0.6], index=dates)
            
            # Create mock Ticker
            mock_ticker = MagicMock()
            mock_ticker.dividends = dividends
            
            # Store mocks
            mock_tickers[ticker] = mock_ticker
            mock_dividends[ticker] = dividends
            
            # Configure yf.Ticker to return our mock
            mock_yf.Ticker.side_effect = lambda t: mock_tickers.get(t)
        
        # Call the method
        result = self.connector.get_dividends(
            tickers=self.tickers,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        # Check that yf.Ticker was called for each ticker
        self.assertEqual(mock_yf.Ticker.call_count, len(self.tickers))
        
        # Check the result
        self.assertEqual(len(result), len(self.tickers))
        for ticker in self.tickers:
            self.assertIn(ticker, result)
            pd.testing.assert_series_equal(result[ticker], mock_dividends[ticker])
    
    @patch('src.backtesting.data.yfinance_connector.YFINANCE_AVAILABLE', True)
    @patch('src.backtesting.data.yfinance_connector.yf')
    def test_get_benchmark_data(self, mock_yf):
        """Test getting benchmark data."""
        # Create mock benchmark data
        benchmark_data = pd.DataFrame({
            'Open': [420.0, 425.0, 430.0],
            'High': [425.0, 430.0, 435.0],
            'Low': [415.0, 420.0, 425.0],
            'Close': [422.0, 427.0, 432.0],
            'Volume': [10000000, 11000000, 12000000]
        })
        
        # Create mock Ticker for benchmark
        mock_benchmark = MagicMock()
        mock_benchmark.history.return_value = benchmark_data
        
        # Configure yf.Ticker to return our mock
        mock_yf.Ticker.return_value = mock_benchmark
        
        # Call the method
        result = self.connector.get_benchmark_data(
            benchmark=self.benchmark,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        # Check that yf.Ticker was called for the benchmark
        mock_yf.Ticker.assert_called_once_with(self.benchmark)
        
        # Check that history was called for the benchmark
        mock_benchmark.history.assert_called_once_with(
            start=self.start_date,
            end=self.end_date,
            interval='1d'
        )
        
        # Check the result
        pd.testing.assert_frame_equal(result, benchmark_data)
    
    @patch('src.backtesting.data.yfinance_connector.YFINANCE_AVAILABLE', False)
    def test_no_yfinance_available(self):
        """Test behavior when yfinance is not available."""
        # Call the methods
        prices = self.connector.get_historical_prices(
            tickers=self.tickers,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        dividends = self.connector.get_dividends(
            tickers=self.tickers,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        benchmark = self.connector.get_benchmark_data(
            benchmark=self.benchmark,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        # Check the results - should all be empty
        self.assertEqual(prices, {})
        self.assertEqual(dividends, {})
        self.assertTrue(benchmark.empty)

if __name__ == '__main__':
    unittest.main() 