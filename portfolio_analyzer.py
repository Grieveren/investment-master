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
    parser.add_argument("--model", type=str, help="AI model to use (o3-mini or claude-3-7)")
    return parser.parse_args()

def main():
    """Main function to analyze a portfolio."""
    parser = argparse.ArgumentParser(description="Analyze a portfolio of stocks from a value investing perspective")
    parser.add_argument("--data-only", action="store_true", help="Only fetch and save data, skip analysis")
    parser.add_argument("--model", type=str, help="AI model to use (o3-mini or claude-3-7)")
    args = parser.parse_args()
    
    # Print startup banner
    print("STARTING: Portfolio Analyzer")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    
    if args.data_only:
        print("\nRunning in DATA-ONLY mode (will not run analysis)")
    
    # Load environment variables from .env file
    print("\nLoading environment variables...")
    load_dotenv()
    print("Environment variables loaded")
    
    # Check if API tokens are available
    sws_token = os.getenv("SWS_API_TOKEN")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    print(f"SWS API Token available: {bool(sws_token)}")
    print(f"OpenAI API Key available: {bool(openai_api_key)}")
    print(f"Anthropic API Key available: {bool(anthropic_api_key)}")
    
    # Mask API keys for logging
    if openai_api_key:
        masked_openai_key = f"{openai_api_key[:7]}...{openai_api_key[-4:]}"
        logger.info(f"OpenAI API Key: {masked_openai_key}")
    
    if anthropic_api_key:
        masked_anthropic_key = f"{anthropic_api_key[:7]}...{anthropic_api_key[-4:]}"
        logger.info(f"Anthropic API Key: {masked_anthropic_key}")
    
    # Determine which model to use
    model = args.model if args.model else "o3-mini"
    
    # For backward compatibility, handle old --model openai_o3
    if model == "openai_o3":
        model = "o3-mini"
    
    # Determine specific model name based on config
    if model.startswith("claude"):
        model_name = config["claude"]["model"]
    else:
        model_name = config["openai"]["model"]
    
    print(f"Selected AI model: {model_name}")
    logger.info(f"Selected AI model: {model_name}")
    
    # Ensure required directories exist
    ensure_directories_exist()
    
    # Parse portfolio data
    print("Parsing portfolio data...")
    logger.info(f"Parsing portfolio data from {config['api']['portfolio_file']}...")
    portfolio_data = parse_portfolio()
    logger.info(f"Found {len(portfolio_data)} stocks in portfolio.")
    print(f"Found {len(portfolio_data)} stocks in portfolio.")
    
    # Fetch data from SimplyWall.st API
    print("Fetching data from SimplyWall.st API...")
    logger.info("Fetching data from SimplyWall.st API...")
    api_data = fetch_all_companies(portfolio_data, sws_token)
    
    # Save raw API data
    data_file = config["output"]["raw_data_file"]
    print(f"Saving raw API data to {data_file}...")
    save_json_data(api_data, data_file)
    logger.info(f"Data saved to {data_file}")
    print(f"Raw API data saved to {data_file}")
    logger.info(f"Raw API data saved to {data_file}")
    
    if args.data_only:
        print("Skipping analysis because --data-only flag was specified.")
        logger.info("Skipping analysis because --data-only flag was specified.")
        logger.info(f"Raw API data has been saved to {data_file} for manual analysis.")
        print(f"Raw API data has been saved to {data_file} for manual analysis.")
        print("FINISHED: Portfolio Analyzer")
        return
    
    # Initialize AI clients
    openai_client = None
    anthropic_client = None
    
    if model.startswith("claude"):
        anthropic_client = create_anthropic_client(anthropic_api_key)
        if not anthropic_client:
            print("Error: Failed to initialize Anthropic client. Check your API key.")
            logger.error("Failed to initialize Anthropic client")
            return
    else:
        openai_client = create_openai_client(openai_api_key)
        if not openai_client:
            print("Error: Failed to initialize OpenAI client. Check your API key.")
            logger.error("Failed to initialize OpenAI client")
            return
    
    # Generate analysis
    print("Generating value investing analysis...")
    logger.info("Generating value investing analysis...")
    analysis = get_value_investing_signals(portfolio_data, api_data, openai_client, anthropic_client, model)
    
    # Save analysis to file
    output_file = config["output"]["analysis_file"]
    print(f"Saving analysis to {output_file}...")
    save_markdown(analysis, output_file)
    logger.info(f"Analysis saved to {output_file}")
    print(f"Analysis saved to {output_file}")
    
    print("FINISHED: Portfolio Analyzer")

if __name__ == "__main__":
    main() 