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
    # Check if appropriate client is available based on model
    if model.startswith("claude"):
        if anthropic_client is None:
            return {
                "markdown": "Error: Anthropic client not initialized. Please check your API key.",
                "stocks": []
            }
    else:
        if openai_client is None:
            return {
                "markdown": "Error: OpenAI client not initialized. Please check your API key.",
                "stocks": []
            }
        
    # Process each stock individually
    stock_analyses = []
    
    total_stocks = len(portfolio_data)
    print(f"\n{'='*50}")
    print(f"ANALYZING {total_stocks} STOCKS WITH {model}")
    print(f"{'='*50}")
    
    analysis_date = datetime.datetime.now().strftime("%Y-%m-%d")
    
    print(f"{'Stock':<30} | {'Status':<20} | {'Signal':<10}")
    print(f"{'-'*30} | {'-'*20} | {'-'*10}")
    
    # Create directories for storing individual company analyses
    model_short_name = "openai" if model == "o3-mini" else "claude"
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
                
            # Prepare the system prompt with value investing principles and consistent format
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
            
            # Extract the components from the response
            components = extract_analysis_components(response)
            
            # Add to results
            stock_analyses.append({
                'name': company_data['name'],
                'ticker': ticker,
                'recommendation': components.get('recommendation', 'N/A'),
                'summary': components.get('summary', ''),
                'strengths': components.get('strengths', []),
                'weaknesses': components.get('weaknesses', []),
                'rationale': components.get('rationale', ''),
                'price_targets': components.get('price_targets', {}),
                'metrics': components.get('metrics', {}),
                'raw_response': components.get('raw_response', response)
            })
            
            # Create an individual markdown file for the detailed company analysis
            company_filename = f"{ticker.replace('.', '_')}.md"
            company_filepath = os.path.join(model_companies_dir, company_filename)
            
            # Create an individual markdown file for the detailed company analysis
            company_markdown = f"# {company_data['name']} ({ticker}) Analysis\n\n"
            company_markdown += f"**Analysis Date:** {analysis_date}\n\n"
            
            # Always display recommendation 
            recommendation = components.get('recommendation', 'HOLD')
            if recommendation is None or recommendation.strip() == '':
                recommendation = 'HOLD'
            company_markdown += f"**Recommendation:** {recommendation}\n\n"
            
            # Add summary if available
            summary = components.get('summary', '')
            if summary:
                company_markdown += "## Summary\n\n"
                company_markdown += f"{summary}\n\n"
            
            # Add price targets if available
            price_targets = components.get('price_targets', {})
            if any(price_targets.values()):
                company_markdown += "## Price Analysis\n\n"
                if price_targets.get('current'):
                    company_markdown += f"**Current Price:** ${price_targets.get('current')}\n\n"
                if price_targets.get('intrinsic'):
                    company_markdown += f"**Intrinsic Value:** ${price_targets.get('intrinsic')}\n\n"
                if price_targets.get('margin_of_safety') is not None:
                    company_markdown += f"**Margin of Safety:** {price_targets.get('margin_of_safety')}%\n\n"
            
            # Add strengths if available
            strengths = components.get('strengths', [])
            if strengths:
                company_markdown += "## Strengths\n\n"
                for strength in strengths:
                    company_markdown += f"- {strength}\n"
                company_markdown += "\n"
            
            # Add weaknesses if available
            weaknesses = components.get('weaknesses', [])
            if weaknesses:
                company_markdown += "## Weaknesses\n\n"
                for weakness in weaknesses:
                    company_markdown += f"- {weakness}\n"
                company_markdown += "\n"
            
            # Add metrics if available
            metrics = components.get('metrics', {})
            if metrics:
                company_markdown += "## Key Metrics\n\n"
                for key, value in metrics.items():
                    # Format the metric name for better readability
                    metric_name = key.replace('_', ' ').title()
                    company_markdown += f"**{metric_name}:** {value}\n"
                company_markdown += "\n"
            
            # Add rationale if available 
            rationale = components.get('rationale', '')
            if rationale:
                company_markdown += "## Investment Rationale\n\n"
            company_markdown += f"{rationale}\n\n"
            
            # Add full AI response as a reference
            company_markdown += "## Full Analysis\n\n"
            company_markdown += "```\n"
            company_markdown += components.get('raw_response', '')[:5000]  # Limit to first 5000 chars if too long
            if len(components.get('raw_response', '')) > 5000:
                company_markdown += "\n... (truncated) ..."
            company_markdown += "\n```\n\n"
            
            # Add footer with model information
            company_markdown += "---\n\n"
            if model.startswith("claude"):
                company_markdown += "This analysis was performed using SimplyWall.st financial statements data processed through Anthropic's Claude model with extended thinking. "
            else:
                company_markdown += "This analysis was performed using SimplyWall.st financial statements data processed through OpenAI's o3-mini model. "
            company_markdown += "Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
            company_markdown += "Remember that this analysis is one input for investment decisions and should be combined with your own research and risk assessment."
            
            # Save the individual company file
            save_markdown(company_markdown, company_filepath)
            
            # Handle None values safely in format strings
            company_name = company_data.get('name', 'Unknown')
            recommendation = components.get('recommendation', 'N/A')
            if recommendation is None:
                recommendation = 'N/A'
                
            print(f"{company_name:<30} | {'✅ Complete':<20} | {recommendation:<10}")
            logger.info(f"Analyzed {company_name} ({ticker}) in {elapsed_time:.1f}s: {recommendation}")
            
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
        if len(summary) > 200:
            summary = summary[:197] + "..."
        summary = summary.replace('\n', ' ').replace('|', '/').strip()
        
        # Get top 2 strengths
        strengths = result.get('strengths', [])
        strengths_text = ", ".join(strengths[:2])
        if len(strengths) > 2:
            strengths_text += ", ..."
        strengths_text = strengths_text.replace('\n', ' ').replace('|', '/').strip()
        
        # Create link to detailed analysis
        ticker = result.get('ticker', 'unknown')
        model_short_name = "openai" if model == "o3-mini" else "claude"
        ticker_filename = ticker.replace('.', '_')
        detail_link = f"[View Details](companies/{model_short_name}/{ticker_filename}.md)"
        
        markdown += f"| {name_with_ticker} | {recommendation} | {summary} | {strengths_text} | {detail_link} |\n"
    
    markdown += "\n## Analysis Summary\n\n"
    if model.startswith("claude"):
        markdown += "This analysis was performed using SimplyWall.st financial statements data processed through Anthropic's Claude model with extended thinking. "
    else:
        markdown += "This analysis was performed using SimplyWall.st financial statements data processed through OpenAI's o3-mini model. "
    markdown += "Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
    markdown += "Remember that this analysis is one input for investment decisions and should be combined with your own research and risk assessment."
    
    # Combine the results into a final analysis
    final_markdown = format_analysis_to_markdown(stock_analyses)
    
    # Return both the markdown and the structured data for portfolio optimization
    return {
        "markdown": final_markdown,
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

def analyze_with_claude(user_prompt, client, model="claude-3-7-sonnet-20250219"):
    """Use Anthropic's Claude model to analyze financial data.
    
    Args:
        user_prompt (str): The prompt to send to Claude.
        client (Anthropic): Anthropic client instance.
        model (str, optional): Claude model to use. Defaults to "claude-3-7-sonnet-20250219".
        
    Returns:
        str: Text response from Claude.
    """
    try:
        thinking_budget = config["claude"].get("thinking_budget", 16000)
        
        # Updated system prompt with explicit formatting instructions that match our extraction patterns
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
Current Price: $[current price - ALWAYS include this exactly as provided in the data]
Intrinsic Value: $[your estimated fair value]
Margin of Safety: [percentage]%

## Investment Rationale
[Detailed explanation of your recommendation, focusing on value investing principles]

IMPORTANT: Always include the Current Price in your Price Analysis section, exactly as provided in the data. If no price is available, clearly state "Price data not available". The current price is a critical data point for any investment analysis.

Follow this format exactly as it will be parsed programmatically. Your analysis should be based on the financial statements and data provided, evaluating whether the stock is undervalued, fairly valued, or overvalued according to value investing principles.
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
        if len(summary) > 200:
            summary = summary[:197] + "..."
        summary = summary.replace('\n', ' ').replace('|', '/').strip()
        
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
    
    # Organize statements by category
    valuation_statements = []
    financial_health_statements = []
    performance_statements = []
    growth_statements = []
    dividend_statements = []
    risk_statements = []
    
    for statement in statements:
        area = statement.get('area', '').upper()
        
        if not statement.get('description'):
            continue
            
        if 'VALUATION' in area:
            valuation_statements.append(statement)
        elif 'HEALTH' in area or 'DEBT' in area or 'BALANCE' in area:
            financial_health_statements.append(statement)
        elif 'PERFORMANCE' in area or 'PROFIT' in area or 'MARGIN' in area:
            performance_statements.append(statement)
        elif 'GROWTH' in area or 'FUTURE' in area:
            growth_statements.append(statement)
        elif 'DIVIDEND' in area or 'INCOME' in area:
            dividend_statements.append(statement)
        elif 'RISK' in area or 'WARNING' in area:
            risk_statements.append(statement)
    
    # Extract key financial metrics
    financial_metrics = {}
    
    # Key metrics to look for
    metrics_to_extract = [
        ('PE_Ratio', 'Price-To-Earnings'),
        ('PB_Ratio', 'Price-To-Book'),
        ('ROE', 'Return on Equity'),
        ('ROA', 'Return on Assets'),
        ('Debt_to_Equity', 'Debt to Equity'),
        ('Dividend_Yield', 'Dividend Yield'),
        ('Payout_Ratio', 'Payout Ratio'),
        ('Operating_Margin', 'Operating Margin'),
        ('Net_Margin', 'Net Profit Margin'),
        ('Current_Ratio', 'Current Ratio'),
        ('Quick_Ratio', 'Quick Ratio'),
        ('EPS_Growth', 'Earnings Growth'),
        ('Revenue_Growth', 'Revenue Growth'),
        ('Free_Cash_Flow', 'Free Cash Flow'),
        ('Intrinsic_Value_Discount', 'Trading at')
    ]
    
    for statement in statements:
        description = statement.get('description', '')
        value = statement.get('value')
        
        for metric_key, search_term in metrics_to_extract:
            if search_term in description and value is not None:
                # Store the full description to preserve context
                financial_metrics[metric_key] = {
                    'description': description,
                    'value': value
                }
    
    # Build the prompt
    prompt = f"""
As a value investing expert, analyze this company using Benjamin Graham and Warren Buffett's principles.

## COMPANY INFORMATION
Name: {name}
Ticker: {ticker}
Exchange: {exchange}
Current Price: {current_price_formatted}
Market Cap: {market_cap_formatted}
Currency: {currency}

## FINANCIAL METRICS SUMMARY
"""
    
    # Add extracted financial metrics
    if financial_metrics:
        for key, data in financial_metrics.items():
            formatted_key = key.replace('_', ' ')
            prompt += f"- {formatted_key}: {data['description']}\n"
    else:
        prompt += "- Limited specific metrics available in the data\n"
    
    # Add detailed sections from statements
    prompt += "\n## VALUATION\n"
    if valuation_statements:
        for stmt in valuation_statements[:10]:  # Limit to top 10
            prompt += f"- {stmt.get('description', '')}\n"
    else:
        prompt += "- Limited valuation data available\n"
        
    prompt += "\n## FINANCIAL HEALTH\n"
    if financial_health_statements:
        for stmt in financial_health_statements[:10]:
            prompt += f"- {stmt.get('description', '')}\n"
    else:
        prompt += "- Limited financial health data available\n"
        
    prompt += "\n## PERFORMANCE\n"
    if performance_statements:
        for stmt in performance_statements[:10]:
            prompt += f"- {stmt.get('description', '')}\n"
    else:
        prompt += "- Limited performance data available\n"
        
    prompt += "\n## GROWTH\n"
    if growth_statements:
        for stmt in growth_statements[:10]:
            prompt += f"- {stmt.get('description', '')}\n"
    else:
        prompt += "- Limited growth data available\n"
        
    prompt += "\n## DIVIDEND INFORMATION\n"
    if dividend_statements:
        for stmt in dividend_statements[:8]:
            prompt += f"- {stmt.get('description', '')}\n"
    else:
        prompt += "- Limited dividend data available\n"
        
    prompt += "\n## RISK FACTORS\n"
    if risk_statements:
        for stmt in risk_statements[:10]:
            prompt += f"- {stmt.get('description', '')}\n"
    else:
        prompt += "- Limited risk factor data available\n"
    
    # Add full raw statements data as well (with reasonable limit)
    prompt += "\n## ALL AVAILABLE FINANCIAL STATEMENTS\n"
    statements_count = min(len(statements), 100)  # Limit to 100 statements to avoid token limits
    prompt += f"Showing {statements_count} of {len(statements)} total statements\n\n"
    
    for i, statement in enumerate(statements[:statements_count]):
        area = statement.get('area', 'GENERAL')
        description = statement.get('description', 'No description')
        value = statement.get('value', 'N/A')
        prompt += f"{i+1}. [{area}] {description} - Value: {value}\n"
    
    prompt += """
## ANALYSIS TASK
Based on the financial data provided, conduct a thorough value investing analysis, evaluating:
1. Whether the company has a sustainable competitive advantage (moat)
2. The quality of management and capital allocation
3. Financial strength and stability
4. Growth prospects and return on invested capital
5. Current valuation relative to intrinsic value
6. Margin of safety

IMPORTANT: Always include the current price and your estimate of intrinsic value in your analysis.

Then provide a clear BUY, SELL, or HOLD recommendation with detailed rationale.
"""
    
    return prompt

def extract_analysis_components(response_text):
    """Extract components from AI model's response.
    
    Args:
        response_text (str): Text response from AI model.
        
    Returns:
        dict: Dictionary with parsed components.
    """
    # Default structure for analysis components
    components = {
        "ticker": None,
        "name": None,
        "summary": None,
        "strengths": [],
        "weaknesses": [],
        "recommendation": "HOLD",  # Default to HOLD when no clear recommendation found
        "rationale": None,
        "price_targets": {"current": None, "intrinsic": None, "margin_of_safety": None},
        "metrics": {},
        "raw_response": response_text
    }
    
    # Extract ticker and name using broader patterns to catch various formats
    ticker_match = re.search(r'(?:^# |^#|^)([^(]+?)\s*\(([A-Z.]+)\)', response_text, re.MULTILINE)
    if ticker_match:
        components["name"] = ticker_match.group(1).strip()
        components["ticker"] = ticker_match.group(2).strip()
    
    # Try multiple patterns for extracting recommendation
    recommendation_patterns = [
        r'(?:^## |^#|^)Recommendation:?\s*(.*?)$',
        r'(?:^## |^#|^)Signal:?\s*(.*?)$',
        r'Recommendation:\s*(.*?)(?:\n|\.|$)',
        r'Signal:\s*(.*?)(?:\n|\.|$)',
        r'(?:^## |^#|^)Verdict:?\s*(.*?)$',
        r'(?:^## |^#|^)Conclusion:?\s*(.*?)$'
    ]
    
    for pattern in recommendation_patterns:
        recommendation_match = re.search(pattern, response_text, re.MULTILINE | re.IGNORECASE)
        if recommendation_match:
            rec = recommendation_match.group(1).strip()
            # If recommendation was found but empty, keep searching
            if rec:
                components["recommendation"] = rec
                break
    
    # Infer recommendation from response text if still missing
    if components["recommendation"] == "HOLD":
        # Look for explicit recommendation terms throughout the text
        if re.search(r'\b(?:strong buy|buy signal|undervalued|recommend buying|should buy)\b', response_text.lower()):
            components["recommendation"] = "BUY"
        elif re.search(r'\b(?:strong sell|sell signal|overvalued|recommend selling|should sell)\b', response_text.lower()):
            components["recommendation"] = "SELL"
    
    # Extract strengths
    strengths_section = re.search(r'(?:^## |^)Strengths:?\s*(.*?)(?=(?:^## |^#|$))', response_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if strengths_section:
        strengths_text = strengths_section.group(1).strip()
        # Try list pattern first (numbered or bullet points)
        strengths = re.findall(r'^[0-9.*-]+\s*(.*?)$', strengths_text, re.MULTILINE)
        if strengths:
            components["strengths"] = [s.strip() for s in strengths if s.strip()]
        else:
            # Try alternative format - split by lines
            strengths = [s.strip() for s in strengths_text.split('\n') if s.strip()]
            if strengths:
                components["strengths"] = strengths
    
    # Extract weaknesses
    weaknesses_section = re.search(r'(?:^## |^)Weaknesses:?\s*(.*?)(?=(?:^## |^#|$))', response_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if weaknesses_section:
        weaknesses_text = weaknesses_section.group(1).strip()
        # Try list pattern first
        weaknesses = re.findall(r'^[0-9.*-]+\s*(.*?)$', weaknesses_text, re.MULTILINE)
        if weaknesses:
            components["weaknesses"] = [w.strip() for w in weaknesses if w.strip()]
        else:
            # Try alternative format - split by lines
            weaknesses = [w.strip() for w in weaknesses_text.split('\n') if w.strip()]
            if weaknesses:
                components["weaknesses"] = weaknesses
    
    # Extract rationale
    rationale_section = re.search(r'(?:^## |^)Rationale:?\s*(.*?)(?=(?:^## |^#|$))', response_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    if rationale_section:
        components["rationale"] = rationale_section.group(1).strip()
    else:
        # Try alternative patterns like "Analysis" or "Value Assessment"
        for alt_pattern in ["Analysis", "Value Assessment", "Investment Thesis"]:
            alt_section = re.search(fr'(?:^## |^){alt_pattern}:?\s*(.*?)(?=(?:^## |^#|$))', 
                                   response_text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
            if alt_section:
                components["rationale"] = alt_section.group(1).strip()
                break
    
    # If no rationale found, extract a summary from the text
    if not components["rationale"]:
        # Find first substantive paragraph after any headers
        summary_match = re.search(r'(?:^#.*?\n+)(.*?)(?=\n\n|\n#)', response_text, re.DOTALL)
        if summary_match:
            components["rationale"] = summary_match.group(1).strip()
    
    # Extract price targets
    price_match = re.search(r'(?:Current\s+Price|Current\s+price|Price):\s*\$?\s*([\d,.]+)', response_text, re.IGNORECASE)
    if price_match:
        components["price_targets"]["current"] = float(price_match.group(1).replace(',', ''))
    
    intrinsic_match = re.search(r'(?:Intrinsic\s+Value|Fair\s+Value|Target\s+Price):\s*\$?\s*([\d,.]+)', response_text, re.IGNORECASE)
    if intrinsic_match:
        components["price_targets"]["intrinsic"] = float(intrinsic_match.group(1).replace(',', ''))
    
    margin_match = re.search(r'Margin\s+of\s+Safety:?\s*([+-]?\d+(?:\.\d+)?)\s*%', response_text, re.IGNORECASE)
    if margin_match:
        components["price_targets"]["margin_of_safety"] = float(margin_match.group(1))
    
    # Extract financial metrics
    pe_match = re.search(r'P/E(?:\s+Ratio)?:\s*([\d.]+)', response_text, re.IGNORECASE)
    if pe_match:
        components["metrics"]["pe_ratio"] = float(pe_match.group(1))
    
    pb_match = re.search(r'P/B(?:\s+Ratio)?:\s*([\d.]+)', response_text, re.IGNORECASE)
    if pb_match:
        components["metrics"]["pb_ratio"] = float(pb_match.group(1))
    
    dividend_match = re.search(r'Dividend\s+Yield:\s*([\d.]+)%', response_text, re.IGNORECASE)
    if dividend_match:
        components["metrics"]["dividend_yield"] = float(dividend_match.group(1))
    
    roe_match = re.search(r'ROE:\s*([\d.]+)%', response_text, re.IGNORECASE)
    if roe_match:
        components["metrics"]["roe"] = float(roe_match.group(1))
    
    # Extract summary (first paragraph or section of the response)
    summary_match = re.search(r'^(?:#.*\n+)?(.*?)(?=\n\n|\n#)', response_text, re.DOTALL)
    if summary_match:
        components["summary"] = summary_match.group(1).strip()
    
    # If no strengths or weaknesses found, try to extract them from key sentences using keywords
    if not components["strengths"]:
        # Look for positive assessment statements
        strength_mentions = re.findall(r'(?:strong|solid|impressive|excellent|positive|good|high)\s+(?:\w+\s+){0,3}(?:balance sheet|cash flow|growth|profitability|margin|revenue|management|position|advantage)', response_text, re.IGNORECASE)
        if strength_mentions:
            components["strengths"] = [s.strip() for s in strength_mentions[:5]]
    
    if not components["weaknesses"]:
        # Look for negative assessment statements
        weakness_mentions = re.findall(r'(?:weak|poor|low|concerning|negative|declining|high)\s+(?:\w+\s+){0,3}(?:debt|valuation|competition|risk|expense|cost|margin|growth|revenue|profit)', response_text, re.IGNORECASE)
        if weakness_mentions:
            components["weaknesses"] = [w.strip() for w in weakness_mentions[:5]]
    
    return components 