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
        # Ensure all fields are properly formatted for markdown table
        name_with_ticker = f"{result['name']} ({result['ticker']})"
        signal = result['signal']
        
        # Clean and format rationale
        rationale = result.get('rationale', 'Analysis unavailable')
        rationale = rationale.replace('\n', ' ').replace('|', '/').strip()
        if len(rationale) > 300:
            rationale = rationale[:297] + "..."
            
        # Clean and format valuation assessment
        valuation = result.get('valuation_assessment', 'Unknown')
        valuation = valuation.replace('\n', ' ').replace('|', '/').strip()
        if len(valuation) > 300:
            valuation = valuation[:297] + "..."
            
        # Clean and format risk factors
        risks = result.get('key_risk_factors', 'None identified')
        risks = risks.replace('\n', ' ').replace('|', '/').strip()
        if len(risks) > 300:
            risks = risks[:297] + "..."
        
        markdown += f"| {name_with_ticker} | {signal} | {rationale} | {valuation} | {risks} |\n"
    
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
        
        # Enhanced system prompt with explicit formatting instructions
        system_prompt = """You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham.

Your analysis must include EXACTLY these four distinct sections, each with its own heading:

1. SIGNAL: State a clear BUY, SELL, or HOLD recommendation as the first line.
2. RATIONALE: Provide a detailed explanation of your recommendation, focusing on value investing principles.
3. VALUATION ASSESSMENT: Evaluate whether the stock is undervalued, fairly valued, or overvalued.
4. KEY RISK FACTORS: List the main risks that could impact the investment thesis.

Format each section with a clear heading (e.g., "## SIGNAL") followed by concise content.
DO NOT include other headings or sections that would confuse parsing.
"""
        
        response = client.messages.create(
            model=model,
            max_tokens=20000,  # Increased to be greater than thinking budget
            system=system_prompt,
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
    As a value investing expert, analyze this stock with Benjamin Graham and Warren Buffett's principles:

    COMPANY INFORMATION:
    Name: {name}
    Ticker: {ticker}
    Exchange: {exchange}
    
    KEY FINANCIAL METRICS:
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
    prompt += "\nADDITIONAL FINANCIAL DATA:\n"
    for key, value in financial_metrics.items():
        if key not in [k for k, _ in key_metrics]:
            # Format the key name for better readability
            formatted_key = key.replace('_', ' ').title()
            prompt += f"- {formatted_key}: {value}\n"
    
    prompt += """
    REQUIRED ANALYSIS FORMAT:
    Your analysis must include exactly these four sections with these specific headings:

    ## SIGNAL
    Your BUY, SELL, or HOLD recommendation based on value investing principles.

    ## RATIONALE
    Detailed explanation of your recommendation focusing on:
    - Competitive advantages (economic moat)
    - Management quality and capital allocation
    - Financial strength and stability
    - Cash flow generation and earnings quality

    ## VALUATION ASSESSMENT
    Whether the stock is undervalued, fairly valued, or overvalued, with analysis of:
    - Current price relative to intrinsic value
    - Margin of safety
    - Potential return prospects

    ## KEY RISK FACTORS
    The main risks that could negatively impact this investment thesis.

    IMPORTANT: Keep each section concise and focused. Do not include additional sections or sub-headings.
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
    
    # Try to extract signal directly from response
    if "BUY" in response_text.upper():
        signal = "BUY"
    elif "SELL" in response_text.upper():
        signal = "SELL"
    elif "HOLD" in response_text.upper():
        signal = "HOLD"
    
    # Improved section detection with multiple possible heading formats
    sections = {}
    current_section = None
    section_text = []
    
    # Normalize line breaks to ensure consistent processing
    normalized_text = response_text.replace('\r\n', '\n')
    
    for line in normalized_text.split('\n'):
        line = line.strip()
        if not line:
            continue
            
        # Check for section headers with different formats (##, #, UPPERCASE:, etc.)
        line_upper = line.upper()
        
        # Signal/Recommendation section
        if any(pattern in line_upper for pattern in ["## SIGNAL", "# SIGNAL", "SIGNAL:", "RECOMMENDATION:", "## RECOMMENDATION", "# RECOMMENDATION"]):
            if current_section and section_text:
                sections[current_section] = ' '.join(section_text)
            current_section = "signal"
            section_text = []
            continue
            
        # Rationale section
        elif any(pattern in line_upper for pattern in ["## RATIONALE", "# RATIONALE", "RATIONALE:", "## ANALYSIS", "# ANALYSIS", "ANALYSIS:"]):
            if current_section and section_text:
                sections[current_section] = ' '.join(section_text)
            current_section = "rationale" 
            section_text = []
            continue
            
        # Valuation section
        elif any(pattern in line_upper for pattern in ["## VALUATION", "# VALUATION", "VALUATION:", "## VALUATION ASSESSMENT", "# VALUATION ASSESSMENT", "VALUATION ASSESSMENT:"]):
            if current_section and section_text:
                sections[current_section] = ' '.join(section_text)
            current_section = "valuation"
            section_text = []
            continue
            
        # Risk section
        elif any(pattern in line_upper for pattern in ["## RISK", "# RISK", "RISK:", "## KEY RISK", "# KEY RISK", "KEY RISK FACTORS:", "## KEY RISK FACTORS", "# KEY RISK FACTORS"]):
            if current_section and section_text:
                sections[current_section] = ' '.join(section_text)
            current_section = "risks"
            section_text = []
            continue
            
        # Add content to current section if we're in one
        elif current_section:
            # Skip sub-headers within sections to avoid keeping them in content
            if line.startswith('#') or line.startswith('*'):
                continue
            section_text.append(line)
    
    # Don't forget to add the last section
    if current_section and section_text:
        sections[current_section] = ' '.join(section_text)
    
    # Extract content from identified sections
    if "signal" in sections:
        # Extract only the BUY/SELL/HOLD from the signal section
        signal_text = sections["signal"].upper()
        if "BUY" in signal_text:
            signal = "BUY"
        elif "SELL" in signal_text:
            signal = "SELL"
        elif "HOLD" in signal_text:
            signal = "HOLD"
    
    if "rationale" in sections:
        rationale = sections["rationale"].strip()
        # Trim to reasonable length for table display
        if len(rationale) > 300:
            rationale = rationale[:297] + "..."
    
    if "valuation" in sections:
        valuation = sections["valuation"].strip()
        # Trim to reasonable length for table display
        if len(valuation) > 300:
            valuation = valuation[:297] + "..."
    
    if "risks" in sections:
        risk_factors = sections["risks"].strip()
        # Trim to reasonable length for table display
        if len(risk_factors) > 300:
            risk_factors = risk_factors[:297] + "..."
    
    return signal, rationale, valuation, risk_factors 