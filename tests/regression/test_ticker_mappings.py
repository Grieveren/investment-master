"""
Regression tests for ticker mapping functionality.

Tests for various ticker mappings to ensure they continue working correctly.
"""

import unittest
from src.core.portfolio import get_stock_ticker_and_exchange

class TestTickerMappings(unittest.TestCase):
    """Test the ticker mappings against regression issues."""
    
    def test_direct_ticker_lookup(self):
        """Test that direct ticker lookups work correctly."""
        # Test common ticker symbols directly
        tickers = ["MSFT", "GOOG", "NVDA", "TSM", "BRK.B", "ASML", "AMD", "CRWD", "NTNX", "GTLB", "ALV"]
        
        for ticker in tickers:
            with self.subTest(ticker=ticker):
                result = get_stock_ticker_and_exchange(ticker)
                self.assertIsNotNone(result, f"Direct ticker lookup failed for {ticker}")
                self.assertEqual(result["ticker"], ticker)
    
    def test_company_name_lookup(self):
        """Test that company name lookups work correctly."""
        # Map of company names to expected tickers
        name_to_ticker = {
            "Microsoft": "MSFT",
            "Alphabet C": "GOOG",
            "NVIDIA": "NVDA",
            "Taiwan Semiconductor": "TSM",
            "TSMC": "TSM",
            "Taiwan Semiconductor Manufacturing Company": "TSM",
            "Taiwan Semiconductor ADR": "TSM",
            "Berkshire Hathaway B": "BRK.B",
            "ASML Holding": "ASML",
            "Advanced Micro Devices": "AMD",
            "CrowdStrike": "CRWD",
            "Nutanix": "NTNX",
            "GitLab Inc.": "GTLB",
            "Allianz SE": "ALV"
        }
        
        for name, expected_ticker in name_to_ticker.items():
            with self.subTest(name=name):
                result = get_stock_ticker_and_exchange(name)
                self.assertIsNotNone(result, f"Company name lookup failed for {name}")
                self.assertEqual(result["ticker"], expected_ticker)
    
if __name__ == '__main__':
    unittest.main() 