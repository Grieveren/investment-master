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
import glob
import datetime
import time
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
        normalized_ticker = ticker.replace("_", ".")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            analyses[normalized_ticker] = content
            logger.debug(f"Loaded analysis for {normalized_ticker}")
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
    
    return analyses


def create_claude_portfolio_prompt(portfolio_data, analyses):
    """Create a comprehensive prompt for Claude with portfolio data and analyses.
    
    Args:
        portfolio_data (dict): Portfolio data from parse_portfolio_csv.
        analyses (dict): Dictionary of company analyses keyed by ticker.
        
    Returns:
        str: Comprehensive prompt for Claude.
    """
    logger.info("Creating portfolio optimization prompt...")
    
    # Calculate total portfolio value from positions
    total_value = 0
    for position in portfolio_data.get('positions', []):
        market_value = position.get('Market Value (EUR)')
        if market_value:
            # Handle numeric or string representations
            if isinstance(market_value, (int, float)):
                total_value += market_value
            elif isinstance(market_value, str):
                # Try to convert string to float, handling commas and periods
                try:
                    # Remove currency symbols, spaces, and handle European number format
                    clean_value = market_value.replace('€', '').replace(' ', '')
                    # Convert European format (1.234,56) to standard format (1234.56)
                    clean_value = clean_value.replace('.', '').replace(',', '.')
                    total_value += float(clean_value)
                except ValueError:
                    logger.warning(f"Could not convert market value: {market_value}")
    
    logger.info(f"Portfolio total value: €{total_value:,.2f}")
    
    # Create the prompt
    prompt = """# Portfolio Optimization Analysis Request

## Portfolio Overview

"""
    
    # Add portfolio summary
    prompt += f"- Total portfolio value: €{total_value:,.2f}\n"
    prompt += f"- Number of positions: {len(portfolio_data['positions'])}\n"
    current_date = portfolio_data.get(
        'date', datetime.datetime.now().strftime('%Y-%m-%d')
    )
    prompt += f"- Date: {current_date}\n\n"
    
    # Add current positions
    prompt += "## Current Positions\n\n"
    prompt += "| Position | Ticker | Current Value (€) | % of Portfolio | "
    prompt += "Shares | Current Price | Portfolio |\n"
    prompt += "|----------|--------|------------------|----------------|"
    prompt += "--------|---------------|----------|\n"
    
    # Prepare data to map portfolio data to analyses
    ticker_map = {
        # Original format
        "ALLIANZ SE NA O.N.": "ALV",
        "ASML HOLDING    EO -,09": "ASML",
        "ADVANCED MIC.DEV.  DL-,01": "AMD",
        "ALPHABET INC.CL C DL-,001": "GOOG",
        "BERKSH. H.B NEW DL-,00333": "BRK.B",
        "CROWDSTRIKE HLD. DL-,0005": "CRWD",
        "MICROSOFT    DL-,00000625": "MSFT",
        "NUTANIX INC. A": "NTNX", 
        "NVIDIA CORP.      DL-,001": "NVDA",
        "TAIWAN SEMICON.MANU.ADR/5": "TSM",
        # Add new format entries
        "GitLab Inc.": "GTLB",
    }
    
    # Column mapping for different CSV formats
    column_mapping = {
        # Original format
        "Bezeichnung": ["Bezeichnung", "Security"],
        "Wert in EUR": ["Wert in EUR", "Market Value (EUR)"],
        "Anteil im Depot": ["Anteil im Depot", "Weight"],
        "Einstandswert in EUR": ["Einstandswert in EUR", "Purchase Value (EUR)"],
        "akt. Kurs": ["akt. Kurs", "Current Price (EUR)"],
        "Stück/Nominale": ["Stück/Nominale", "Shares"]
    }
    
    # Helper function to get value using column mapping
    def get_value(position, key):
        for possible_key in column_mapping.get(key, [key]):
            if possible_key in position:
                return position[possible_key]
        return None
    
    # Track which positions we have analyses for
    positions_with_analyses = []
    
    for position in portfolio_data['positions']:
        # Get designation using column mapping
        designation = get_value(position, "Bezeichnung")
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
                    clean_str = ''.join(
                        c for c in value if c.isdigit() or c in ',.').strip()
                    # Convert European format (1.234,56) to standard format (1234.56)
                    clean_str = clean_str.replace('.', '').replace(',', '.')
                    return float(clean_str)
                except (ValueError, TypeError):
                    return default
            return default
        
        # Convert values using the safe conversion function
        current_value = safe_convert(get_value(position, "Wert in EUR"))
        
        # For Weight, handle percentage format
        weight_value = get_value(position, "Anteil im Depot")
        if isinstance(weight_value, str) and '%' in weight_value:
            weight_value = weight_value.replace('%', '')
        percent = safe_convert(weight_value)
        
        # Get shares
        shares = safe_convert(get_value(position, "Stück/Nominale"))
        
        # Get current price
        current_price = safe_convert(get_value(position, "akt. Kurs"))
        
        # Get portfolio identifier if available
        portfolio_id = position.get('Portfolio', '')
        
        # Add to table
        prompt += f"| {designation} | {ticker} | €{current_value:,.2f} | "
        prompt += f"{percent:.2f}% | {shares:.0f} | {current_price:.2f} | "
        prompt += f"{portfolio_id} |\n"
        
        # Track positions that have analyses
        if ticker in analyses:
            positions_with_analyses.append((ticker, designation))
        else:
            logger.warning(f"No analysis found for {ticker}")
    
    # Add individual stock analyses
    prompt += "\n## Individual Stock Analyses\n\n"
    
    for ticker, designation in positions_with_analyses:
        prompt += f"### Analysis for {designation} ({ticker})\n\n"
        
        # Include the complete analysis - no extraction of sections
        analysis = analyses.get(ticker, "No analysis available")
        prompt += analysis + "\n\n"
        analysis_len = len(analysis)
        logger.info(f"Added complete analysis for {ticker} ({analysis_len} characters)")
    
    # Add final optimization request
    prompt += """
## Portfolio Optimization Request

IMPORTANT: Only make recommendations for positions that are ALREADY in the portfolio. 
DO NOT suggest adding any new positions that aren't listed in the Current Positions 
table above.

IMPORTANT: Treat all three portfolios (Work, Family, Brett) as ONE UNIFIED PORTFOLIO. 
When making recommendations:
1. Consider duplicate positions across portfolios as a single consolidated position
2. Do not distinguish which sub-portfolio a position belongs to in your recommendations
3. Evaluate positions purely on their investment merits, not on which sub-portfolio they're in
4. Make recommendations for the total portfolio as if it were a single unified account

Based on the above data, please provide:

1. **Overall Analysis**: A comprehensive analysis of the current portfolio considering 
   diversification, sector allocation, risk profile, and alignment with value investing 
   principles.

2. **Recommended Changes**: Specific recommendations for rebalancing the portfolio, including:
   - Positions to increase (with specific amounts in euros and percentages)
   - Positions to decrease (with specific amounts in euros and percentages)
   - Positions to maintain

3. **Detailed Rationales**: For each recommended change, provide a detailed explanation 
   of the rationale, considering:
   - Intrinsic value estimates and margin of safety
   - Growth prospects and competitive position
   - Portfolio balance considerations
   - Risk management considerations

4. **Overall Optimization Strategy**: Explain the overall portfolio optimization strategy 
   and how it aligns with value investing principles.

Please be specific in your recommendations and provide detailed justifications for each 
proposed change. For example, don't just say "increase Microsoft position", but rather 
"increase Microsoft (MSFT) position by €X,XXX (approximately X%), because...".

## German Investor Considerations

Please consider that I am a German investor based in Germany, with the following specific 
considerations:

1. **Tax Implications**:
   - 26.375% flat tax on capital gains and dividends (25% base rate + 5.5% solidarity surcharge)
   - €1,000 annual tax-free allowance (Sparerpauschbetrag)
   - Different tax treatment for accumulating vs. distributing funds
   - Double taxation issues with US stocks (15% US withholding tax + German taxation)
   - Tax efficiency of different investment vehicles and asset classes

2. **Currency Considerations**:
   - EUR is my base currency
   - Non-EUR denominated stocks introduce currency risk
   - Currency conversion costs impact total returns
   - Hedging options for currency risk

3. **Commerzbank Direct Depot Account Specifics**:
   - Transaction fees: 0.25% of transaction volume + €4.90 (minimum €9.90) for stocks, 
     ETFs, certificates, and bonds on German exchanges
   - Additional costs for international exchanges may apply
   - No custody fees when executing at least one trade per quarter (otherwise 0.175% p.a., 
     minimum €4.95 per quarter)
   - ETF savings plans cost 0.25% of transaction volume + €2.50 per execution
   - Trading on XETRA and other German exchanges is available
   - Access to 64 trading venues worldwide
   - No limit fees for various order types (limit orders, stop orders, trailing stop orders)
   - Additional €9.50 fee for phone orders
   - Support for various order types including standard limit orders, stop orders, 
     and trailing stop orders
   - Automatic tax withholding and reporting to German tax authorities

Please factor these German investor considerations into your portfolio recommendations, 
particularly regarding:
- Tax efficiency of your proposed changes
- Currency exposure in the overall portfolio
- Transaction cost implications of your recommendations
- Specific advantages/disadvantages for German investors in each position

Use your maximum thinking budget to analyze all data thoroughly and provide the most 
comprehensive optimization possible.
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
        thinking_budget = config["claude"].get("thinking_budget", 32000)
        output_tokens = config["portfolio"]["claude_optimization"].get("output_tokens", 4000)
        # max_tokens must be larger than thinking_budget according to Anthropic's docs
        max_tokens = thinking_budget + output_tokens
        temperature = config["portfolio"]["claude_optimization"].get("temperature", 0.1)
        
        # System prompt to clarify the task
        system_prompt = """You are a financial advisor with expertise in value investing and 
specific knowledge of German investment considerations.
Your task is to provide comprehensive portfolio optimization recommendations based on 
the detailed portfolio data and individual stock analyses provided. Focus on providing specific,
actionable advice with detailed rationales for each recommendation.

Take your time to think through all aspects of the portfolio in detail:
1. Consider the intrinsic value of each stock compared to its current price
   - Perform detailed DCF calculations when possible
   - Apply appropriate margin of safety for each company based on its specific risks
   - Explain your valuation methodology for each position
2. Analyze sector allocations and diversification
   - Compare current sector weights against appropriate benchmarks
   - Identify sectors that are overweight or underweight
3. Evaluate the risk profile of the overall portfolio
   - Assess both systematic and unsystematic risks
   - Consider correlation between positions and diversification effects
4. Compare the growth prospects of each position
   - Analyze historical growth rates and future projections
   - Consider industry trends and competitive positioning
5. Look for potential concentration risks
   - Geographic concentration
   - Sector concentration
   - Risk factor concentration (e.g., interest rate sensitivity)
6. Assess the alignment with value investing principles
   - Focus on quantitative metrics like P/E, P/B, debt levels, etc.
   - Evaluate qualitative factors like competitive advantages and management quality
7. Evaluate tax implications for a German investor (26.375% flat tax, €1,000 annual allowance)
   - Consider tax-efficient rebalancing strategies
   - Evaluate impact of dividend withholding taxes for different countries
8. Consider currency risks for non-EUR denominated stocks
   - Analyze historical currency volatility
   - Assess hedging needs for different currency exposures
9. Account for the specific Commerzbank direct depot fee structure:
   - 0.25% of transaction volume + €4.90 (minimum €9.90) for trades on German exchanges
   - No custody fees with at least one trade per quarter
   - ETF savings plans at 0.25% of volume + €2.50
   - No fees for limit orders or stop orders
   - Additional €9.50 fee for phone orders
10. Consider transaction cost implications when recommending portfolio changes
    - Minimize unnecessary transactions
    - Batch similar orders when possible

For each position in the portfolio, provide:
1. A clear buy/hold/sell recommendation with specific percentage adjustments
2. A detailed rationale explaining your recommendation
3. Company-specific risk factors that influenced your decision
4. Intrinsic value estimates and your calculation methodology

Remember that you are advising a German investor using a Commerzbank direct depot account,
so consider German tax laws, EUR as the base currency, and European market access in
your recommendations.

You have an expanded thinking budget of 32,000 tokens, so use this capacity to provide the 
most thorough and detailed analysis possible. Don't rush your analysis - take time to consider 
each position's unique characteristics and how it fits into the overall portfolio strategy."""
        
        logger.info(f"Requesting portfolio optimization from Claude ({model})...")
        logger.info(f"Using thinking budget: {thinking_budget} tokens with total max_tokens: {max_tokens} tokens")
        logger.debug(f"Prompt length: {len(prompt)} characters")
        
        start_time = time.time()
        
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            thinking={"type": "enabled", "budget_tokens": thinking_budget},
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


def format_optimization_output(optimization_response, portfolio_data, total_value=0.0):
    """Format Claude's optimization response for output.
    
    Args:
        optimization_response (str): Claude's response text.
        portfolio_data (dict): Original portfolio data.
        total_value (float): The calculated total portfolio value.
        
    Returns:
        str: Markdown-formatted optimization recommendations.
    """
    # Create a markdown document with the optimization recommendations
    markdown = "# Claude Portfolio Optimization Recommendations\n\n"
    
    # Add date information
    markdown += f"**Analysis Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    # Add note about enhanced analysis mode
    thinking_budget = config["claude"].get("thinking_budget", 32000)
    output_tokens = config["portfolio"]["claude_optimization"].get("output_tokens", 4000)
    max_tokens = thinking_budget + output_tokens
    
    markdown += (
        f"**Enhanced Analysis Mode:** This optimization was performed using the complete "
        f"analysis data for each position with Claude's extended thinking capability ({thinking_budget} tokens "
        f"thinking budget and {output_tokens} output tokens), allowing "
        f"for more comprehensive and nuanced recommendations.\n\n"
    )
    
    # Add note about German investor context
    markdown += (
        "**German Investor Focus:** This analysis specifically accounts for German tax "
        "implications (26.375% flat tax), currency considerations (EUR base), German "
        "market access factors, and Commerzbank direct depot account considerations in "
        "all recommendations.\n\n"
    )
    
    # Add portfolio summary
    markdown += "## Portfolio Summary\n\n"
    
    # Add the total value with proper formatting
    markdown += f"Total portfolio value: €{total_value:,.2f}\n"
    markdown += f"Total positions: {len(portfolio_data['positions'])}\n\n"
    
    # Add optimization recommendations
    markdown += "## Recommendations\n\n"
    markdown += optimization_response
    
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
        
        logger.info(
            f"Successfully parsed portfolio data with {len(portfolio_data['positions'])} positions"
        )
        print(
            f"Successfully parsed portfolio data with {len(portfolio_data['positions'])} positions"
        )
        
        # Create prompt for Claude
        logger.info("Creating portfolio optimization prompt...")
        print("Creating portfolio optimization prompt...")
        prompt = create_claude_portfolio_prompt(portfolio_data, analyses)
        
        # Get the calculated total value
        total_value = 0
        for position in portfolio_data.get('positions', []):
            market_value = position.get('Market Value (EUR)')
            if market_value:
                # Handle numeric or string representations
                if isinstance(market_value, (int, float)):
                    total_value += market_value
                elif isinstance(market_value, str):
                    # Try to convert string to float, handling commas and periods
                    try:
                        # Remove currency symbols, spaces, and handle European number format
                        clean_value = market_value.replace('€', '').replace(' ', '')
                        # Convert European format (1.234,56) to standard format (1234.56)
                        clean_value = clean_value.replace('.', '').replace(',', '.')
                        total_value += float(clean_value)
                    except ValueError:
                        logger.warning(f"Could not convert market value: {market_value}")
        
        # Get optimization recommendations from Claude
        claude_model = config["claude"]["model"]
        thinking_budget = config["claude"].get("thinking_budget", 32000)
        output_tokens = config["portfolio"]["claude_optimization"].get("output_tokens", 4000)
        max_tokens = thinking_budget + output_tokens
        
        logger.info(
            f"Requesting portfolio optimization from Claude ({claude_model}) "
            f"with {thinking_budget} token thinking budget and {max_tokens} total max tokens..."
        )
        print(
            f"Requesting portfolio optimization from Claude ({claude_model}) "
            f"with {thinking_budget} token thinking budget and {max_tokens} total max tokens..."
        )
        print("This may take longer than usual due to full analysis processing...")
        optimization_response = get_claude_portfolio_optimization(
            prompt, client, model=claude_model
        )
        
        # Format and save the output
        logger.info("Formatting and saving optimization results...")
        print("Formatting and saving optimization results...")
        output_markdown = format_optimization_output(
            optimization_response, portfolio_data, total_value
        )
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