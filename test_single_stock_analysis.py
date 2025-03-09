"""
Test script to validate analysis on a single stock.

This script loads existing API data and runs the analysis on a single stock
to verify that the extraction and formatting logic works correctly.
"""

import os
import json
import argparse
import traceback
from dotenv import load_dotenv
import anthropic
import openai
from utils.logger import logger
from utils.config import load_config
from utils.analysis import get_value_investing_signals
from utils.file_operations import save_markdown

# Load configuration
config = load_config()

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
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Test single stock analysis')
    parser.add_argument('--ticker', type=str, required=True, help='Stock ticker symbol')
    parser.add_argument('--company', type=str, required=True, help='Company name')
    parser.add_argument('--model', type=str, default='claude-3-7-sonnet-20250219', help='Model to use for analysis')
    args = parser.parse_args()
    
    # Get the model name from args
    model = args.model
    print(f"Testing with model: {model}")
    
    # Initialize API clients
    openai_client = None
    anthropic_client = None
    
    # Initialize the appropriate client based on the model
    if model.startswith('claude'):
        try:
            print("Initializing Anthropic client...")
            load_dotenv()
            anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
            
            if not anthropic_api_key:
                print("Error: Anthropic API key not found in environment variables.")
                return
                
            anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        except Exception as e:
            print(f"Error initializing Anthropic client: {e}")
            print("Make sure you have set the ANTHROPIC_API_KEY environment variable.")
            return
    else:
        try:
            load_dotenv()
            openai_api_key = os.getenv("OPENAI_API_KEY")
            
            if not openai_api_key:
                print("Error: OpenAI API key not found in environment variables.")
                return
                
            openai_client = openai.OpenAI(api_key=openai_api_key)
        except Exception as e:
            print(f"Error initializing OpenAI client: {e}")
            print("Make sure you have set the OPENAI_API_KEY environment variable.")
            return
    
    # Load API data
    api_data = load_api_data()
    
    # Get ticker and company name from args
    ticker = args.ticker
    company_name = args.company
    
    # Run analysis
    print(f"Testing analysis for {company_name} ({ticker})")
    
    # Find the company data
    company_data = None
    for key, data in api_data.items():
        if company_name in key:
            print(f"Found API data for company name {company_name}")
            company_data = data
            break
    
    if company_data is None:
        print(f"Could not find API data for {company_name}")
        return
    
    # Run analysis
    print(f"Running analysis for {company_name} ({ticker})")
    
    # Create a stock object with the necessary fields
    stock = {
        'ticker': ticker,
        'name': company_name,
        'data': company_data
    }
    
    # Run analysis
    analysis_results = analyze_stock(stock, model=model, openai_client=openai_client, anthropic_client=anthropic_client)
    
    # Print results
    print(f"\nAnalysis Results Structure:")
    print(f"Type: {type(analysis_results)}")
    
    if isinstance(analysis_results, dict):
        print(f"Keys: {list(analysis_results.keys())}")
        
        if 'stocks' in analysis_results:
            print(f"\nNumber of analyzed stocks: {len(analysis_results['stocks'])}")
        
        # Save markdown to file
        if 'markdown' in analysis_results:
            output_file = "data/processed/test_analysis_claude.md"
            with open(output_file, 'w') as f:
                f.write(analysis_results['markdown'])
            print(f"\nSaved markdown analysis to {output_file}")
    
    # Check if the company file was created
    company_file = f"data/processed/companies/claude/{ticker}.md"
    print(f"\nCompany analysis file should be at: {company_file}")
    
    if os.path.exists(company_file):
        file_size = os.path.getsize(company_file)
        print(f"Company file exists with size: {file_size} bytes")
        
        # Print a preview of the file
        print("\nPreview of company file:")
        with open(company_file, 'r') as f:
            content = f.read()
            print(content[:500])  # Print first 500 characters
    else:
        print("Company file does not exist.")
    
    print("\nFINISHED: Single Stock Analysis Test")

def load_api_data():
    """Load API data from file."""
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
            if isinstance(api_data[key], dict):
                print(f"Key '{key}' contains data dict")
        
        return api_data
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading API data: {e}")
        return {}

def analyze_stock(stock, model, openai_client=None, anthropic_client=None):
    """Analyze a single stock."""
    try:
        # Create minimal portfolio data for a single stock
        portfolio_data = [
            {
                "name": stock['name'],
                "shares": 100,
                "current_price": 400.0,
                "market_value": 40000.0,
                "weight": 10.0
            }
        ]
        
        # Create filtered API data
        filtered_api_data = {
            stock['ticker']: stock['data']
        }
        
        # Run analysis
        analysis_results = get_value_investing_signals(
            portfolio_data, 
            filtered_api_data, 
            openai_client, 
            anthropic_client, 
            model
        )
        
        return analysis_results
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
        traceback.print_exc()
        return {"markdown": f"Error: {str(e)}", "stocks": []}

if __name__ == "__main__":
    main() 