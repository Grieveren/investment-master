"""
Simple test to verify we can fetch TSM data from SimplyWall.st API.
"""

import os
from dotenv import load_dotenv
from src.tools.api import fetch_company_data
from src.core.logger import logger

# Load environment variables
load_dotenv()

def test_tsm_fetch():
    """Test that we can fetch TSM data from SimplyWall.st API."""
    
    # Get API token from environment
    api_token = os.getenv("SWS_API_TOKEN")
    if not api_token:
        print("ERROR: SWS_API_TOKEN not found in environment")
        return False
    
    # Fetch TSM data
    ticker = "TSM"
    exchange = "NYSE"
    print(f"Fetching data for {ticker} on {exchange}...")
    
    # Attempt to fetch data
    result = fetch_company_data(ticker, exchange, api_token)
    
    # Check if we got a valid response
    if result:
        # Verify the structure
        if (isinstance(result, dict) and 
            "data" in result and 
            "companyByExchangeAndTickerSymbol" in result["data"] and
            result["data"]["companyByExchangeAndTickerSymbol"] is not None):
            
            company = result["data"]["companyByExchangeAndTickerSymbol"]
            name = company.get("name", "Unknown")
            statements_count = len(company.get("statements", []))
            
            print(f"✅ SUCCESS: Got data for {name}")
            print(f"Found {statements_count} statements")
            
            return True
        else:
            print("❌ ERROR: Data structure not as expected")
            print(f"Response: {result}")
            return False
    else:
        print("❌ ERROR: Failed to fetch data")
        return False

if __name__ == "__main__":
    success = test_tsm_fetch()
    exit(0 if success else 1) 