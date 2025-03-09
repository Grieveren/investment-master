"""
Debug script to test the portfolio CSV parsing functionality
"""

import os
import json
import sys
from dotenv import load_dotenv
from utils.logger import logger
from utils.config import config
from utils.portfolio_optimizer import parse_portfolio_csv

def test_parse_portfolio_csv():
    """Test parsing portfolio data from a CSV file."""
    # Get the portfolio CSV path from config
    csv_path = config["portfolio"]["csv_file"]
    print(f"Parsing portfolio data from CSV: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"ERROR: Portfolio CSV file not found: {csv_path}")
        return None
    
    # Parse the portfolio data
    try:
        portfolio_data = parse_portfolio_csv(csv_path)
        
        # Print summary information
        print("\nPortfolio Summary:")
        for key, value in portfolio_data['summary'].items():
            print(f"  {key}: {value}")
        
        # Print position information
        print(f"\nPositions ({len(portfolio_data['positions'])}):")
        for i, position in enumerate(portfolio_data['positions']):
            print(f"\nPosition {i+1}:")
            print(f"  Bezeichnung: {position.get('Bezeichnung', 'N/A')}")
            print(f"  ISIN: {position.get('ISIN', 'N/A')}")
            print(f"  Wert in EUR: {position.get('Wert in EUR', 'N/A')}")
            print(f"  Anteil im Depot: {position.get('Anteil im Depot', 'N/A')}")
        
        return portfolio_data
    except Exception as e:
        print(f"ERROR: Failed to parse portfolio CSV: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    load_dotenv()
    print("Testing portfolio CSV parsing...")
    portfolio_data = test_parse_portfolio_csv()
    
    if portfolio_data:
        print(f"\nSuccessfully parsed portfolio data with {len(portfolio_data['positions'])} positions.")
    else:
        print("\nFailed to parse portfolio data.")
    
    print("\nTest complete.") 