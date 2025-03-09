"""
Claude Portfolio Optimizer - Holistic Portfolio Optimization

This script provides a holistic portfolio optimization approach by sending:
1. Complete portfolio data
2. All individual stock analyses
3. Current allocations and performance

to Claude for comprehensive analysis and detailed recommendations with rationales.

Features:
- Collects all individual stock analyses from data/processed/companies/claude
- Loads current portfolio allocation data from CSV
- Creates a single, comprehensive prompt that gives Claude the full context
- Gets detailed portfolio optimization recommendations with specific rationales
- Includes specific buy/sell recommendations with amounts and reasoning

Requirements:
- Python 3.6+
- Anthropic API key
- Previously generated stock analyses from Claude

Usage:
python claude_portfolio_optimizer.py
"""

import os
import sys
import glob
import json
import datetime
import time
import re
import traceback
from dotenv import load_dotenv
import anthropic

from utils.logger import logger
from utils.config import config
from utils.portfolio_optimizer import parse_portfolio_csv
from utils.file_operations import save_markdown


def create_anthropic_client(api_key):
    """Create an Anthropic client.
    
    Args:
        api_key (str): Anthropic API key.
        
    Returns:
        Anthropic client instance or None if creation fails.
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        logger.info("Successfully created Anthropic client")
        return client
    except Exception as e:
        logger.error(f"Error creating Anthropic client: {e}")
        return None


def read_company_analyses():
    """Read all company analyses from the Claude output directory.
    
    Returns:
        dict: Dictionary mapping tickers to their analysis content.
    """
    analyses = {}
    model_companies_dir = os.path.join(config["output"]["companies_dir"], "claude")
    
    if not os.path.exists(model_companies_dir):
        logger.error(f"Company analyses directory not found: {model_companies_dir}")
        return analyses
    
    company_files = glob.glob(os.path.join(model_companies_dir, "*.md"))
    logger.info(f"Found {len(company_files)} company analysis files.")
    
    for file_path in company_files:
        ticker = os.path.basename(file_path).replace(".md", "")
        # Handle tickers with underscores that should be periods (like BRK_B → BRK.B)
        ticker = ticker.replace("_", ".")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            analyses[ticker] = content
            logger.debug(f"Loaded analysis for {ticker}")
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
    
    return analyses


def create_claude_portfolio_prompt(portfolio_data, analyses):
    """Create a comprehensive prompt for Claude with portfolio data and analyses.
    
    Args:
        portfolio_data (dict): Portfolio data from parse_portfolio_csv.
        analyses (dict): Dictionary mapping tickers to their analysis content.
        
    Returns:
        str: Complete prompt for Claude.
    """
    # Start with a description of the task
    prompt = """
# Portfolio Optimization Task

## Overview
You are tasked with providing a holistic portfolio optimization recommendation based on the following:
1. Current portfolio allocation and performance data
2. Individual value investing analyses for each stock
3. Overall market conditions and portfolio diversification

Your job is to recommend specific changes to the portfolio allocation with detailed rationales.

## Current Portfolio Data

Portfolio summary:
"""
    
    # Add portfolio summary
    total_value_str = portfolio_data['summary'].get('Depotwert (inkl. Stückzinsen) in EUR', '0')
    # Convert string to float - handle European format
    try:
        # Remove any non-numeric characters except for comma and period
        cleaned_value = ''.join(c for c in total_value_str if c.isdigit() or c in ',.').strip()
        # Replace comma with period for float conversion
        cleaned_value = cleaned_value.replace('.', '').replace(',', '.')
        total_value = float(cleaned_value)
        logger.info(f"Portfolio total value: €{total_value:,.2f}")
    except (ValueError, TypeError) as e:
        logger.warning(f"Could not convert total value string: {total_value_str}, using 0. Error: {e}")
        total_value = 0.0
    
    prompt += f"- Total portfolio value: €{total_value:,.2f}\n"
    prompt += f"- Number of positions: {len(portfolio_data['positions'])}\n"
    prompt += f"- Date: {portfolio_data.get('date', datetime.datetime.now().strftime('%Y-%m-%d'))}\n\n"
    
    # Add current positions
    prompt += "## Current Positions\n\n"
    prompt += "| Position | Ticker | Current Value (€) | % of Portfolio | Purchase Value (€) | Performance | Current Price |\n"
    prompt += "|----------|--------|------------------|----------------|-------------------|-------------|---------------|\n"
    
    # Prepare data to map portfolio data to analyses
    ticker_map = {
        "ALLIANZ SE NA O.N.": "ALV",
        "ASML HOLDING    EO -,09": "ASML",
        "ADVANCED MIC.DEV.  DL-,01": "AMD",
        "ALPHABET INC.CL C DL-,001": "GOOG",
        "BERKSH. H.B NEW DL-,00333": "BRK.B",
        "CROWDSTRIKE HLD. DL-,0005": "CRWD",
        "MICROSOFT    DL-,00000625": "MSFT",
        "NUTANIX INC. A": "NTNX",
        "NVIDIA CORP.      DL-,001": "NVDA",
        "TAIWAN SEMICON.MANU.ADR/5": "TSM"
    }
    
    # Track which positions we have analyses for
    positions_with_analyses = []
    
    for position in portfolio_data['positions']:
        designation = position.get('Bezeichnung')
        if not designation:
            continue
        
        # Map to ticker
        ticker = ticker_map.get(designation)
        if not ticker:
            logger.warning(f"Could not map position {designation} to a ticker")
            continue
        
        # Get values and convert from string if needed
        # Function to safely convert values, handling both numeric and string input
        def safe_convert(value, default=0.0):
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                try:
                    # Remove non-numeric characters except digits, comma, period
                    clean_str = ''.join(c for c in value if c.isdigit() or c in ',.').strip()
                    # Convert European format (1.234,56) to standard format (1234.56)
                    clean_str = clean_str.replace('.', '').replace(',', '.')
                    return float(clean_str)
                except (ValueError, TypeError):
                    return default
            return default
        
        # Convert values using the safe conversion function
        current_value = safe_convert(position.get('Wert in EUR', 0))
        percent = safe_convert(position.get('Anteil im Depot', 0))
        purchase_value = safe_convert(position.get('Einstandswert in EUR', 0))
        current_price = safe_convert(position.get('akt. Kurs', 0))
        
        # Calculate performance
        performance = 0
        if purchase_value > 0:
            performance = ((current_value - purchase_value) / purchase_value) * 100
        
        # Add to table
        prompt += f"| {designation} | {ticker} | €{current_value:,.2f} | {percent:.2f}% | €{purchase_value:,.2f} | {performance:.2f}% | {current_price:.2f} |\n"
        
        # Track positions that have analyses
        if ticker in analyses:
            positions_with_analyses.append((ticker, designation))
        else:
            logger.warning(f"No analysis found for {ticker}")
    
    # Add individual stock analyses
    prompt += "\n## Individual Stock Analyses\n\n"
    
    for ticker, designation in positions_with_analyses:
        prompt += f"### Analysis for {designation} ({ticker})\n\n"
        
        # Add the full analysis, but use just the key sections to save space
        analysis = analyses.get(ticker, "No analysis available")
        
        # Extract just the key sections to save space
        recommendation_match = re.search(r'(?:^## |^#|^)Recommendation:?\s*(.*?)$', analysis, re.MULTILINE | re.IGNORECASE)
        recommendation = "N/A"
        if recommendation_match:
            recommendation = recommendation_match.group(1).strip()
        
        # Extract summary
        summary_match = re.search(r'(?:^## |^#|^)Summary:?\s*(.*?)(?=(?:^## |^#|$))', analysis, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        summary = "No summary available"
        if summary_match:
            summary = summary_match.group(1).strip()
        
        # Extract price analysis
        price_analysis_match = re.search(r'(?:^## |^#|^)Price Analysis:?\s*(.*?)(?=(?:^## |^#|$))', analysis, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        price_analysis = "No price analysis available"
        if price_analysis_match:
            price_analysis = price_analysis_match.group(1).strip()
        
        # Extract rationale
        rationale_match = re.search(r'(?:^## |^#|^)Investment Rationale:?\s*(.*?)(?=(?:^## |^#|$))', analysis, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        rationale = "No investment rationale available"
        if rationale_match:
            rationale = rationale_match.group(1).strip()
        
        # Add to prompt
        prompt += f"**Recommendation:** {recommendation}\n\n"
        prompt += f"**Summary:** {summary}\n\n"
        prompt += f"**Price Analysis:**\n{price_analysis}\n\n"
        prompt += f"**Investment Rationale:**\n{rationale}\n\n"
    
    # Add final optimization request
    prompt += """
## Portfolio Optimization Request

Based on the above data, please provide:

1. **Overall Analysis**: A comprehensive analysis of the current portfolio considering diversification, sector allocation, risk profile, and alignment with value investing principles.

2. **Recommended Changes**: Specific recommendations for rebalancing the portfolio, including:
   - Positions to increase (with specific amounts in euros and percentages)
   - Positions to decrease (with specific amounts in euros and percentages)
   - Positions to maintain

3. **Detailed Rationales**: For each recommended change, provide a detailed explanation of the rationale, considering:
   - Intrinsic value estimates and margin of safety
   - Growth prospects and competitive position
   - Portfolio balance considerations
   - Risk management considerations

4. **Overall Optimization Strategy**: Explain the overall portfolio optimization strategy and how it aligns with value investing principles.

Please be specific in your recommendations and provide detailed justifications for each proposed change. For example, don't just say "increase Microsoft position", but rather "increase Microsoft (MSFT) position by €X,XXX (approximately X%), because...".
"""
    
    return prompt


def get_claude_portfolio_optimization(prompt, client, model="claude-3-7-sonnet-20250219"):
    """Get portfolio optimization recommendations from Claude.
    
    Args:
        prompt (str): The comprehensive portfolio prompt.
        client (Anthropic): Anthropic client instance.
        model (str, optional): Claude model to use.
        
    Returns:
        str: Text response from Claude or error message.
    """
    try:
        # Get configuration values
        max_tokens = config["portfolio"]["claude_optimization"].get("max_tokens", 4000)
        temperature = config["portfolio"]["claude_optimization"].get("temperature", 0.1)
        
        # System prompt to clarify the task
        system_prompt = """You are a financial advisor with expertise in value investing. 
Your task is to provide comprehensive portfolio optimization recommendations based on 
the detailed portfolio data and individual stock analyses provided. Focus on providing specific, 
actionable advice with detailed rationales for each recommendation."""
        
        logger.info(f"Requesting portfolio optimization from Claude ({model})...")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
        start_time = time.time()
        
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=temperature
        )
        
        elapsed_time = time.time() - start_time
        logger.info(f"Claude portfolio optimization completed in {elapsed_time:.1f}s")
        
        return message.content[0].text
    except Exception as e:
        error_msg = f"Error getting portfolio optimization from Claude: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return f"Error getting portfolio optimization: {str(e)}"


def format_optimization_output(optimization_response, portfolio_data):
    """Format Claude's optimization response for output.
    
    Args:
        optimization_response (str): Claude's response text.
        portfolio_data (dict): Original portfolio data.
        
    Returns:
        str: Markdown-formatted optimization recommendations.
    """
    # Create a markdown document with the optimization recommendations
    markdown = "# Claude Portfolio Optimization Recommendations\n\n"
    
    # Add date information
    markdown += f"**Analysis Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    # Add portfolio summary
    markdown += "## Portfolio Summary\n\n"
    
    # Function to safely convert values, handling both numeric and string input
    def safe_convert(value, default=0.0):
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            try:
                # Remove non-numeric characters except digits, comma, period
                clean_str = ''.join(c for c in value if c.isdigit() or c in ',.').strip()
                # Convert European format (1.234,56) to standard format (1234.56)
                clean_str = clean_str.replace('.', '').replace(',', '.')
                return float(clean_str)
            except (ValueError, TypeError):
                return default
        return default
    
    # Convert total value using the safe conversion function
    total_value_str = portfolio_data['summary'].get('Depotwert (inkl. Stückzinsen) in EUR', '0')
    total_value = safe_convert(total_value_str)
    
    markdown += f"Total portfolio value: €{total_value:,.2f}\n"
    markdown += f"Total positions: {len(portfolio_data['positions'])}\n\n"
    
    # Add Claude's optimization response
    markdown += "## Recommendations\n\n"
    markdown += optimization_response
    
    # Add disclaimer
    markdown += "\n\n---\n\n"
    markdown += "**Disclaimer:** These recommendations are based on algorithmic analysis of financial data and "
    markdown += "should not be considered financial advice. All investment decisions should be made based on "
    markdown += "your own research and in consultation with a qualified financial advisor. Past performance is "
    markdown += "not indicative of future results.\n"
    
    return markdown


def ensure_directories_exist():
    """Ensure all required directories exist."""
    directories = [
        "data",
        "data/processed",
        "data/processed/companies",
        "data/processed/companies/claude",
    ]
    
    for directory in directories:
        if not os.path.exists(directory):
            logger.info(f"Creating directory: {directory}")
            os.makedirs(directory, exist_ok=True)


def main():
    """Main function to get holistic portfolio optimization from Claude."""
    try:
        logger.info("STARTING: Claude Portfolio Optimizer")
        print("STARTING: Claude Portfolio Optimizer")
        print(f"Working directory: {os.getcwd()}")
        
        # Ensure required directories exist
        ensure_directories_exist()
        
        # Load environment variables
        load_dotenv()
        
        # Get Anthropic API key
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_api_key:
            logger.error("Anthropic API key not found in environment variables.")
            print("Error: Anthropic API key not found in environment variables.")
            return
        
        # Create Anthropic client
        logger.info("Creating Anthropic client...")
        client = create_anthropic_client(anthropic_api_key)
        if not client:
            logger.error("Failed to create Anthropic client.")
            print("Error: Failed to create Anthropic client.")
            return
        
        # Read company analyses
        logger.info("Reading company analyses...")
        print("Reading company analyses...")
        analyses = read_company_analyses()
        if not analyses:
            logger.error("No company analyses found. Please run the analysis first.")
            print("No company analyses found. Please run the analysis first.")
            return
        
        logger.info(f"Successfully loaded analyses for {len(analyses)} companies")
        print(f"Successfully loaded analyses for {len(analyses)} companies")
        
        # Parse portfolio data
        csv_path = config["portfolio"]["csv_file"]
        logger.info(f"Parsing portfolio data from CSV: {csv_path}")
        print(f"Parsing portfolio data from CSV: {csv_path}")
        portfolio_data = parse_portfolio_csv(csv_path)
        if not portfolio_data:
            logger.error(f"Error parsing portfolio data from {csv_path}")
            print(f"Error parsing portfolio data from {csv_path}")
            return
        
        logger.info(f"Successfully parsed portfolio data with {len(portfolio_data['positions'])} positions")
        print(f"Successfully parsed portfolio data with {len(portfolio_data['positions'])} positions")
        
        # Create prompt for Claude
        logger.info("Creating portfolio optimization prompt...")
        print("Creating portfolio optimization prompt...")
        prompt = create_claude_portfolio_prompt(portfolio_data, analyses)
        
        # Get optimization recommendations from Claude
        logger.info("Requesting portfolio optimization from Claude...")
        print("Requesting portfolio optimization from Claude...")
        optimization_response = get_claude_portfolio_optimization(prompt, client, 
                                                               model=config["claude"]["model"])
        
        # Format and save the output
        logger.info("Formatting and saving optimization results...")
        print("Formatting and saving optimization results...")
        output_markdown = format_optimization_output(optimization_response, portfolio_data)
        output_file = config["output"]["claude_optimization_file"]
        save_markdown(output_markdown, output_file)
        logger.info(f"Optimization recommendations saved to {output_file}")
        print(f"Optimization recommendations saved to {output_file}")
        
        logger.info("FINISHED: Claude Portfolio Optimizer")
        print("FINISHED: Claude Portfolio Optimizer")
    except Exception as e:
        logger.error(f"Unexpected error in Claude Portfolio Optimizer: {str(e)}")
        logger.error(traceback.format_exc())
        print(f"Unexpected error: {str(e)}")
        print("See logs for details.")


if __name__ == "__main__":
    main() 