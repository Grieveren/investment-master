"""
Analysis module for generating stock analyses using OpenAI and Anthropic Claude.
"""

import os
import json
import datetime
import time
import re
from openai import OpenAI
from utils.logger import logger
from utils.config import config
from utils.file_operations import save_markdown, save_json_data

# Try to import Anthropic, but don't fail if not available
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

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

def get_value_investing_signals(portfolio_data, api_data, openai_client, anthropic_client, model="o3-mini"):
    """Analyze stocks using value investing principles."""
    logger.info(f"Starting value investing analysis using {model} model")
    
    # Determine if we're using Claude for enhanced analysis
    using_claude = model.startswith("claude")
    thinking_budget = config["claude"].get("thinking_budget", 16000) if using_claude else 0
    
    if using_claude:
        logger.info(f"Using Claude with enhanced analysis mode and {thinking_budget} token thinking budget")
        print(f"Enhanced Analysis Mode: Using Claude with {thinking_budget} token thinking budget")
        print(f"This will provide more comprehensive and nuanced analysis, but may take longer per company")
    
    # Prepare results
    stock_analyses = []
    analysis_date = datetime.date.today().isoformat()
    
    # Process each stock in the portfolio
    for stock in portfolio_data:
        try:
            name = stock.get('name')
            ticker = None
            
            # Try to find the ticker from the name
            for api_ticker, api_stock_data in api_data.items():
                api_name = api_stock_data.get('name', '')
                if not api_name and isinstance(api_stock_data, dict) and 'data' in api_stock_data:
                    # Try to get name from nested data structure
                    if 'companyByExchangeAndTickerSymbol' in api_stock_data['data']:
                        api_name = api_stock_data['data']['companyByExchangeAndTickerSymbol'].get('name', '')
                
                # Check if this is the stock we're looking for
                if name and api_name and name.lower() in api_name.lower() or api_ticker.lower() in name.lower():
                    ticker = api_ticker
                    break
            
            if not ticker:
                logger.warning(f"Could not find ticker for {name}")
                continue
            
                logger.info(f"Found API data for ticker {ticker}")
            
            # Get company data
            company_data = api_data.get(ticker)
            if not company_data:
                logger.warning(f"No API data found for {ticker}")
                continue
            
            # Start timing
            start_time = time.time()
            
            # Create a stock object with the necessary fields
            stock_obj = {
                'ticker': ticker,
                'name': name,
                'data': company_data
            }
            
            # Analyze the stock
            print(f"Analyzing {name} ({ticker})...")
            analysis_result = analyze_stock(stock_obj, model=model, openai_client=openai_client, anthropic_client=anthropic_client)
            
            # Calculate elapsed time
            elapsed_time = time.time() - start_time
            
            # Extract recommendation from analysis
            if isinstance(analysis_result, dict):
                recommendation = analysis_result.get('recommendation', 'N/A')
                summary = analysis_result.get('summary')
                strengths = analysis_result.get('strengths', [])
                weaknesses = analysis_result.get('weaknesses', [])
                
                # Add to stock analyses
            stock_analyses.append({
                'ticker': ticker,
                    'name': name,
                    'recommendation': recommendation,
                    'summary': summary,
                    'strengths': strengths,
                    'weaknesses': weaknesses,
                    'analysis_path': analysis_result.get('analysis_path')
                })
            else:
                recommendation = 'N/A'
                
            print(f"{name:<30} | {'✅ Complete':<20} | {recommendation:<10}")
            logger.info(f"Analyzed {name} ({ticker}) in {elapsed_time:.1f}s: {recommendation}")
            
        except Exception as e:
            logger.error(f"Error analyzing {stock.get('ticker', 'unknown')}: {e}")
            stock_name = stock.get('name')
            if stock_name is None:
                stock_name = stock.get('ticker', 'Unknown')
            if stock_name is None:
                stock_name = 'Unknown'
            print(f"{stock_name:<30} | {'❌ Error':<20} | {'':<10}")
    
    # Create markdown output for the summary table
    markdown = f"# Portfolio Value Investing Analysis\n\nAnalysis Date: {analysis_date}\n\n"
    markdown += "| Stock (Ticker) | Recommendation | Summary | Key Strengths | Detailed Analysis |\n"
    markdown += "|----------------|---------------|---------|--------------|-------------------|\n"
    
    for result in stock_analyses:
        # Ensure all fields are properly formatted for markdown table
        name_with_ticker = f"{result.get('name', 'Unknown')} ({result.get('ticker', 'Unknown')})"
        recommendation = result.get('recommendation', 'N/A')
        
        # Truncate and format summary
        summary = result.get('summary', 'No summary provided')
        if summary is not None and len(summary) > 200:
            summary = summary[:197] + "..."
        summary = summary.replace('\n', ' ').replace('|', '/').strip() if summary else 'No summary provided'
        
        # Get top 2 strengths
        strengths = result.get('strengths', [])
        strengths_text = ", ".join(strengths[:2])
        if len(strengths) > 2:
            strengths_text += ", ..."
        strengths_text = strengths_text.replace('\n', ' ').replace('|', '/').strip()
        
        # Create link to detailed analysis
        ticker = result.get('ticker', 'unknown')
        model_short_name = "openai" if model == "o3-mini" else "claude"
        analysis_link = f"[Full Analysis](companies/{model_short_name}/{ticker}.md)"
        
        # Add row to table
        markdown += f"| {name_with_ticker} | {recommendation} | {summary} | {strengths_text} | {analysis_link} |\n"
    
    # Return the results
    return {
        "markdown": markdown,
        "stocks": stock_analyses
    }

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

def analyze_with_claude(client, stock_data, ticker, company_name, model_name, thinking_budget):
    """Perform a detailed analysis of a stock using Claude model."""
    logger.info(f"Starting enhanced Claude analysis for {ticker}")
    logger.info(f"  - Using enhanced analysis with full data and extended thinking time")
    
    prompt = create_enhanced_analysis_prompt(stock_data, ticker, company_name)
    logger.info(f"Analysis prompt for {ticker} created: {len(prompt)} characters")
    
    # Create system prompt for Claude
    system_prompt = """You are a value investing expert analyzing a stock. Provide a thorough financial analysis that includes:

1. Recommendation: Give a clear BUY, SELL, or HOLD recommendation based on intrinsic value vs. current price.
2. Summary: Provide a brief one-paragraph overview of the company and your recommendation.
3. Strengths: List 3-5 key strengths or competitive advantages.
4. Weaknesses: List 3-5 key weaknesses or challenges.
5. Competitive Analysis: Evaluate the company's position relative to competitors.
6. Management Assessment: Evaluate the management team's performance, vision, and shareholder focus.
7. Financial Health: Analyze key financial metrics including debt, cash flow, and profitability.
8. Growth Prospects: Evaluate growth opportunities in existing and new markets.
9. Price Analysis: Calculate intrinsic value using DCF, P/E, and P/B. Compare to current price.
10. Investment Rationale: Explain with at least 3 reasons why this is a good or bad investment.
11. Risk Factors: List 3-5 key risks.

Use value investing principles with a focus on:
- Margin of safety between price and value
- Financial strength and competitive advantages
- Management quality and shareholder orientation
- Long-term growth prospects

Format your response as Markdown with clear sections for each of the above elements.
"""
    
    # Log the request
    logger.info(f"Requesting detailed company analysis from Claude ({model_name}) with {thinking_budget} token thinking budget...")
    
    max_tokens = 40000  # Set a high max token to accommodate thinking budget
    
    # Log whether we're using streaming
    if thinking_budget > 2000:
        logger.info("Using streaming mode for large thinking budget to avoid timeouts")
        
    try:
        start_time = time.time()
        
        # Use streaming for large thinking budget to prevent timeout
        text_content = ""  # Initialize empty string to collect response
        
        with client.messages.stream(
            model=model_name,
            max_tokens=max_tokens,
            temperature=1.0,  # Must be 1.0 when thinking is enabled
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "enabled", "budget_tokens": thinking_budget}
        ) as stream:
            # Process each chunk in the stream
            for chunk in stream:
                if hasattr(chunk, 'delta') and hasattr(chunk.delta, 'text') and chunk.delta.text:
                    text_content += chunk.delta.text
                elif hasattr(chunk, 'message') and hasattr(chunk.message, 'content'):
                    for content_block in chunk.message.content:
                        if hasattr(content_block, 'text') and content_block.text:
                            text_content += content_block.text
        
        # Log the completion time
        elapsed_time = time.time() - start_time
        logger.info(f"Claude analysis completed in {elapsed_time:.1f}s")
        
        # Extract key information from the response
        recommendation_match = re.search(r'(?:^## |^#|^)Recommendation:?\s*(.*?)$', text_content, re.MULTILINE | re.IGNORECASE)
        summary_match = re.search(r'(?:^## |^#|^)Summary:?\s*(.*?)(?=(?:^## |^#|$))', text_content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        strengths_section = re.search(r'(?:^## |^#|^)Strengths:?\s*(.*?)(?=(?:^## |^#|$))', text_content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        weaknesses_section = re.search(r'(?:^## |^#|^)Weaknesses:?\s*(.*?)(?=(?:^## |^#|$))', text_content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        
        # Extract and format data
        recommendation = recommendation_match.group(1).strip() if recommendation_match else 'N/A'
        summary = summary_match.group(1).strip() if summary_match else None
        
        # Extract strengths
        strengths = []
        if strengths_section:
            strengths_text = strengths_section.group(1)
            # Extract list items (- item or * item or 1. item format)
            strengths_items = re.findall(r'(?:^-|\*|\d+\.)\s*(.*?)$', strengths_text, re.MULTILINE)
            strengths = [item.strip() for item in strengths_items if item.strip()]
        
        # Extract weaknesses
        weaknesses = []
        if weaknesses_section:
            weaknesses_text = weaknesses_section.group(1)
            # Extract list items (- item or * item or 1. item format)
            weaknesses_items = re.findall(r'(?:^-|\*|\d+\.)\s*(.*?)$', weaknesses_text, re.MULTILINE)
            weaknesses = [item.strip() for item in weaknesses_items if item.strip()]
        
        # Create markdown file with the analysis
        markdown_content = f"# {company_name} ({ticker}) Analysis\n\n"
        markdown_content += f"**Analysis Date:** {datetime.date.today().isoformat()}\n\n"
        markdown_content += f"**Recommendation:** {recommendation}\n\n"
        markdown_content += "## Full Analysis\n\n"
        markdown_content += text_content
        
        # Add disclaimer and save
        markdown_content += "\n\n---\n\n"
        markdown_content += "This analysis was performed using SimplyWall.st financial statements data processed through Anthropic's Claude model "
        markdown_content += f"with {thinking_budget} tokens of thinking budget. The enhanced analysis includes comprehensive evaluation of all available financial data. "
        markdown_content += "Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
        markdown_content += "Remember that this analysis is one input for investment decisions and should be combined with your own research and risk assessment."
        
        # Ensure the directory exists
        os.makedirs('data/processed/companies/claude', exist_ok=True)
        
        # Save the markdown file
        file_path = f'data/processed/companies/claude/{ticker}.md'
        with open(file_path, 'w') as f:
            f.write(markdown_content)
        
        logger.info(f"Markdown saved to {file_path}")
        
        return {
            'ticker': ticker,
            'name': company_name,
            'recommendation': recommendation,
            'summary': summary,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'analysis_path': file_path
        }
        
    except Exception as e:
        logger.error(f"Error with Claude analysis for {ticker}: {str(e)}")
        return None

def format_analysis_to_markdown(stock_analyses):
    """Format stock analyses into markdown.
    
    Args:
        stock_analyses (list): List of dictionaries with stock analysis results.
        
    Returns:
        str: Markdown-formatted analysis.
    """
    # Combine all analyses into a single markdown table
    markdown_output = "# Portfolio Value Investing Analysis\n\n"
    markdown_output += f"Analysis Date: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    # Create the table header
    markdown_output += "| Stock (Ticker) | Recommendation | Summary | Key Strengths | Key Weaknesses |\n"
    markdown_output += "|----------------|---------------|---------|--------------|----------------|\n"
    
    # Add each stock's analysis to the table
    for analysis in stock_analyses:
        name = analysis.get('name', 'Unknown')
        ticker = analysis.get('ticker', 'N/A')
        name_with_ticker = f"{name} ({ticker})"
        
        recommendation = analysis.get('recommendation', 'N/A')
        
        # Truncate and format summary
        summary = analysis.get('summary', 'No summary provided')
        if summary is not None and len(summary) > 200:
            summary = summary[:197] + "..."
        summary = summary.replace('\n', ' ').replace('|', '/').strip() if summary else 'No summary provided'
        
        # Get top strengths and weaknesses
        strengths = analysis.get('strengths', [])
        strengths_text = ", ".join(strengths[:2])
        if len(strengths) > 2:
            strengths_text += ", ..."
        
        weaknesses = analysis.get('weaknesses', [])
        weaknesses_text = ", ".join(weaknesses[:2])
        if len(weaknesses) > 2:
            weaknesses_text += ", ..."
        
        # Format cells for markdown table
        markdown_output += f"| {name_with_ticker} | {recommendation} | {summary} | {strengths_text} | {weaknesses_text} |\n"
    
    # Add summary and notes
    markdown_output += "\n## Analysis Summary\n\n"
    markdown_output += "This analysis was performed using SimplyWall.st financial statements data processed through AI analysis. "
    markdown_output += "Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
    markdown_output += "Remember that this analysis is one input for investment decisions and should be combined with your own research and risk assessment."
    
    return markdown_output

def build_analysis_prompt(company_data):
    """Build a comprehensive analysis prompt based on the company data.
    
    This function extracts key financial metrics from the company data and formats
    them into a structured prompt for AI analysis. It includes special handling
    for price extraction using a priority-based approach to ensure accurate current
    stock prices are included.
    
    Args:
        company_data (dict): Company data including financial statements
        
    Returns:
        str: Formatted prompt for analysis
    """
    # Get company basic info
    name = company_data.get('name', 'Unknown Company')
    ticker = company_data.get('ticker', 'UNKNOWN')
    exchange = company_data.get('exchange', 'UNKNOWN')
    
    # Extract statements from API response based on data structure
    statements = []
    if 'statements' in company_data:
        # Direct statements array
        statements = company_data['statements']
    elif 'data' in company_data and 'companyByExchangeAndTickerSymbol' in company_data['data']:
        # Nested structure from GraphQL
        company_obj = company_data['data']['companyByExchangeAndTickerSymbol']
        statements = company_obj.get('statements', [])
        # Also update basic info if available
        if 'name' in company_obj:
            name = company_obj['name']
        if 'tickerSymbol' in company_obj:
            ticker = company_obj['tickerSymbol']
        if 'exchangeSymbol' in company_obj:
            exchange = company_obj['exchangeSymbol']
    
    # Extract key information - CURRENT PRICE and MARKET CAP are priorities
    current_price = None
    market_cap = None
    currency = 'USD'  # Default currency
    
    # PRICE EXTRACTION STRATEGY:
    # 1. First look for price in IsUndervaluedBasedOnDCF statement (most reliable source)
    # 2. If not found, try direct price fields being selective to avoid confusing metrics 
    # 3. If still not found, check various patterns in descriptions
    # This prioritization ensures we get the actual trading price, not P/E ratios or other metrics
    
    # First look for price in IsUndervaluedBasedOnDCF statement (most reliable source)
    for statement in statements:
        if statement.get('name') == 'IsUndervaluedBasedOnDCF':
            description = statement.get('description', '')
            # Extract the price from ticker with price in parentheses - handles both $ and € symbols
            # E.g., "BRK.B ($495.62)" or "ALV (€343.2)"
            price_match = re.search(r'[\u20AC$€]([0-9.,]+)', description)
            if price_match:
                try:
                    # Handle European number format (replace comma with period)
                    price_str = price_match.group(1).replace(',', '.')
                    current_price = float(price_str)
                    # Found the most reliable price, no need to look further
                    break
                except (ValueError, TypeError):
                    pass
    
    # If still no price, try other methods
    if current_price is None:
        # Look for other price-related statements
        for statement in statements:
            stmt_name = statement.get('name', '').lower()
            stmt_area = statement.get('area', '').lower()
            description = statement.get('description', '').lower()
            value = statement.get('value')
            
            # Be very selective about which statements we use for price
            # Avoid statements with PE ratio or other valuation multiples
            if ('current price' in stmt_name.lower() or 'share price' in stmt_name.lower()) and 'ratio' not in stmt_name.lower():
                if value is not None and isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').isdigit()):
                    try:
                        current_price = float(value)
                        break
                    except (ValueError, TypeError):
                        pass
            
            # Look for market cap
            if 'marketcap' in stmt_name.replace(' ', ''):
                market_cap = value
            
            # Try to find currency
            if 'currency' in stmt_name or 'currency' in description:
                if value and isinstance(value, str):
                    currency = value
    
    # If still no price, check descriptions
    if current_price is None:
        # Check statement descriptions for price mentions
        for statement in statements:
            description = statement.get('description', '')
            
            # First try to find ticker with price in parentheses format: "BRK.B ($495.62)"
            ticker_price_match = re.search(r'{}?\s*\(\$([0-9,.]+)\)'.format(re.escape(ticker)), description)
            if ticker_price_match:
                try:
                    price_str = ticker_price_match.group(1).replace(',', '')
                    current_price = float(price_str)
                    break
                except (ValueError, TypeError):
                    pass
            
            # Then try other common price formats
            if 'current price' in description.lower() or 'share price' in description.lower() or 'trading at' in description.lower():
                # Try to extract price from description text
                price_match = re.search(r'(?:price|value|trading at)[^\d]*?\$([0-9,.]+)', description.lower())
                if price_match:
                    try:
                        price_str = price_match.group(1).replace(',', '')
                        current_price = float(price_str)
                        break
                    except (ValueError, TypeError):
                        pass
    
    # Format price and market cap for readability
    current_price_formatted = f"${current_price:.2f}" if current_price is not None else "Not available in API data"
    
    market_cap_formatted = "Unknown"
    if market_cap:
        try:
            market_cap_float = float(market_cap)
            if market_cap_float >= 1000000000:
                market_cap_formatted = f"${market_cap_float / 1000000000:.2f} billion"
            else:
                market_cap_formatted = f"${market_cap_float / 1000000:.2f} million"
        except (ValueError, TypeError):
            market_cap_formatted = str(market_cap)
    
    # Enhanced approach: Group statements by area, but include all of them
    # Define the areas and create empty lists for each
    areas = [
        "VALUE", "HEALTH", "PERFORMANCE", "GROWTH", 
        "DIVIDENDS", "RISK", "MANAGEMENT", "MARKET",
        "BANK_HEALTH", "BANK_DIVIDENDS", "FUTURE", "PAST",
        "REWARDS", "RISKS", "MISC"
    ]
    
    area_statements = {area: [] for area in areas}
    
    # Distribute all statements to their respective areas
    for statement in statements:
        area = statement.get('area', '').upper()
        if area:
            # If this area exists in our mapping, add the statement
            if area in area_statements:
                area_statements[area].append(statement)
            else:
                # For any unknown areas, put in MISC
                area_statements["MISC"].append(statement)
    
    # Start building prompt
    prompt = f"# Financial Analysis for {name} ({ticker})\n\n"
    prompt += f"Exchange: {exchange}\n"
    prompt += f"Current Price: {current_price_formatted}\n"
    prompt += f"Market Cap: {market_cap_formatted}\n\n"
    
    # Add a table of contents for easier navigation
    prompt += "## Table of Contents\n"
    for area in areas:
        if area_statements[area]:  # Only include areas that have statements
            prompt += f"- {area.replace('_', ' ')}\n"
    prompt += "\n"
    
    # Enhanced function to format a statement with full details
    def format_statement(stmt):
        name = stmt.get('name', 'Unnamed')
        title = stmt.get('title', '')
        value = stmt.get('value', 'N/A')
        outcome = stmt.get('outcome', '')
        description = stmt.get('description', 'No description available')
        severity = stmt.get('severity', 0)
        outcome_name = stmt.get('outcomeName', '')
        
        # Show all details for each statement with a clear structure
        formatted = f"### {title if title else name}\n"
        formatted += f"**Result:** {value} ({outcome_name if outcome_name else outcome})\n"
        
        # Add severity indicator if available (higher is more critical)
        if severity:
            try:
                # Convert severity to integer if it's a string
                if isinstance(severity, str):
                    # Handle non-numeric severity values
                    if severity.upper() in ('MINOR', 'LOW'):
                        severity_int = 2
                    elif severity.upper() in ('MODERATE', 'MEDIUM'):
                        severity_int = 5
                    elif severity.upper() in ('SEVERE', 'HIGH', 'CRITICAL'):
                        severity_int = 8
                    else:
                        # Default if not recognized
                        severity_int = 3
                else:
                    # If already a number, use it directly
                    severity_int = int(severity)
                
                severity_indicator = "!" * min(severity_int, 5)  # Max 5 exclamation marks
                formatted += f"**Severity:** {severity_indicator} ({severity_int}/10)\n"
            except (ValueError, TypeError):
                # If conversion fails, just skip the severity indicator
                pass
        
        formatted += f"**Description:** {description}\n\n"
        return formatted
    
    # Add each area with formatted statements
    for area in areas:
        if area_statements[area]:  # Only include areas that have statements
            prompt += f"## {area.replace('_', ' ')}\n"
            
            # For each statement in this area, format it completely
            for stmt in area_statements[area]:
                prompt += format_statement(stmt)
            
            prompt += "\n"
    
    # Add a summary of key metrics
    prompt += "## KEY METRICS SUMMARY\n"
    prompt += f"Current Price: {current_price_formatted}\n"
    prompt += f"Market Cap: {market_cap_formatted}\n"
    prompt += f"Exchange: {exchange}\n"
    prompt += f"Total Financial Statements Analyzed: {len(statements)}\n\n"
    
    # Add specific request for thorough analysis to maximize Claude's thinking
    prompt += "## ANALYSIS REQUEST\n"
    prompt += "Please analyze this company thoroughly using all the data provided above. Take your time to consider:\n\n"
    prompt += "1. Intrinsic value calculation based on future cash flows, growth rates, and margin of safety\n"
    prompt += "2. Quality of the business model and competitive advantages\n"
    prompt += "3. Financial health and risk of financial distress\n"
    prompt += "4. Management quality and capital allocation\n"
    prompt += "5. Growth prospects and sustainability\n"
    prompt += "6. Risks - both company-specific and macroeconomic\n"
    prompt += "7. A clear BUY, SELL, or HOLD recommendation with detailed rationale\n\n"
    prompt += "This is an in-depth value investing analysis. Use as much time as you need to analyze the full dataset."
    
    return prompt

def extract_analysis_components(response):
    """Extract components from the AI analysis response.
    
    Args:
        response (str): Raw response text from the AI model
        
    Returns:
        dict: Dictionary of extracted components
    """
    components = {
        'raw_response': response,
        'recommendation': None,
        'summary': None,
        'strengths': [],
        'weaknesses': [],
        'price_targets': {},
        'rationale': None,
        'metrics': {},
        'competitive_analysis': None,  # New field for enhanced analysis
        'management_assessment': None, # New field for enhanced analysis
        'financial_health': None,      # New field for enhanced analysis
        'growth_prospects': None,      # New field for enhanced analysis
        'risk_factors': None           # New field for enhanced analysis
    }
    
    # Extract recommendation (BUY, SELL, HOLD)
    recommendation_match = re.search(r'(?:^## |^#|^)Recommendation:?\s*(.*?)$', response, re.MULTILINE | re.IGNORECASE)
    if recommendation_match:
        recommendation = recommendation_match.group(1).strip()
        # Normalize to just BUY, SELL, or HOLD
        if 'buy' in recommendation.lower():
            components['recommendation'] = 'BUY'
        elif 'sell' in recommendation.lower():
            components['recommendation'] = 'SELL'
        elif 'hold' in recommendation.lower():
            components['recommendation'] = 'HOLD'
    else:
            components['recommendation'] = recommendation
    
    # Extract summary
    summary_match = re.search(r'(?:^## |^#|^)Summary:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if summary_match:
        components['summary'] = summary_match.group(1).strip()
    
    # Extract strengths
    strengths_match = re.search(r'(?:^## |^#|^)Strengths:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if strengths_match:
        strengths_text = strengths_match.group(1)
        strengths = re.findall(r'^-\s*(.*?)$', strengths_text, re.MULTILINE)
        components['strengths'] = [s.strip() for s in strengths if s.strip()]
    
    # Extract weaknesses
    weaknesses_match = re.search(r'(?:^## |^#|^)Weaknesses:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if weaknesses_match:
        weaknesses_text = weaknesses_match.group(1)
        weaknesses = re.findall(r'^-\s*(.*?)$', weaknesses_text, re.MULTILINE)
        components['weaknesses'] = [w.strip() for w in weaknesses if w.strip()]
    
    # Extract price targets
    price_analysis_match = re.search(r'(?:^## |^#|^)Price Analysis:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if price_analysis_match:
        price_analysis = price_analysis_match.group(1).strip()
        
        # Extract current price
        current_price_match = re.search(r'Current Price:.*?[$€£¥]([0-9.,]+)', price_analysis, re.IGNORECASE)
        if current_price_match:
            try:
                # Handle potential commas in number format
                price_str = current_price_match.group(1).replace(',', '')
                components['price_targets']['current_price'] = float(price_str)
            except (ValueError, IndexError):
                pass
        
        # Extract intrinsic value
        intrinsic_match = re.search(r'Intrinsic Value:.*?[$€£¥]([0-9.,]+)', price_analysis, re.IGNORECASE)
        if intrinsic_match:
            try:
                value_str = intrinsic_match.group(1).replace(',', '')
                components['price_targets']['intrinsic_value'] = float(value_str)
            except (ValueError, IndexError):
                pass
        
        # Extract margin of safety
        safety_match = re.search(r'Margin of Safety:.*?([0-9.,]+)%', price_analysis, re.IGNORECASE)
        if safety_match:
            try:
                safety_str = safety_match.group(1).replace(',', '')
                components['price_targets']['margin_of_safety'] = float(safety_str)
            except (ValueError, IndexError):
                pass
                
        # Extract valuation method (new field from enhanced analysis)
        valuation_method_match = re.search(r'Valuation Method\(s\):.*?([^\n]+)', price_analysis, re.IGNORECASE)
        if valuation_method_match:
            components['price_targets']['valuation_method'] = valuation_method_match.group(1).strip()
    
    # Extract investment rationale
    rationale_match = re.search(r'(?:^## |^#|^)Investment Rationale:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if rationale_match:
        components['rationale'] = rationale_match.group(1).strip()
    
    # Extract new sections from enhanced analysis
    
    # Competitive Analysis
    comp_analysis_match = re.search(r'(?:^## |^#|^)Competitive Analysis:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if comp_analysis_match:
        components['competitive_analysis'] = comp_analysis_match.group(1).strip()
    
    # Management Assessment
    mgmt_match = re.search(r'(?:^## |^#|^)Management Assessment:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if mgmt_match:
        components['management_assessment'] = mgmt_match.group(1).strip()
    
    # Financial Health
    fin_health_match = re.search(r'(?:^## |^#|^)Financial Health:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if fin_health_match:
        components['financial_health'] = fin_health_match.group(1).strip()
    
    # Growth Prospects
    growth_match = re.search(r'(?:^## |^#|^)Growth Prospects:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if growth_match:
        components['growth_prospects'] = growth_match.group(1).strip()
    
    # Risk Factors
    risk_match = re.search(r'(?:^## |^#|^)Risk Factors:?\s*(.*?)(?=(?:^## |^#|$))', response, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if risk_match:
        components['risk_factors'] = risk_match.group(1).strip()
    
    return components 

def create_enhanced_analysis_prompt(stock_data, ticker, company_name):
    """Create a detailed prompt for Claude with all available financial data."""
    # Financial data and metadata
    financial_metrics = stock_data.get('financial_metrics', {})
    financial_statements = stock_data.get('financial_statements', {})
    
    # Get current price if available
    current_price = stock_data.get('current_price', 'Not available')
    currency = stock_data.get('currency', 'USD')
    
    # Create the prompt
    prompt = f"""# Financial Analysis Request for {company_name} ({ticker})

## Company Information
- Company: {company_name}
- Ticker: {ticker}
- Current Price: {current_price} {currency}
- Industry: {stock_data.get('industry', 'Not available')}
- Sector: {stock_data.get('sector', 'Not available')}

## Key Financial Metrics
"""

    # Add financial metrics
    if financial_metrics:
        for category, metrics in financial_metrics.items():
            prompt += f"\n### {category}\n"
            for metric_name, value in metrics.items():
                prompt += f"- {metric_name}: {value}\n"
    
    # Add financial statements if available
    if financial_statements:
        prompt += "\n## Financial Statements\n"
        for statement_type, data in financial_statements.items():
            prompt += f"\n### {statement_type}\n"
            if isinstance(data, dict):
                for year, values in data.items():
                    prompt += f"\n#### {year}\n"
                    for item, value in values.items():
                        prompt += f"- {item}: {value}\n"
            else:
                prompt += "Data not available in expected format\n"
    
    # Add business description if available
    if 'business_description' in stock_data:
        prompt += f"\n## Business Description\n{stock_data.get('business_description')}\n"
    
    # Add news if available
    if 'news' in stock_data and stock_data['news']:
        prompt += "\n## Recent News\n"
        for news_item in stock_data['news']:
            prompt += f"- {news_item.get('date', 'No date')}: {news_item.get('headline', 'No headline')}\n"
    
    # End with analysis request
    prompt += """
## Analysis Request

Using the provided financial data, please conduct a detailed value investing analysis for this company. 

Your analysis should focus on:
1. Intrinsic value estimation vs current market price
2. Financial health assessment
3. Competitive advantages and business model durability
4. Management quality and capital allocation
5. Growth prospects and market position
6. Key risks and potential catalysts

Based on your analysis, provide a clear BUY, SELL, or HOLD recommendation with detailed rationale.
"""
    
    return prompt

def analyze_stock(stock, model, openai_client=None, anthropic_client=None):
    """Analyze a single stock using the specified model."""
    ticker = stock['ticker']
    name = stock['name']
    company_data = stock['data']
    
    # Build the analysis prompt
    logger.info(f"Building comprehensive analysis prompt for {ticker}")
    prompt = create_enhanced_analysis_prompt(company_data, ticker, name)
    
    # Show prompt size to monitor token usage
    prompt_size = len(prompt)
    logger.info(f"Analysis prompt for {ticker} created: {prompt_size} characters")
    
    # Determine which model to use
    if model.startswith("claude"):
        # Use Claude with enhanced analysis
        thinking_budget = config["claude"].get("thinking_budget", 16000)
        logger.info(f"Starting enhanced Claude analysis for {ticker}")
        print(f"  - Using enhanced analysis with full data and extended thinking time")
        return analyze_with_claude(anthropic_client, company_data, ticker, name, model, thinking_budget)
        else:
        # Use OpenAI for analysis
        logger.info(f"Starting OpenAI analysis for {ticker}")
        system_prompt = """You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham.

You will produce a detailed value investing analysis report with the following structure:

# [Company Name] ([Ticker])

## Recommendation
[Clearly state BUY, SELL, or HOLD here - this must be one of these three words]

## Summary
[One paragraph summary of the company and your analysis]

## Strengths
- [Strength 1]
- [Strength 2]
- [Additional strengths...]

## Weaknesses
- [Weakness 1]
- [Weakness 2]
- [Additional weaknesses...]

## Price Analysis
Current Price: $[current price]
Intrinsic Value: $[your estimated fair value]
Margin of Safety: [percentage]%

## Investment Rationale
[Detailed explanation of your recommendation, focusing on value investing principles]

Follow this format exactly as it will be parsed programmatically. Your analysis should be based on the financial statements and data provided, evaluating whether the stock is undervalued, fairly valued, or overvalued according to value investing principles.
"""
        response = openai_client.chat.completions.create(
            model=config["openai"]["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        # Extract the text from the response
        text_content = response.choices[0].message.content
        
        # Extract components from the response
        components = extract_analysis_components(text_content)
        
        # Create markdown file with the analysis
        markdown_content = f"# {name} ({ticker}) Analysis\n\n"
        markdown_content += f"**Analysis Date:** {datetime.date.today().isoformat()}\n\n"
        markdown_content += f"**Recommendation:** {components.get('recommendation', 'N/A')}\n\n"
        markdown_content += "## Full Analysis\n\n"
        markdown_content += text_content
        
        # Add disclaimer and save
        markdown_content += "\n\n---\n\n"
        markdown_content += "This analysis was performed using SimplyWall.st financial statements data processed through OpenAI's model. "
        markdown_content += "Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
        markdown_content += "Remember that this analysis is one input for investment decisions and should be combined with your own research and risk assessment."
        
        # Ensure the directory exists
        os.makedirs('data/processed/companies/openai', exist_ok=True)
        
        # Save the markdown file
        file_path = f'data/processed/companies/openai/{ticker}.md'
        with open(file_path, 'w') as f:
            f.write(markdown_content)
        
        logger.info(f"Markdown saved to {file_path}")
        
        return {
            'ticker': ticker,
            'name': name,
            'recommendation': components.get('recommendation', 'N/A'),
            'summary': components.get('summary'),
            'strengths': components.get('strengths', []),
            'weaknesses': components.get('weaknesses', []),
            'analysis_path': file_path
        } 