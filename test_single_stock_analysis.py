"""
Test script to validate analysis on a single stock.

This script loads existing API data and runs the analysis on a single stock
to verify that the extraction and formatting logic works correctly.
"""

import os
import json
import datetime
import argparse
from dotenv import load_dotenv
from utils.logger import logger
from utils.config import config
from utils.analysis import create_openai_client, create_anthropic_client, get_value_investing_signals
from utils.file_operations import save_json_data, save_markdown
from utils.portfolio import get_stock_ticker_and_exchange

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test analysis on a single stock")
    parser.add_argument("--model", type=str, default="claude-3-7", 
                        help="AI model to use (claude-3-7 or o3-mini)")
    parser.add_argument("--ticker", type=str, default="BRK.B",
                        help="Ticker symbol to analyze")
    parser.add_argument("--company", type=str, default="Berkshire Hathaway B",
                        help="Company name (if different from the default)")
    return parser.parse_args()

def main():
    """Run analysis on a single stock for testing."""
    # Parse command line arguments
    args = parse_args()
    
    print("STARTING: Single Stock Analysis Test")
    print(f"Working directory: {os.getcwd()}")
    
    # Load environment variables
    load_dotenv()
    
    # Get API keys
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Use model from command line args
    model = args.model
    print(f"Testing with model: {model}")
    
    # Create appropriate client
    if model.startswith("claude"):
        print("Initializing Anthropic client...")
        client = create_anthropic_client(anthropic_api_key)
        if not client:
            print("Error: Failed to initialize Anthropic client.")
            return
        openai_client = None
        anthropic_client = client
    else:
        print("Initializing OpenAI client...")
        client = create_openai_client(openai_api_key)
        if not client:
            print("Error: Failed to initialize OpenAI client.")
            return
        openai_client = client
        anthropic_client = None
    
    # Load existing API data to avoid making new API calls
    api_data_file = config["output"]["raw_data_file"]
    try:
        with open(api_data_file, 'r') as f:
            api_data = json.load(f)
        print(f"Loaded API data from {api_data_file}")
        
        # Debug: Print keys from the API data
        print(f"API data contains {len(api_data)} entries")
        print(f"API data keys: {list(api_data.keys())[:5]}..." if len(api_data) > 0 else "No keys found")
        
        # If the API data is keyed by company name, show those
        for key in list(api_data.keys())[:5]:
            if isinstance(api_data[key], dict) and "data" in api_data[key]:
                print(f"Key '{key}' contains data dict")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading API data: {e}")
        return
    
    # Create minimal portfolio data for a single stock
    test_ticker = args.ticker
    test_company = args.company
    
    print(f"Testing analysis for {test_company} ({test_ticker})")
    
    portfolio_data = [
        {
            "name": test_company,
            "shares": 100,
            "current_price": 400.0,
            "market_value": 40000.0,
            "weight": 10.0
        }
    ]
    
    # Determine how to access the API data based on its structure
    filtered_api_data = {}
    
    # Try different ways to find the data
    if test_ticker in api_data:
        # If the data is keyed by ticker
        filtered_api_data[test_ticker] = api_data[test_ticker]
        print(f"Found API data for ticker {test_ticker}")
    elif test_company in api_data:
        # If the data is keyed by company name
        filtered_api_data[test_ticker] = api_data[test_company]
        print(f"Found API data for company name {test_company}")
    else:
        # Try company name variations
        for company_key in api_data.keys():
            if test_company.lower() in company_key.lower() or test_ticker.lower() in company_key.lower():
                filtered_api_data[test_ticker] = api_data[company_key]
                print(f"Found API data for similar key: {company_key}")
                break
        
        # If still not found, we may need to reconstruct the data
        if not filtered_api_data and isinstance(api_data, dict):
            print("Building synthetic test data from the API data structure")
            
            # Use the first entry as a template
            if len(api_data) > 0:
                first_key = list(api_data.keys())[0]
                template_data = api_data[first_key]
                
                # Create a simplified version for testing
                filtered_api_data[test_ticker] = {
                    "name": test_company,
                    "ticker": test_ticker,
                    "exchange": "NYSE",
                    "statements": []
                }
                
                # Copy the data structure but with minimal content
                if isinstance(template_data, dict):
                    if "data" in template_data and "companyByExchangeAndTickerSymbol" in template_data["data"]:
                        filtered_api_data[test_ticker] = {
                            "data": {
                                "companyByExchangeAndTickerSymbol": {
                                    "name": test_company,
                                    "tickerSymbol": test_ticker,
                                    "exchangeSymbol": "NYSE",
                                    "statements": template_data["data"]["companyByExchangeAndTickerSymbol"].get("statements", [])
                                }
                            }
                        }
    
    if not filtered_api_data:
        print(f"Error: Test stock {test_ticker} not found in API data")
        print("Available keys:")
        for key in list(api_data.keys())[:10]:
            print(f"  - {key}")
        return
    
    print(f"Running analysis for {test_company} ({test_ticker})")
    
    # Run analysis
    analysis_results = get_value_investing_signals(
        portfolio_data, 
        filtered_api_data, 
        openai_client, 
        anthropic_client, 
        model
    )
    
    # Print results for debugging
    print("\nAnalysis Results Structure:")
    print(f"Type: {type(analysis_results)}")
    if isinstance(analysis_results, dict):
        print(f"Keys: {analysis_results.keys()}")
    
        if 'stocks' in analysis_results:
            print(f"\nNumber of analyzed stocks: {len(analysis_results['stocks'])}")
            
            # Detailed examination of the first stock
            if analysis_results['stocks']:
                stock = analysis_results['stocks'][0]
                print(f"\nStock Analysis for {stock.get('name', 'Unknown')} ({stock.get('ticker', 'Unknown')}):")
                print(f"Recommendation: {stock.get('recommendation', 'N/A')}")
                print(f"Summary: {stock.get('summary', 'None')[:100]}..." if stock.get('summary') else "No summary")
                print(f"Strengths: {stock.get('strengths', [])}")
                print(f"Weaknesses: {stock.get('weaknesses', [])}")
                print(f"Rationale available: {'Yes' if stock.get('rationale') else 'No'}")
    
    # Save the markdown analysis
    model_short_name = "openai" if model == "o3-mini" else "claude"
    test_output_file = f"data/processed/test_analysis_{model_short_name}.md"
    
    if isinstance(analysis_results, dict) and 'markdown' in analysis_results:
        save_markdown(analysis_results["markdown"], test_output_file)
        print(f"\nSaved markdown analysis to {test_output_file}")
    
    # Save the individual company markdown
    ticker_filename = test_ticker.replace('.', '_')
    model_companies_dir = os.path.join("data/processed/companies", model_short_name)
    os.makedirs(model_companies_dir, exist_ok=True)
    company_file = os.path.join(model_companies_dir, f"{ticker_filename}.md")
    
    print(f"\nCompany analysis file should be at: {company_file}")
    if os.path.exists(company_file):
        print(f"Company file exists with size: {os.path.getsize(company_file)} bytes")
        
        # Read the first few lines to verify content
        with open(company_file, 'r') as f:
            preview = "".join(f.readlines()[:10])
        print(f"\nPreview of company file:\n{preview}...")
    else:
        print("Company file was not created!")
    
    print("FINISHED: Single Stock Analysis Test")

if __name__ == "__main__":
    main() 