#!/usr/bin/env python
"""
Run all backtesting tests.

This script discovers and runs all backtesting tests.
"""

import unittest
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_tests():
    """Discover and run all backtesting tests."""
    # Discover tests in the backtesting directory
    loader = unittest.TestLoader()
    suite = loader.discover('tests/backtesting', pattern='test_*.py')
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    print("Running backtesting tests...\n")
    
    # Run tests
    success = run_tests()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1) 