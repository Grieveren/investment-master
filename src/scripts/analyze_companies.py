#!/usr/bin/env python
"""
Script to analyze all companies in portfolio using previously fetched API data.
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
    """Main function to analyze all companies."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Analyze all companies using SimplyWall.st data")
    parser.add_argument("--model", default="claude-3-7", help="AI model to use for analysis")
    args = parser.parse_args()
    
    model = args.model
    
    start_time = time.time()
    
    print("STARTING: Portfolio Companies Analyzer")
    print(f"Working directory: {os.getcwd()}")
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
            company_count = len(api_data)
            print(f"Loaded API data for {company_count} companies from {api_data_file}")
    except Exception as e:
        logger.error(f"Error loading API data: {e}")
        print(f"ERROR: Failed to load API data: {e}")
        return 1
    
    # Create output directory
    output_dir = "data/processed"
    os.makedirs(output_dir, exist_ok=True)
    
    # Run analysis for all companies
    print(f"\nAnalyzing {company_count} companies...")
    logger.info(f"Starting analysis for {company_count} companies using {model} model")
    
    success_count = 0
    failure_count = 0
    failed_companies = []
    
    for i, (company_name, company_data) in enumerate(api_data.items(), 1):
        print(f"\n[{i}/{company_count}] Analyzing {company_name}...")
        logger.info(f"Starting analysis for {company_name}")
        
        try:
            # Analyze the company
            analysis = analyze_company_value(company_name, company_data, model)
            
            # Save analysis to file
            analysis_file = os.path.join(output_dir, f"{company_name}_analysis.md")
            with open(analysis_file, "w") as f:
                f.write(analysis)
            
            print(f"Analysis saved to {analysis_file}")
            logger.info(f"Analysis for {company_name} saved to {analysis_file}")
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"Error analyzing {company_name}: {e}")
            print(f"ERROR: Failed to analyze {company_name}: {e}")
            failure_count += 1
            failed_companies.append(company_name)
    
    # Print summary
    print("\n=== Analysis Summary ===")
    print(f"Total companies: {company_count}")
    print(f"Successfully analyzed: {success_count}")
    print(f"Failed: {failure_count}")
    
    if failed_companies:
        print(f"Companies that failed: {', '.join(failed_companies)}")
    
    # Calculate and print execution time
    execution_time = time.time() - start_time
    print(f"\nTotal execution time: {execution_time:.2f} seconds")
    
    return 0 if failure_count == 0 else 1

if __name__ == "__main__":
    exit(main()) 