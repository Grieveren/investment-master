"""
Analysis module for generating stock analyses using OpenAI and Anthropic Claude.

This module coordinates the end-to-end analysis of stocks using AI models,
leveraging specialized modules for specific functionalities.
"""

import os
import json
import datetime
import time
from src.core.logger import logger
from src.core.config import config
from src.core.file_operations import save_markdown, save_json_data
from src.core.portfolio import get_stock_ticker_and_exchange

# Import specialized modules
from src.models.clients import create_openai_client, create_anthropic_client
from src.models.openai.openai_analysis import analyze_with_openai
from src.models.claude.claude_analysis import analyze_with_claude
from src.models.prompts import build_analysis_prompt, get_openai_system_prompt
from src.models.parsers import extract_analysis_components, format_analysis_to_markdown

def get_value_investing_signals(portfolio_data, api_data, openai_client=None, anthropic_client=None, model="o3-mini"):
    """Use AI models to analyze stocks and provide buy/sell signals.
    
    This function processes each stock individually and combines the results,
    ensuring every stock gets fully analyzed without context window limitations.
    
    Args:
        portfolio_data (list): List of stock dictionaries with name, shares, price, etc.
        api_data (dict): Dictionary of API responses from SimplyWall.st
        openai_client (OpenAI, optional): OpenAI client for o3-mini model.
        anthropic_client (Anthropic, optional): Anthropic client for Claude model.
        model (str): Model to use - either "o3-mini" or "claude-3-7"
        
    Returns:
        dict: Dictionary containing the markdown analysis and structured stock results
    """
    model_short_name = "openai" if model == "o3-mini" else "claude"
    logger.info(f"Starting value investing analysis using {model} model")
    
    if model.startswith("claude"):
        thinking_budget = config["claude"].get("thinking_budget", 32000)
        logger.info(f"Using Claude with enhanced analysis mode and {thinking_budget} token thinking budget")
        print(f"Enhanced Analysis Mode: Using Claude with {thinking_budget} token thinking budget")
        print("This will provide more comprehensive and nuanced analysis, but may take longer per company")
        print("Streaming enabled - you'll see real-time progress updates during analysis")
    
    stock_analyses = []
    analysis_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Create output directory for individual company analyses
    model_companies_dir = os.path.join(config["output"]["companies_dir"], model_short_name)
    os.makedirs(model_companies_dir, exist_ok=True)
    
    for stock in portfolio_data:
        ticker = None
        try:
            name = stock.get('name', 'Unknown')
            ticker_info = get_stock_ticker_and_exchange(name)
            
            if not ticker_info:
                logger.warning(f"No ticker info found for {name}")
                continue
            
            ticker = ticker_info.get('ticker')
            exchange = ticker_info.get('exchange')
            
            # Get API data for this company - try different possible keys
            company_data = None
            
            # Try by ticker first
            if ticker in api_data:
                company_data = api_data[ticker]
                logger.info(f"Found API data for ticker {ticker}")
            # Then try by name
            elif name in api_data:
                company_data = api_data[name]
                logger.info(f"Found API data for company name {name}")
            # Try similar name variations
            else:
                for key in api_data.keys():
                    if name.lower() in key.lower() or ticker.lower() in key.lower():
                        company_data = api_data[key]
                        logger.info(f"Found API data for similar key: {key}")
                        break
            
            if not company_data:
                logger.warning(f"No API data found for {name} ({ticker})")
                continue
            
            # Add ticker and name to company data for reference if not already present
            if 'ticker' not in company_data:
                company_data['ticker'] = ticker
            if 'name' not in company_data:
                company_data['name'] = name
            
            print(f"Analyzing {name} ({ticker})...")
            
            # Create the user prompt with all available financial data
            logger.info(f"Building comprehensive analysis prompt for {ticker}")
            user_prompt = build_analysis_prompt(company_data)
            
            # Show prompt size to monitor token usage
            prompt_size = len(user_prompt)
            logger.info(f"Analysis prompt for {ticker} created: {prompt_size} characters")
            
            start_time = time.time()
            
            if model.startswith("claude"):
                # Use Claude with enhanced analysis
                logger.info(f"Starting enhanced Claude analysis for {ticker}")
                print(f"  - Using enhanced analysis with full data and extended thinking time")
                response = analyze_with_claude(user_prompt, anthropic_client, model=config["claude"]["model"])
            else:
                # Use OpenAI for analysis
                logger.info(f"Starting OpenAI analysis for {ticker}")
                system_prompt = get_openai_system_prompt()
                response = analyze_with_openai(system_prompt, user_prompt, openai_client, model=config["openai"]["model"])
            
            elapsed_time = time.time() - start_time
            logger.info(f"Analysis completed for {ticker} in {elapsed_time:.1f}s, response size: {len(response)} characters")
            print(f"  - Analysis completed in {elapsed_time:.1f} seconds")
            
            # Extract analysis components (recommendation, strengths, weaknesses, etc.)
            analysis_data = extract_analysis_components(response)
            
            # Add ticker and name 
            analysis_data['ticker'] = ticker
            analysis_data['name'] = name
            analysis_data['date'] = analysis_date
            
            # Log the recommendation
            recommendation = analysis_data.get('recommendation', 'UNKNOWN')
            logger.info(f"Recommendation for {ticker}: {recommendation}")
            print(f"  - Recommendation: {recommendation}")
            
            # Add to the results list
            stock_analyses.append(analysis_data)
            
            # Save individual company analysis to file
            company_filename = f"{ticker.replace('.', '_')}_analysis.md"
            company_file_path = os.path.join(model_companies_dir, company_filename)
            save_markdown(response, company_file_path)
            logger.info(f"Saved {ticker} analysis to {company_file_path}")
            
            # Save JSON data for later use
            json_filename = f"{ticker.replace('.', '_')}_analysis.json"
            json_file_path = os.path.join(model_companies_dir, json_filename)
            save_json_data(analysis_data, json_file_path)
            logger.info(f"Saved {ticker} structured data to {json_file_path}")
            
            # Add a small delay between companies to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error analyzing {name} ({ticker}): {e}")
            print(f"Error analyzing {name}: {e}")
    
    # Format all analyses into a summary markdown document
    markdown_content = format_analysis_to_markdown(stock_analyses)
    
    return {
        "markdown": markdown_content, 
        "stocks": stock_analyses
    } 