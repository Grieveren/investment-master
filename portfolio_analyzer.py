"""
Portfolio Analyzer - Value Investing Analysis Tool

This script analyzes a portfolio of stocks using financial data from SimplyWall.st
and generates a value investing analysis using OpenAI's o3-mini model.

Features:
- Parses portfolio data from a markdown file
- Fetches detailed financial data from SimplyWall.st GraphQL API
- Processes ALL statements data (166 per company) for comprehensive analysis
- Leverages OpenAI's o3-mini model (200K token context window) for analysis
- Generates buy/sell/hold recommendations with rationales
- Saves raw API data and analysis results to files

Note: This script analyzes each stock individually, which takes approximately 15-20 seconds
per stock. For a portfolio of 11 stocks, the total analysis time will be 3-4 minutes.
Progress indicators will show which stock is being analyzed and the results as they complete.

Requirements:
- Python 3.6+
- SimplyWall.st API token
- OpenAI API key

Usage:
1. Create a .env file with your API keys
2. Run the script: 
   - Full analysis: python portfolio_analyzer.py
   - Data fetch only: python portfolio_analyzer.py --data-only
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
from utils.analysis import create_openai_client, get_value_investing_signals
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
    parser = argparse.ArgumentParser(description='Portfolio Analyzer')
    parser.add_argument('--data-only', action='store_true', 
                        help='Only fetch data, skip analysis')
    parser.add_argument('--model', type=str, choices=['o3-mini', 'claude-3-7'],
                        help='Select AI model for analysis: o3-mini (default) or claude-3-7')
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
    
    # Print debug info
    print(f"SWS API Token available: {bool(sws_api_token)}")
    print(f"OpenAI API Key available: {bool(openai_api_key)}")
    logger.info(f"OpenAI API Key: {openai_api_key[:8]}...{openai_api_key[-4:] if openai_api_key else 'None'}")
    
    # Check API token
    if not sws_api_token:
        logger.error("Error: SimplyWall.st API token not found. Please add it to your .env file.")
        return
    
    # Set the model based on args or default
    selected_model = args.model if args.model else config["openai"]["default_model"]
    if selected_model not in config["openai"]["models"]:
        logger.warning(f"Invalid model selection: {selected_model}. Using default model.")
        selected_model = config["openai"]["default_model"]
    
    print(f"Selected AI model: {selected_model}")
    logger.info(f"Selected AI model: {selected_model}")
    
    # Check OpenAI API key
    openai_available = False
    if not args.data_only:  # Only check if we're doing analysis
        if not openai_api_key:
            logger.warning("Warning: OpenAI API key not found. Will save raw data but cannot generate analysis.")
        elif openai_api_key.startswith("your_"):
            logger.warning("Warning: OpenAI API key appears to be a placeholder. Please update it with a real key.")
            logger.warning("Will continue to fetch data but analysis may not be available.")
        else:
            openai_available = True
            logger.info("OpenAI API key found. Will attempt to generate analysis.")
    
    # Create OpenAI client
    openai_client = None
    if not args.data_only and openai_available:
        print("Creating OpenAI client...")
        openai_client = create_openai_client(openai_api_key)
        print(f"OpenAI client created: {openai_client is not None}")
    
    # Parse portfolio data
    print("Parsing portfolio data...")
    logger.info("Parsing portfolio data...")
    stocks = parse_portfolio()
    print(f"Found {len(stocks)} stocks in portfolio.")
    logger.info(f"Found {len(stocks)} stocks in portfolio.")
    
    # Fetch data from SimplyWall.st API
    print("Fetching data from SimplyWall.st API...")
    logger.info("Fetching data from SimplyWall.st API...")
    api_data = fetch_all_companies(stocks, sws_api_token)
    print(f"Fetched data for {len(api_data)} stocks.")
    
    # Save raw API data
    print("Saving raw API data...")
    logger.info("Saving raw API data...")
    raw_data_file = config["output"]["raw_data_file"]
    print(f"Raw data file path: {raw_data_file}")
    save_result = save_json_data(api_data, raw_data_file)
    print(f"Raw data saved: {save_result}")
    
    # Get value investing signals
    if not args.data_only and openai_available and openai_client is not None:
        model_config = config["openai"]["models"][selected_model]
        model_name = model_config["name"]
        reasoning_effort = model_config["reasoning_effort"]
        print(f"Analyzing stocks using {model_name} with {reasoning_effort} reasoning effort...")
        logger.info(f"Analyzing stocks for value investing signals using {model_name} (individual stock approach)...")
        signals = get_value_investing_signals(stocks, api_data, openai_client, selected_model)
        
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
            print("Skipping analysis because OpenAI API key is not valid or missing.")
            logger.warning("Skipping analysis because OpenAI API key is not valid or missing.")
            logger.warning("You can add your OpenAI API key to the .env file and run the script again.")
        
        logger.info(f"Raw API data has been saved to {config['output']['raw_data_file']} for manual analysis.")
        print(f"Raw API data has been saved to {raw_data_file} for manual analysis.")
    
    print("FINISHED: Portfolio Analyzer")

if __name__ == "__main__":
    main() 