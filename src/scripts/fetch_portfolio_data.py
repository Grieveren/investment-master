#!/usr/bin/env python
"""
Script to fetch portfolio data from SimplyWall.st API without running analysis.
This is a stripped-down version of portfolio_analyzer.py that only handles
the data fetching part.
"""

import os
import json
import time
from dotenv import load_dotenv
from src.core.logger import logger
from src.core.config import config
from src.tools.api import fetch_all_companies
from src.core.portfolio import parse_portfolio

def main():
    """Main function to fetch portfolio data."""
    start_time = time.time()
    
    print("STARTING: Portfolio Data Fetcher")
    print(f"Working directory: {os.getcwd()}")
    
    # Load environment variables
    print("\nLoading environment variables...")
    load_dotenv()
    print("Environment variables loaded")
    
    # Check API token
    sws_api_token = os.getenv("SWS_API_TOKEN")
    has_sws_token = bool(sws_api_token)
    print(f"SWS API Token available: {has_sws_token}")
    
    if not has_sws_token:
        logger.error("SWS API token not found in environment variables.")
        print("ERROR: SWS API token not found. Please set SWS_API_TOKEN environment variable.")
        return 1
    
    # Parse portfolio data
    logger.info("Parsing portfolio data from combined_portfolio.md...")
    try:
        portfolio = parse_portfolio("combined_portfolio.md")
        stock_count = len(portfolio)
        logger.info(f"Found {stock_count} stocks in portfolio.")
        print(f"\nFound {stock_count} stocks in portfolio.")
    except Exception as e:
        logger.error(f"Error parsing portfolio data: {e}")
        print(f"ERROR: Failed to parse portfolio data: {e}")
        return 1
    
    # Fetch data from SimplyWall.st API
    logger.info("Fetching data from SimplyWall.st API...")
    print("\nFetching data from SimplyWall.st API...")
    
    try:
        api_data = fetch_all_companies(portfolio, sws_api_token)
        
        # Save API data to file
        output_dir = "data/raw"
        os.makedirs(output_dir, exist_ok=True)
        api_data_file = os.path.join(output_dir, "api_data.json")
        with open(api_data_file, "w") as f:
            json.dump(api_data, f, indent=2)
            
        logger.info(f"Data saved to {api_data_file}")
        print(f"\nRaw API data saved to {api_data_file}")
        
        # Print success statistics
        success_count = len(api_data)
        total_count = len(portfolio)
        success_rate = (success_count / total_count) * 100 if total_count > 0 else 0
        
        print(f"\nSuccessfully fetched data for {success_count} out of {total_count} stocks ({success_rate:.1f}%).")
        if success_count < total_count:
            print(f"Failed to fetch data for {total_count - success_count} stocks.")
            # List the stocks that failed
            failed_stocks = [stock["name"] for stock in portfolio if stock["name"] not in api_data]
            print(f"Failed stocks: {', '.join(failed_stocks)}")
            
    except Exception as e:
        logger.error(f"Error fetching API data: {e}")
        print(f"ERROR: Failed to fetch API data: {e}")
        return 1
    
    # Calculate and print execution time
    execution_time = time.time() - start_time
    print(f"\nTotal execution time: {execution_time:.2f} seconds")
    
    return 0

if __name__ == "__main__":
    exit(main()) 