"""
Portfolio Analyzer - Value Investing Analysis Tool

This script analyzes a portfolio of stocks using financial data from SimplyWall.st
and generates a value investing analysis using either OpenAI's o3-mini model or
Anthropic's Claude model with extended thinking.

Features:
- Parses portfolio data from a markdown file
- Fetches detailed financial data from SimplyWall.st GraphQL API
- Processes ALL statements data (166 per company) for comprehensive analysis
- Leverages AI models (OpenAI or Claude) with large context windows for analysis
- Generates buy/sell/hold recommendations with rationales
- Saves raw API data and analysis results to files

Note: This script analyzes each stock individually, which takes approximately 15-20 seconds
per stock. For a portfolio of 11 stocks, the total analysis time will be 3-4 minutes.
Progress indicators will show which stock is being analyzed and the results as they complete.

Requirements:
- Python 3.6+
- SimplyWall.st API token
- OpenAI API key or Anthropic API key (depending on selected model)

Usage:
1. Create a .env file with your API keys
2. Run the script: 
   - Full analysis: python portfolio_analyzer.py
   - Data fetch only: python portfolio_analyzer.py --data-only
   - Select model: python portfolio_analyzer.py --model [o3-mini|claude-3-7]
3. Review the generated analysis in data/processed/portfolio_analysis.md
"""

import os
import sys
import argparse
from dotenv import load_dotenv
from utils.logger import logger
from utils.config import config
from utils.portfolio import parse_portfolio
from utils.api import fetch_all_companies
from utils.analysis import create_openai_client, create_anthropic_client, get_value_investing_signals
from utils.file_operations import save_json_data, save_markdown

def ensure_directories_exist():
    """Ensure all required directories exist."""
    directories = [
        "data",
        "data/raw",
        "data/processed",
        "logs"
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            print(f"Creating directory: {directory}")
            os.makedirs(directory, exist_ok=True)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Analyze a portfolio of stocks from a value investing perspective")
    parser.add_argument("--data-only", action="store_true", help="Only fetch and save data, skip analysis")
    parser.add_argument("--model", type=str, default=None, help="AI model to use (o3-mini or claude-3-7)")
    return parser.parse_args()

def main():
    """Main function."""
    # Parse command line arguments
    args = parse_args()
    
    # Ensure directories exist first
    ensure_directories_exist()
    
    # Add debug print statements
    print("STARTING: Portfolio Analyzer")
    print("Working directory:", os.getcwd())
    print("Python version:", sys.version)
    
    if args.data_only:
        print("\nRunning in DATA-ONLY mode (will not run analysis)")
    else:
        print("\nNote: Analysis will take approximately 15-20 seconds per stock.")
        print("      Progress indicators will be shown during analysis.")
    print()
    
    # Load environment variables
    print("Loading environment variables...")
    load_dotenv()
    print("Environment variables loaded")
    
    # Get API tokens
    sws_api_token = os.getenv("SWS_API_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Print debug info
    print(f"SWS API Token available: {bool(sws_api_token)}")
    print(f"OpenAI API Key available: {bool(openai_api_key)}")
    print(f"Anthropic API Key available: {bool(anthropic_api_key)}")
    logger.info(f"OpenAI API Key: {openai_api_key[:8]}...{openai_api_key[-4:] if openai_api_key else 'None'}")
    logger.info(f"Anthropic API Key: {anthropic_api_key[:8]}...{anthropic_api_key[-4:] if anthropic_api_key else 'None'}")
    
    # Check API token
    if not sws_api_token:
        logger.error("Error: SimplyWall.st API token not found. Please add it to your .env file.")
        return
    
    # Determine which model to use
    if args.model:
        selected_model = args.model
    else:
        selected_model = config["openai"]["model"]
    
    is_claude = selected_model.startswith("claude")
    
    # If using Claude, make sure we're using the full model name from config
    if is_claude and selected_model == "claude-3-7":
        selected_model = config["claude"]["model"]
        
    print(f"Selected AI model: {selected_model}")
    logger.info(f"Selected AI model: {selected_model}")
    
    # Check API keys based on selected model
    if not args.data_only:
        if is_claude:
            # Checking Claude API key
            if not anthropic_api_key:
                logger.warning("Warning: Anthropic API key not found. Will save raw data but cannot generate analysis.")
                api_key_valid = False
            elif anthropic_api_key.startswith("your_"):
                logger.warning("Warning: Anthropic API key appears to be a placeholder. Please update it with a real key.")
                logger.warning("Will continue to fetch data but analysis may not be available.")
                api_key_valid = False
            else:
                api_key_valid = True
                logger.info("API key found. Will attempt to generate analysis.")
        else:
            # Checking OpenAI API key
            if not openai_api_key:
                logger.warning("Warning: OpenAI API key not found. Will save raw data but cannot generate analysis.")
                api_key_valid = False
            elif openai_api_key.startswith("your_"):
                logger.warning("Warning: OpenAI API key appears to be a placeholder. Please update it with a real key.")
                logger.warning("Will continue to fetch data but analysis may not be available.")
                api_key_valid = False
            else:
                api_key_valid = True
                logger.info("API key found. Will attempt to generate analysis.")
    else:
        api_key_valid = False  # Not needed in data-only mode
        
    # Create AI client based on selected model
    client = None
    if not args.data_only and api_key_valid:
        if is_claude:
            # Create Anthropic client
            print("Creating Anthropic client...")
            try:
                import anthropic
                client = create_anthropic_client(anthropic_api_key)
                print(f"Anthropic client created: {client is not None}")
            except ImportError:
                logger.error("Anthropic Python package not installed. Install with 'pip install anthropic'")
                print("Error: Anthropic Python package not installed. Install with 'pip install anthropic'")
                api_key_valid = False
        else:
            # Create OpenAI client
            print("Creating OpenAI client...")
            client = create_openai_client(openai_api_key)
            print(f"OpenAI client created: {client is not None}")
            
        if client is None:
            api_key_valid = False
            logger.warning("Failed to create API client. Will save raw data but cannot generate analysis.")
    
    # Parse portfolio data from text file
    print("Parsing portfolio data...")
    portfolio_file = config["api"]["portfolio_file"]
    logger.info(f"Parsing portfolio data from {portfolio_file}...")
    stocks = parse_portfolio(portfolio_file)
    
    if not stocks:
        logger.error(f"Error: No stocks found in {portfolio_file}. Please check the file format.")
        return
    
    logger.info(f"Found {len(stocks)} stocks in portfolio.")
    print(f"Found {len(stocks)} stocks in portfolio.")
    
    # Fetch data from API
    print("Fetching data from SimplyWall.st API...")
    logger.info("Fetching data from SimplyWall.st API...")
    api_data = fetch_all_companies(stocks, sws_api_token)
    
    # Save API responses to file
    raw_data_file = config["output"]["raw_data_file"]
    print(f"Saving raw API data to {raw_data_file}...")
    save_result = save_json_data(api_data, raw_data_file)
    
    if save_result:
        print(f"Raw API data saved to {raw_data_file}")
        logger.info(f"Raw API data saved to {raw_data_file}")
    else:
        print(f"Error saving raw API data to {raw_data_file}")
        logger.error(f"Error saving raw API data to {raw_data_file}")
    
    # Get value investing signals
    if not args.data_only and api_key_valid and client is not None:
        print(f"Analyzing stocks using {'Claude' if is_claude else 'OpenAI'} {selected_model}...")
        logger.info(f"Analyzing stocks for value investing signals using {'Claude' if is_claude else 'OpenAI'} {selected_model} model...")
        signals = get_value_investing_signals(stocks, api_data, client, selected_model)
        
        # Print results
        print("=== VALUE INVESTING ANALYSIS COMPLETE ===")
        logger.info("=== VALUE INVESTING ANALYSIS COMPLETE ===")
        logger.info("Analysis has been generated for all stocks in your portfolio.")
        
        # Save results to file
        analysis_file = config["output"]["analysis_file"]
        print(f"Saving analysis to {analysis_file}...")
        save_result = save_markdown(signals, analysis_file)
        
        if save_result:
            print(f"Analysis complete! Results saved to {analysis_file}")
            logger.info(f"Analysis complete! Results saved to {analysis_file}")
        else:
            print(f"Error saving analysis results to {analysis_file}")
            logger.error(f"Error saving analysis results to {analysis_file}")
    else:
        if args.data_only:
            print("Skipping analysis because --data-only flag was specified.")
            logger.info("Skipping analysis because --data-only flag was specified.")
        else:
            print("Skipping analysis because API key is not valid or missing.")
            logger.warning("Skipping analysis because API key is not valid or missing.")
            logger.warning("You can add your API key to the .env file and run the script again.")
        
        logger.info(f"Raw API data has been saved to {config['output']['raw_data_file']} for manual analysis.")
        print(f"Raw API data has been saved to {raw_data_file} for manual analysis.")
    
    print("FINISHED: Portfolio Analyzer")
    
if __name__ == "__main__":
    main() 