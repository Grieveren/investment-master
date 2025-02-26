"""
Tests for the portfolio module.
"""

import os
import unittest
from unittest.mock import patch, mock_open
from utils.portfolio import parse_portfolio, get_stock_ticker_and_exchange

class TestPortfolioModule(unittest.TestCase):
    """Tests for the portfolio module."""

    def test_get_stock_ticker_and_exchange(self):
        """Test the get_stock_ticker_and_exchange function."""
        # Test existing stock
        result = get_stock_ticker_and_exchange("NVIDIA")
        self.assertIsNotNone(result)
        self.assertEqual(result["ticker"], "NVDA")
        self.assertEqual(result["exchange"], "NasdaqGS")
        
        # Test non-existing stock
        result = get_stock_ticker_and_exchange("NonExistingStock")
        self.assertIsNone(result)
    
    @patch('utils.config.config', {"api": {"portfolio_file": "test_portfolio.md"}})
    @patch('builtins.open', mock_open(read_data="""
| Security | Shares | Price | Market Value | Weight |
|----------|--------|-------|--------------|--------|
| NVIDIA | 10 | 100.0 | 1000.0 | 50% |
| Microsoft | 5 | 200.0 | 1000.0 | 50% |
    """))
    def test_parse_portfolio(self):
        """Test the parse_portfolio function."""
        result = parse_portfolio()
        
        # Check that we got two stocks
        self.assertEqual(len(result), 2)
        
        # Check first stock
        self.assertEqual(result[0]["name"], "NVIDIA")
        self.assertEqual(result[0]["shares"], 10)
        self.assertEqual(result[0]["current_price"], 100.0)
        self.assertEqual(result[0]["market_value"], 1000.0)
        self.assertEqual(result[0]["weight"], 50.0)
        
        # Check second stock
        self.assertEqual(result[1]["name"], "Microsoft")
        self.assertEqual(result[1]["shares"], 5)
        self.assertEqual(result[1]["current_price"], 200.0)
        self.assertEqual(result[1]["market_value"], 1000.0)
        self.assertEqual(result[1]["weight"], 50.0)
    
    @patch('utils.config.config', {"api": {"portfolio_file": "test_portfolio.md"}})
    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_parse_portfolio_file_not_found(self, mock_open):
        """Test the parse_portfolio function when the file is not found."""
        result = parse_portfolio()
        
        # Check that we got an empty list
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main() 