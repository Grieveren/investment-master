"""
Analysis module for generating stock analyses using OpenAI and Anthropic Claude.
"""

import os
import json
import datetime
import time
from openai import OpenAI

# Try to import Anthropic, but don't fail if not available
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from utils.logger import logger
from utils.config import config
from utils.portfolio import get_stock_ticker_and_exchange

def create_openai_client(api_key):
    """Create an OpenAI client.

    Args:
        api_key (str): OpenAI API key.

    Returns:
        OpenAI: OpenAI client, or None if creation failed.
    """
    try:
        if not api_key or api_key.startswith("your_"):
            logger.warning("Invalid OpenAI API key. Analysis will not be available.")
            return None
        
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Error creating OpenAI client: {e}")
        return None

def create_anthropic_client(api_key=None):
    """Create an Anthropic Claude client.
    
    Args:
        api_key (str, optional): Anthropic API key. If None, will use the ANTHROPIC_API_KEY from environment.
    
    Returns:
        Anthropic: Anthropic client, or None if creation failed.
    """
    if not ANTHROPIC_AVAILABLE:
        logger.error("Anthropic package not installed. Please install with 'pip install anthropic'")
        return None
        
    try:
        if not api_key:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            
        if not api_key or api_key.startswith("your_"):
            logger.warning("Invalid Anthropic API key. Claude analysis will not be available.")
            return None
        
        client = anthropic.Anthropic(api_key=api_key)
        return client
    except Exception as e:
        logger.error(f"Error creating Anthropic client: {e}")
        return None

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
        str: Markdown-formatted analysis with buy/sell/hold signals for each stock
    """
    # Check if appropriate client is available based on model
    if model.startswith("claude"):
        if anthropic_client is None:
            return "Error: Anthropic client not initialized. Please check your API key."
    else:
        if openai_client is None:
            return "Error: OpenAI client not initialized. Please check your API key."
        
    # Process each stock individually
    analysis_results = []
    
    total_stocks = len(portfolio_data)
    print(f"\n{'='*50}")
    print(f"ANALYZING {total_stocks} STOCKS WITH {model}")
    print(f"{'='*50}")
    print(f"{'Stock':<30} | {'Status':<20} | {'Signal':<10}")
    print(f"{'-'*30} | {'-'*20} | {'-'*10}")
    
    analysis_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    for idx, stock in enumerate(portfolio_data):
        try:
            # Get stock info
            stock_name = stock['name']
            
            # Check if we have data for this stock
            if stock_name not in api_data:
                logger.warning(f"No data found for {stock_name}. Skipping analysis.")
                continue
            
            # Use the utility function to get ticker for display purposes
            stock_info = get_stock_ticker_and_exchange(stock_name)
            if not stock_info:
                ticker = "N/A"
            else:
                ticker = stock_info['ticker']
            
            # Get company data from API response    
            api_response = api_data[stock_name]
            
            # Extract company data from API response
            company_data = {}
            
            if "data" in api_response and "companyByExchangeAndTickerSymbol" in api_response["data"]:
                company_obj = api_response["data"]["companyByExchangeAndTickerSymbol"]
                company_data = {
                    "name": company_obj.get("name", stock_name),
                    "ticker": company_obj.get("tickerSymbol", ticker),
                    "exchange": company_obj.get("exchangeSymbol", "Unknown"),
                    "statements": company_obj.get("statements", [])
                }
            else:
                # No valid data found
                logger.warning(f"Invalid API response format for {stock_name}")
                continue
            
            print(f"{company_data['name']:<30} | {'Processing...':<20} | {'':<10}", end='\r')
            
            # Prepare the system prompt with value investing principles
            system_prompt = """You are a value investing expert with deep knowledge of fundamental analysis, following principles of Warren Buffett and Benjamin Graham. 
            You thoroughly analyze financial statements, focusing on margins of safety, quality of management, sustainable competitive advantages, and intrinsic value relative to current price.
            For each company, provide a BUY, SELL, or HOLD recommendation, with a detailed rationale based solely on value investing principles."""
            
            # Create the user prompt with all available financial data
            user_prompt = build_analysis_prompt(company_data)
            
            start_time = time.time()
            
            if model.startswith("claude"):
                # Use Claude for analysis
                response = analyze_with_claude(user_prompt, anthropic_client, model=config["claude"]["model"])
            else:
                # Use OpenAI for analysis
                response = analyze_with_openai(system_prompt, user_prompt, openai_client, model=config["openai"]["model"])
            
            elapsed_time = time.time() - start_time
            
            # Extract the buy/sell/hold signal and rationale from the response
            signal, rationale, valuation, risk_factors = extract_analysis_components(response)
            
            # Add to results
            analysis_results.append({
                'name': company_data['name'],
                'ticker': ticker,
                'signal': signal,
                'rationale': rationale,
                'valuation_assessment': valuation,
                'key_risk_factors': risk_factors
            })
            
            print(f"{company_data['name']:<30} | {'✅ Complete':<20} | {signal:<10}")
            logger.info(f"Analyzed {company_data['name']} ({ticker}) in {elapsed_time:.1f}s: {signal}")
            
        except Exception as e:
            logger.error(f"Error analyzing {stock.get('ticker', 'unknown')}: {e}")
            print(f"{stock.get('name', stock.get('ticker', 'Unknown')):<30} | {'❌ Error':<20} | {'':<10}")
    
    # Create markdown output
    markdown = f"# Portfolio Value Investing Analysis\n\nAnalysis Date: {analysis_date}\n\n"
    markdown += "| Stock (Ticker) | Signal | Rationale | Valuation Assessment | Key Risk Factors |\n"
    markdown += "|----------------|--------|-----------|----------------------|------------------|\n"
    
    for result in analysis_results:
        markdown += f"| {result['name']} ({result['ticker']}) | {result['signal']} | {result['rationale']} | {result['valuation_assessment']} | {result['key_risk_factors']} |\n"
    
    markdown += "\n## Analysis Summary\n\n"
    if model.startswith("claude"):
        markdown += "This analysis was performed using SimplyWall.st financial statements data processed through Anthropic's Claude model with extended thinking. Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
    else:
        markdown += "This analysis was performed using SimplyWall.st financial statements data processed through OpenAI's o3-mini model. Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
    
    markdown += "Remember that this analysis is one input for investment decisions and should be combined with your own research and risk assessment."
    
    return markdown

def analyze_with_openai(system_prompt, user_prompt, client, model="o3-mini"):
    """Send analysis request to OpenAI.
    
    Args:
        system_prompt (str): System prompt with instructions
        user_prompt (str): User prompt with financial data
        client (OpenAI): OpenAI client
        model (str): OpenAI model to use
        
    Returns:
        str: Response text
    """
    # Add high-reasoning effort if configured
    reasoning_effort = "high" if config["openai"].get("reasoning_effort") == "high" else "auto"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            reasoning_effort=reasoning_effort
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return f"Error: {e}"

def analyze_with_claude(user_prompt, client, model="claude-3-7-sonnet-20250219"):
    """Send analysis request to Claude with extended thinking.
    
    Args:
        user_prompt (str): User prompt with financial data
        client (anthropic.Anthropic): Anthropic client
        model (str): Claude model to use
        
    Returns:
        str: Response text
    """
    try:
        thinking_budget = config["claude"].get("thinking_budget", 16000)
        
        response = client.messages.create(
            model=model,
            max_tokens=20000,  # Increased to be greater than thinking budget
            system="You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham.",
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            thinking={"type": "enabled", "budget_tokens": thinking_budget},
            temperature=1.0  # Must be 1.0 when thinking is enabled
        )
        
        # Extract and return the text response
        text_content = ""
        for block in response.content:
            if hasattr(block, 'text'):
                text_content += block.text
        
        return text_content
        
    except Exception as e:
        logger.error(f"Error calling Claude API: {e}")
        return f"Error: {e}"

def format_analysis_to_markdown(stock_analyses):
    """Format the stock analyses into a markdown table.
    
    Args:
        stock_analyses (list): List of stock analysis dictionaries.
        
    Returns:
        str: Markdown-formatted analysis.
    """
    # Combine all analyses into a single markdown table
    markdown_output = "# Portfolio Value Investing Analysis\n\n"
    markdown_output += f"Analysis Date: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    # Create the table header
    markdown_output += "| Stock (Ticker) | Signal | Rationale | Valuation Assessment | Key Risk Factors |\n"
    markdown_output += "|----------------|--------|-----------|----------------------|------------------|\n"
    
    # Add each stock's analysis to the table
    for analysis in stock_analyses:
        name_with_ticker = f"{analysis['name']} ({analysis['ticker']})"
        signal = analysis['signal']
        rationale = analysis.get('rationale', 'No rationale provided')
        valuation = analysis.get('valuation', 'Unknown')
        risks = analysis.get('risks', 'No risks identified')
        
        markdown_output += f"| {name_with_ticker} | {signal} | {rationale} | {valuation} | {risks} |\n"
    
    # Add summary and notes
    markdown_output += "\n## Analysis Summary\n\n"
    markdown_output += "This analysis was performed using SimplyWall.st financial statements data processed through OpenAI's o3-mini model. "
    markdown_output += "Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
    markdown_output += "Remember that this analysis is one input for investment decisions and should be combined with your own research and risk assessment."
    
    return markdown_output

def build_analysis_prompt(company_data):
    """Build a comprehensive analysis prompt based on the company data.
    
    Args:
        company_data (dict): Company data including financial statements
        
    Returns:
        str: Formatted prompt for analysis
    """
    name = company_data.get('name', 'Unknown Company')
    ticker = company_data.get('ticker', 'UNKNOWN')
    exchange = company_data.get('exchange', 'UNKNOWN')
    
    # Extract key financial data
    financial_metrics = {}
    statements = company_data.get('statements', [])
    
    for statement in statements:
        key = statement.get('key', '')
        value = statement.get('value')
        
        if key and value is not None:
            financial_metrics[key] = value
    
    # Build the prompt
    prompt = f"""
    You are a value investing expert analyzing stock data.
    
    Stock Information:
    Company: {name} ({ticker} on {exchange})
    
    Financial Data:
    """
    
    # Add selected important metrics if available
    key_metrics = [
        ('pe_ratio', 'P/E Ratio'),
        ('pb_ratio', 'Price to Book'),
        ('debt_to_equity', 'Debt to Equity'),
        ('roe', 'Return on Equity'),
        ('profit_margin', 'Profit Margin'),
        ('dividend_yield', 'Dividend Yield'),
        ('free_cash_flow', 'Free Cash Flow'),
        ('interest_coverage', 'Interest Coverage'),
        ('current_ratio', 'Current Ratio'),
        ('earnings_growth_5yr', '5-Year Earnings Growth'),
        ('revenue_growth_5yr', '5-Year Revenue Growth'),
        ('fcf_growth_5yr', '5-Year FCF Growth')
    ]
    
    for key, label in key_metrics:
        if key in financial_metrics:
            prompt += f"- {label}: {financial_metrics[key]}\n"
    
    # Add all remaining financial metrics
    prompt += "\nDetailed Financial Statements:\n"
    for key, value in financial_metrics.items():
        if key not in [k for k, _ in key_metrics]:
            # Format the key name for better readability
            formatted_key = key.replace('_', ' ').title()
            prompt += f"- {formatted_key}: {value}\n"
    
    prompt += """
    Based on the principles of value investing (Benjamin Graham and Warren Buffett), analyze this company and provide:
    
    1. A buy/sell/hold recommendation with detailed rationale
    2. Valuation assessment (undervalued, fairly valued, or overvalued) with specific analysis of current price vs intrinsic value
    3. Key risk factors from a value investing perspective
    
    In your analysis, focus on:
    - Margin of safety
    - Quality of management
    - Sustainable competitive advantages
    - Debt levels and financial strength
    - Earnings quality and consistency
    - Free cash flow generation
    - Return on invested capital
    
    Provide your response in a clear, structured format with specific sections for:
    1. SIGNAL (BUY/SELL/HOLD)
    2. RATIONALE
    3. VALUATION ASSESSMENT
    4. KEY RISK FACTORS
    """
    
    return prompt

def extract_analysis_components(response_text):
    """Extract the key components from an AI analysis response.
    
    Args:
        response_text (str): The full text response from the AI
        
    Returns:
        tuple: (signal, rationale, valuation, risk_factors)
    """
    signal = "UNKNOWN"
    rationale = "Analysis unavailable"
    valuation = "Unknown"
    risk_factors = "None identified"
    
    # Try to extract signal
    if "BUY" in response_text.upper():
        signal = "BUY"
    elif "SELL" in response_text.upper():
        signal = "SELL"
    elif "HOLD" in response_text.upper():
        signal = "HOLD"
    
    # Try to extract sections by looking for headers
    sections = {}
    current_section = None
    
    for line in response_text.split('\n'):
        # Check for section headers
        line_upper = line.upper()
        if "SIGNAL" in line_upper or "RECOMMENDATION" in line_upper:
            current_section = "signal"
            sections[current_section] = ""
        elif "RATIONALE" in line_upper or "ANALYSIS" in line_upper:
            current_section = "rationale"
            sections[current_section] = ""
        elif "VALUATION" in line_upper:
            current_section = "valuation"
            sections[current_section] = ""
        elif "RISK" in line_upper:
            current_section = "risks"
            sections[current_section] = ""
        elif current_section and line.strip():
            # Add content to current section
            sections[current_section] += line.strip() + " "
    
    # Extract content from identified sections
    if "rationale" in sections:
        rationale = sections["rationale"].strip()
    if "valuation" in sections:
        valuation = sections["valuation"].strip()
    if "risks" in sections:
        risk_factors = sections["risks"].strip()
    
    return signal, rationale, valuation, risk_factors 