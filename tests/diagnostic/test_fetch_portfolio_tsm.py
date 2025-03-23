"""
Test script to verify TSM works in the full portfolio fetching pipeline.
"""

import os
from dotenv import load_dotenv
from src.core.portfolio import parse_portfolio, get_stock_ticker_and_exchange
from src.tools.api import fetch_all_companies

# Load environment variables
load_dotenv()

def test_portfolio_with_tsm():
    """Test that we can fetch TSM data as part of a portfolio."""
    
    # Get API token from environment
    api_token = os.getenv("SWS_API_TOKEN")
    if not api_token:
        print("ERROR: SWS_API_TOKEN not found in environment")
        return False
    
    # Create a test portfolio with TSM
    mock_portfolio = [
        {"name": "TSM", "shares": 30, "current_price": 139.20, "market_value": 4176, "weight": 4.12},
        {"name": "Microsoft", "shares": 10, "current_price": 425.52, "market_value": 4255.2, "weight": 4.20},
    ]
    
    print("Fetching data for test portfolio with TSM...")
    
    # Test ticker lookup
    tsm_info = get_stock_ticker_and_exchange("TSM")
    if not tsm_info:
        print("❌ ERROR: TSM ticker lookup failed")
        return False
    
    print(f"✅ TSM ticker lookup: {tsm_info}")
    
    # Fetch all company data
    api_data = fetch_all_companies(mock_portfolio, api_token)
    
    # Check if TSM data was fetched
    if "TSM" in api_data:
        print("✅ SUCCESS: TSM data found in API results")
        
        # Verify the structure
        tsm_data = api_data["TSM"]
        if (isinstance(tsm_data, dict) and 
            "data" in tsm_data and 
            "companyByExchangeAndTickerSymbol" in tsm_data["data"] and
            tsm_data["data"]["companyByExchangeAndTickerSymbol"] is not None):
            
            company = tsm_data["data"]["companyByExchangeAndTickerSymbol"]
            name = company.get("name", "Unknown")
            statements_count = len(company.get("statements", []))
            
            print(f"✅ Company data: {name}")
            print(f"Found {statements_count} statements")
            
            return True
        else:
            print("❌ ERROR: TSM data structure not as expected")
            return False
    else:
        print("❌ ERROR: TSM data not found in API results")
        print(f"Available keys: {api_data.keys()}")
        return False

if __name__ == "__main__":
    success = test_portfolio_with_tsm()
    exit(0 if success else 1) 