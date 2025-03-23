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
- Optimizes portfolio allocation based on analysis results

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
   - Skip optimization: python portfolio_analyzer.py --skip-optimization
3. Review the generated analysis in data/processed/portfolio_analysis.md
4. Review optimization recommendations in data/processed/portfolio_optimization.md
"""

import os
import sys
import argparse
import datetime
import time
from dotenv import load_dotenv

# Update imports to use the new module structure
from src.core.logger import logger
from src.core.config import config
from src.core.portfolio import parse_portfolio
from src.tools.api import fetch_all_companies
from src.models.analysis import create_openai_client, create_anthropic_client, get_value_investing_signals
from src.core.file_operations import save_json_data, save_markdown
from src.tools.changelog import add_analysis_run_to_changelog, add_changelog_entry
from src.core.portfolio_optimizer import parse_portfolio_csv, map_portfolio_to_analysis, optimize_portfolio, format_optimization_to_markdown

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
    parser.add_argument("--skip-optimization", action="store_true", help="Skip portfolio optimization step")
    return parser.parse_args()

def main():
    """Main function to analyze a portfolio."""
    print("STARTING: Portfolio Analyzer")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print()
    
    # Record the start time
    start_time = datetime.datetime.now()
    
    # Parse command line arguments
    args = parse_args()
    
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
    
    try:
        analysis_results = get_value_investing_signals(portfolio_data, api_data, openai_client, anthropic_client, model)
        
        # Print debugging information
        print(f"\nAnalysis results structure: {type(analysis_results)}")
        if isinstance(analysis_results, dict):
            print(f"Analysis results keys: {analysis_results.keys()}")
            if 'stocks' in analysis_results:
                print(f"Number of analyzed stocks: {len(analysis_results['stocks'])}")
                if analysis_results['stocks']:
                    print(f"Example stock data keys: {analysis_results['stocks'][0].keys()}")
        
        # Save analysis to file with model name in filename
        model_short_name = "openai" if model == "o3-mini" else "claude"
        output_file_base = os.path.splitext(config["output"]["analysis_file"])[0]  # Remove extension
        output_file = f"{output_file_base}_{model_short_name}.md"
        
        print(f"Saving analysis to {output_file}...")
        
        if isinstance(analysis_results, dict) and 'markdown' in analysis_results:
            save_markdown(analysis_results["markdown"], output_file)
            logger.info(f"Analysis saved to {output_file}")
            print(f"Analysis saved to {output_file}")
        else:
            # Fallback for backward compatibility
            print("Warning: Analysis results not in expected format, trying to save directly...")
            save_markdown(str(analysis_results), output_file)
            logger.warning("Analysis results not in expected format, saved as string")
    except Exception as e:
        print(f"Error during analysis generation: {str(e)}")
        logger.error(f"Error during analysis generation: {str(e)}")
        import traceback
        traceback.print_exc()
        print("FINISHED: Portfolio Analyzer (with errors)")
        return
    
    # Portfolio optimization based on analysis results
    if not args.skip_optimization:
        print("\nPerforming portfolio optimization...")
        logger.info("Performing portfolio optimization...")
        
        try:
            # Parse portfolio CSV file
            csv_path = config["portfolio"]["csv_file"]
            print(f"Parsing portfolio data from CSV: {csv_path}")
            portfolio_csv_data = parse_portfolio_csv(csv_path)
            
            if portfolio_csv_data:
                # Print debugging information
                print(f"Portfolio CSV data structure: {type(portfolio_csv_data)}")
                print(f"Number of positions: {len(portfolio_csv_data['positions'])}")
                
                # Map portfolio positions to analysis results
                print("Mapping portfolio data to analysis results...")
                
                if not isinstance(analysis_results, dict) or 'stocks' not in analysis_results:
                    raise ValueError("Analysis results don't contain 'stocks' key. Cannot proceed with optimization.")
                
                mapped_positions = map_portfolio_to_analysis(portfolio_csv_data, analysis_results['stocks'])
                print(f"Mapped {len(mapped_positions)} positions to analysis results")
                
                # Generate optimization recommendations
                print("Generating optimization recommendations...")
                optimization_results = optimize_portfolio(
                    mapped_positions, 
                    total_value=portfolio_csv_data['summary'].get('Depotwert (inkl. Stückzinsen) in EUR')
                )
                
                # Format and save optimization results
                optimization_md = format_optimization_to_markdown(optimization_results, portfolio_csv_data)
                optimization_file = config["output"]["optimization_file"]
                
                print(f"Saving optimization results to {optimization_file}...")
                save_markdown(optimization_md, optimization_file)
                logger.info(f"Optimization results saved to {optimization_file}")
                print(f"Optimization results saved to {optimization_file}")
            else:
                print("Error: Failed to parse portfolio CSV data. Skipping optimization.")
                logger.error("Failed to parse portfolio CSV data. Skipping optimization.")
        except Exception as e:
            print(f"Error during portfolio optimization: {str(e)}")
            logger.error(f"Error during portfolio optimization: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("Skipping portfolio optimization because --skip-optimization flag was specified.")
        logger.info("Skipping portfolio optimization because --skip-optimization flag was specified.")
    
    # Calculate total elapsed time
    elapsed_time = (datetime.datetime.now() - start_time).total_seconds()
    
    # Add to changelog
    add_analysis_run_to_changelog(
        model=model,
        num_stocks=len(portfolio_data),
        start_time=start_time,
        elapsed_time=elapsed_time
    )
    
    print("FINISHED: Portfolio Analyzer")

if __name__ == "__main__":
    main() 