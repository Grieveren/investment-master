#!/usr/bin/env python
"""
Script to analyze a single company using previously fetched API data.
"""

import os
import json
import time
import argparse
from dotenv import load_dotenv
from src.core.logger import logger
from src.core.config import config
from src.models.company_analyzer import analyze_company_value

def main():
    """Main function to analyze a single company."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Analyze a single company using SimplyWall.st data")
    parser.add_argument("--company", required=True, help="Company name as listed in combined_portfolio.md")
    parser.add_argument("--model", default="claude-3-7", help="AI model to use for analysis")
    args = parser.parse_args()
    
    company_name = args.company
    model = args.model
    
    start_time = time.time()
    
    print("STARTING: Single Company Analyzer")
    print(f"Working directory: {os.getcwd()}")
    print(f"Analyzing company: {company_name}")
    print(f"Using model: {model}")
    
    # Load environment variables
    print("\nLoading environment variables...")
    load_dotenv()
    print("Environment variables loaded")
    
    # Check API tokens
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
    
    has_openai = bool(openai_api_key)
    has_anthropic = bool(anthropic_api_key)
    print(f"OpenAI API Key available: {has_openai}")
    print(f"Anthropic API Key available: {has_anthropic}")
    
    if "claude" in model.lower() and not has_anthropic:
        logger.error("Anthropic API key not found but Claude model specified.")
        print("ERROR: Anthropic API key not found. Please set ANTHROPIC_API_KEY environment variable.")
        return 1
    
    if "gpt" in model.lower() and not has_openai:
        logger.error("OpenAI API key not found but GPT model specified.")
        print("ERROR: OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        return 1
    
    # Load API data
    print("\nLoading API data...")
    api_data_file = "data/raw/api_data.json"
    
    try:
        with open(api_data_file, "r") as f:
            api_data = json.load(f)
            print(f"Loaded API data from {api_data_file}")
    except Exception as e:
        logger.error(f"Error loading API data: {e}")
        print(f"ERROR: Failed to load API data: {e}")
        return 1
    
    # Check if company exists in API data
    if company_name not in api_data:
        logger.error(f"Company '{company_name}' not found in API data.")
        print(f"ERROR: Company '{company_name}' not found in API data.")
        print(f"Available companies: {', '.join(api_data.keys())}")
        return 1
    
    # Run analysis
    print(f"\nAnalyzing {company_name}...")
    logger.info(f"Starting analysis for {company_name} using {model} model")
    
    try:
        company_data = api_data[company_name]
        output_dir = "data/processed"
        os.makedirs(output_dir, exist_ok=True)
        
        # Analyze the company
        analysis = analyze_company_value(company_name, company_data, model)
        
        # Save analysis to file
        analysis_file = os.path.join(output_dir, f"{company_name}_analysis.md")
        with open(analysis_file, "w") as f:
            f.write(analysis)
        
        print(f"Analysis saved to {analysis_file}")
        logger.info(f"Analysis for {company_name} saved to {analysis_file}")
        
    except Exception as e:
        logger.error(f"Error analyzing {company_name}: {e}")
        print(f"ERROR: Failed to analyze {company_name}: {e}")
        return 1
    
    # Calculate and print execution time
    execution_time = time.time() - start_time
    print(f"\nTotal execution time: {execution_time:.2f} seconds")
    
    return 0

if __name__ == "__main__":
    exit(main()) 