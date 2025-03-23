"""
Test the fix for the TSM ticker issue where TSM is not properly mapped when used directly.
"""

import unittest
from src.core.portfolio import get_stock_ticker_and_exchange

class TestTSMFix(unittest.TestCase):
    """Test the fix for the TSM ticker mapping issue."""
    
    def test_tsm_mapping(self):
        """Test that different variations of TSM are correctly mapped."""
        # Test the full name (existing mapping)
        result = get_stock_ticker_and_exchange("Taiwan Semiconductor ADR")
        self.assertIsNotNone(result)
        self.assertEqual(result["ticker"], "TSM")
        self.assertEqual(result["exchange"], "NYSE")
        
        # Test just using the ticker symbol (should work after the fix)
        result = get_stock_ticker_and_exchange("TSM")
        self.assertIsNotNone(result)
        self.assertEqual(result["ticker"], "TSM")
        self.assertEqual(result["exchange"], "NYSE")
        
        # Test common name (should work after the fix)
        result = get_stock_ticker_and_exchange("Taiwan Semiconductor")
        self.assertIsNotNone(result)
        self.assertEqual(result["ticker"], "TSM")
        self.assertEqual(result["exchange"], "NYSE")
        
        # Test full legal name (should work after the fix)
        result = get_stock_ticker_and_exchange("Taiwan Semiconductor Manufacturing Company")
        self.assertIsNotNone(result)
        self.assertEqual(result["ticker"], "TSM")
        self.assertEqual(result["exchange"], "NYSE")
    
if __name__ == '__main__':
    unittest.main() 