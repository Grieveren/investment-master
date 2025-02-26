"""
SimplyWall.st Data Fetcher

This script focuses solely on fetching financial data from SimplyWall.st API.
It parses portfolio data, fetches detailed financial statements, and saves the raw data
without performing any analysis.

Usage:
1. Create a .env file with your SimplyWall.st API token (SWS_API_TOKEN=your_token)
2. Run the script: python sws_data_fetcher.py
3. Review the raw data in sws_data_output.json
"""

import os
import json
import requests
import datetime
import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API key
SWS_API_TOKEN = os.getenv("SWS_API_TOKEN")

# API endpoint
SWS_API_URL = "https://api.simplywall.st/graphql"

# Retry settings
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # Base delay in seconds between retries
RETRY_MAX_DELAY = 10  # Maximum delay in seconds between retries

def parse_portfolio():
    """Parse the portfolio data from combined_portfolio.md"""
    with open("combined_portfolio.md", "r") as f:
        content = f.read()
    
    stocks = []
    
    for line in content.split('\n'):
        if '|' in line and not line.startswith('|--') and "Cash EUR" not in line:
            parts = [part.strip() for part in line.split('|')]
            if len(parts) >= 6 and parts[1] != "Security" and "Cash" not in parts[1]:
                try:
                    stocks.append({
                        "name": parts[1].strip(),
                        "shares": int(parts[2].strip()),
                        "current_price": float(parts[3].strip()),
                        "market_value": float(parts[4].strip().replace(',', '')),
                        "weight": float(parts[5].strip().replace('%', ''))
                    })
                except (ValueError, IndexError) as e:
                    print(f"Error parsing line: {line}, Error: {e}")
    
    return stocks

def get_stock_ticker_and_exchange(stock_name):
    """Map stock names to tickers and exchanges for the API"""
    stock_map = {
        "Berkshire Hathaway B": {"ticker": "BRK.B", "exchange": "NYSE"},
        "Allianz SE": {"ticker": "ALV", "exchange": "XTRA"},
        "GitLab Inc.": {"ticker": "GTLB", "exchange": "NasdaqGS"},
        "NVIDIA": {"ticker": "NVDA", "exchange": "NasdaqGS"},
        "Microsoft": {"ticker": "MSFT", "exchange": "NasdaqGS"},
        "Alphabet C": {"ticker": "GOOG", "exchange": "NasdaqGS"},
        "CrowdStrike": {"ticker": "CRWD", "exchange": "NasdaqGS"},
        "Advanced Micro Devices": {"ticker": "AMD", "exchange": "NasdaqGS"},
        "Nutanix": {"ticker": "NTNX", "exchange": "NasdaqGS"},
        "ASML Holding": {"ticker": "ASML", "exchange": "NasdaqGS"},
        "Taiwan Semiconductor ADR": {"ticker": "TSM", "exchange": "NYSE"}
    }
    
    return stock_map.get(stock_name)

def fetch_company_data(ticker, exchange, max_retries=MAX_RETRIES):
    """Fetch company data from SimplyWall.st GraphQL API with retry logic"""
    query = """
    query companyByExchangeAndTickerSymbol($exchange: String!, $symbol: String!) {
      companyByExchangeAndTickerSymbol(exchange: $exchange, tickerSymbol: $symbol) {
        id
        name
        exchangeSymbol
        tickerSymbol
        marketCapUSD
        statements {
          name
          title
          area
          type
          value
          outcome
          description
          severity
          outcomeName
        }
      }
    }
    """
    
    variables = {
        "exchange": exchange,
        "symbol": ticker
    }
    
    headers = {
        "Authorization": f"Bearer {SWS_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    retries = 0
    while retries <= max_retries:
        response = None
        try:
            if retries > 0:
                # Calculate exponential backoff delay with jitter
                delay = min(RETRY_BASE_DELAY * (2 ** (retries - 1)) + random.uniform(0, 1), RETRY_MAX_DELAY)
                print(f"Retry attempt {retries}/{max_retries} after {delay:.2f}s delay...")
                time.sleep(delay)
            
            response = requests.post(
                SWS_API_URL,
                headers=headers,
                json={"query": query, "variables": variables}
            )
            
            # Debug output to see raw response
            print(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            response_data = response.json()
            
            # Check for server-side errors in the GraphQL response
            if "errors" in response_data and response_data.get("data") is None:
                error_msg = response_data["errors"][0]["message"] if response_data["errors"] else "Unknown GraphQL error"
                
                if "socket hang up" in error_msg or "INTERNAL_SERVER_ERROR" in str(response_data):
                    if retries < max_retries:
                        print(f"Server-side error: {error_msg}. Will retry.")
                        retries += 1
                        continue
                    else:
                        print(f"Max retries reached. Last error: {error_msg}")
                        return None
                else:
                    print(f"GraphQL error: {error_msg}")
                    return response_data  # Return the error response for further analysis
            
            # If we got here, the request was successful
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"Request error fetching data for {ticker} on {exchange}: {e}")
            
            if response and hasattr(response, 'status_code') and response.status_code != 200:
                print(f"Response: {response.text}")
            
            if retries < max_retries:
                retries += 1
            else:
                print(f"Max retries reached. Last error: {e}")
                return None
                
        except Exception as e:
            print(f"Unexpected error fetching data for {ticker} on {exchange}: {e}")
            
            if retries < max_retries:
                retries += 1
            else:
                print(f"Max retries reached. Last error: {e}")
                return None
    
    return None  # Should never reach here but added for safety

def main():
    if not SWS_API_TOKEN:
        print("Error: SimplyWall.st API token not found. Please add it to your .env file.")
        return
    
    print(f"Using SimplyWall.st API token: {SWS_API_TOKEN[:5]}...{SWS_API_TOKEN[-4:] if SWS_API_TOKEN else 'None'}")
    print(f"Retry settings: max_retries={MAX_RETRIES}, base_delay={RETRY_BASE_DELAY}s, max_delay={RETRY_MAX_DELAY}s")
    
    # Parse portfolio data
    print("Parsing portfolio data...")
    stocks = parse_portfolio()
    print(f"Found {len(stocks)} stocks in portfolio.")
    
    # Fetch data from SimplyWall.st API
    print("\nFetching data from SimplyWall.st API...")
    api_data = {}
    
    for stock in stocks:
        stock_info = get_stock_ticker_and_exchange(stock["name"])
        if stock_info:
            ticker = stock_info["ticker"]
            exchange = stock_info["exchange"]
            print(f"Fetching data for {stock['name']} ({ticker} on {exchange})...")
            
            stock_data = fetch_company_data(ticker, exchange)
            if stock_data:
                # Safely check the response structure
                has_valid_data = (
                    isinstance(stock_data, dict) and 
                    "data" in stock_data and 
                    isinstance(stock_data["data"], dict) and
                    "companyByExchangeAndTickerSymbol" in stock_data["data"] and
                    stock_data["data"]["companyByExchangeAndTickerSymbol"] is not None
                )
                
                if has_valid_data:
                    api_data[stock["name"]] = stock_data
                    
                    company = stock_data["data"]["companyByExchangeAndTickerSymbol"]
                    statement_count = len(company.get("statements", [])) if company else 0
                    print(f"✅ Successfully fetched data for {stock['name']}: {statement_count} statements")
                else:
                    print(f"⚠️ Data received for {stock['name']} but structure is not as expected:")
                    print(json.dumps(stock_data, indent=2)[:500] + "..." if len(json.dumps(stock_data)) > 500 else json.dumps(stock_data, indent=2))
            else:
                print(f"❌ Failed to fetch data for {stock['name']}")
        else:
            print(f"⚠️ Warning: No ticker/exchange found for {stock['name']}")
    
    # Save raw API data
    output_file = "sws_data_output.json"
    print(f"\nSaving raw API data to {output_file}...")
    with open(output_file, "w") as f:
        json.dump(api_data, f, indent=2)
    print(f"Raw API data saved to {output_file}")
    
    print("\nData fetching complete!")

if __name__ == "__main__":
    main() 