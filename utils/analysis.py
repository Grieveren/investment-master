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
            if price_targets:
                company_markdown += "## Price Analysis\n\n"
                
                # Current price
                current_price = price_targets.get('current_price')
                if current_price is not None:
                    company_markdown += f"**Current Price:** ${current_price:.2f}\n\n"
                
                # Intrinsic value
                intrinsic_value = price_targets.get('intrinsic_value')
                if intrinsic_value is not None:
                    company_markdown += f"**Intrinsic Value:** ${intrinsic_value:.2f}\n\n"
                
                # Margin of safety
                margin_of_safety = price_targets.get('margin_of_safety')
                if margin_of_safety is not None:
                    company_markdown += f"**Margin of Safety:** {margin_of_safety:.1f}%\n\n"
                
                # Valuation method (new field from enhanced analysis)
                valuation_method = price_targets.get('valuation_method')
                if valuation_method:
                    company_markdown += f"**Valuation Method(s):** {valuation_method}\n\n"
            
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
            
            # Add competitive analysis if available (new section from enhanced analysis)
            competitive_analysis = components.get('competitive_analysis', '')
            if competitive_analysis:
                company_markdown += "## Competitive Analysis\n\n"
                company_markdown += f"{competitive_analysis}\n\n"
            
            # Add management assessment if available (new section from enhanced analysis)
            management_assessment = components.get('management_assessment', '')
            if management_assessment:
                company_markdown += "## Management Assessment\n\n"
                company_markdown += f"{management_assessment}\n\n"
            
            # Add financial health if available (new section from enhanced analysis)
            financial_health = components.get('financial_health', '')
            if financial_health:
                company_markdown += "## Financial Health\n\n"
                company_markdown += f"{financial_health}\n\n"
            
            # Add growth prospects if available (new section from enhanced analysis)
            growth_prospects = components.get('growth_prospects', '')
            if growth_prospects:
                company_markdown += "## Growth Prospects\n\n"
                company_markdown += f"{growth_prospects}\n\n"
            
            # Add investment rationale if available
            rationale = components.get('rationale', '')
            if rationale:
                company_markdown += "## Investment Rationale\n\n"
                company_markdown += f"{rationale}\n\n"
            
            # Add risk factors if available (new section from enhanced analysis)
            risk_factors = components.get('risk_factors', '')
            if risk_factors:
                company_markdown += "## Risk Factors\n\n"
                company_markdown += f"{risk_factors}\n\n"
            
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
                thinking_budget = config["claude"].get("thinking_budget", 32000)
                company_markdown += f"This analysis was performed using SimplyWall.st financial statements data processed through Anthropic's Claude model with {thinking_budget} tokens of thinking budget. "
                company_markdown += "The enhanced analysis includes comprehensive evaluation of all available financial data. "
                company_markdown += "Streaming was used to provide real-time feedback during the analysis process. "
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
        thinking_budget = config["claude"].get("thinking_budget", 32000)
        
        # Enhanced system prompt with detailed guidance for using extended thinking time
        system_prompt = """You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham.

You have been given extended thinking time to perform an exceptionally thorough analysis of a company. Use this time to:

1. Carefully examine all financial statements and metrics provided
2. Calculate intrinsic value using multiple approaches (DCF, multiples, etc.)
3. Assess competitive advantages and durability of the business model
4. Evaluate management quality and capital allocation decisions
5. Consider industry dynamics, competitive threats, and macroeconomic factors
6. Identify potential catalysts and risks not explicitly mentioned in the data
7. Calculate a reasonable margin of safety based on risk factors

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

## Competitive Analysis
[One paragraph assessment of the company's competitive position and moat]

## Management Assessment
[One paragraph evaluation of management quality and capital allocation]

## Financial Health
[Analysis of balance sheet, cash flow, and financial stability]

## Growth Prospects
[Analysis of growth drivers, market opportunities, and threats]

## Price Analysis
Current Price: $[current price - ALWAYS include this exactly as provided in the data]
Intrinsic Value: $[your estimated fair value]
Margin of Safety: [percentage]%
Valuation Method(s): [Brief description of valuation method(s) used]

## Investment Rationale
[Detailed explanation of your recommendation, focusing on value investing principles]

## Risk Factors
[List and analysis of key risks that could impact the investment thesis]

IMPORTANT: Always include the Current Price in your Price Analysis section, exactly as provided in the data. If no price is available, clearly state "Price data not available". The current price is a critical data point for any investment analysis.

This format will be used to guide investment decisions, so be thorough and objective. This is an enhanced analysis using comprehensive data, so provide detailed insights beyond a typical stock report.
"""
        
        logger.info(f"Requesting detailed company analysis from Claude ({model}) with {thinking_budget} token thinking budget...")
        print(f"Starting analysis with {thinking_budget} token thinking budget...")
        print("This will take some time. Progress will be shown as Claude processes the data...")
        
        start_time = time.time()
        
        # Variables to track streaming progress
        full_response = ""
        current_thinking = ""
        current_text = ""
        thinking_in_progress = False
        text_in_progress = False
        thinking_chunks = 0
        text_chunks = 0
        last_progress_time = time.time()
        progress_interval = 5  # Show progress every 5 seconds
        
        # Use streaming to get the response
        with client.messages.stream(
            model=model,
            max_tokens=thinking_budget + 5000,  # Ensure max_tokens is greater than thinking_budget
            thinking={"type": "enabled", "budget_tokens": thinking_budget},
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=1.0  # Must be 1.0 when thinking is enabled
        ) as stream:
            # Display initial progress message
            print("Claude's thinking process has started...")
            
            # Process the streaming events
            for event in stream:
                current_time = time.time()
                
                # Handle message start
                if event.type == "message_start":
                    pass
                
                # Handle content block start
                elif event.type == "content_block_start":
                    if event.content_block.type == "thinking":
                        thinking_in_progress = True
                        text_in_progress = False
                        thinking_chunks = 0
                        if current_time - last_progress_time > progress_interval:
                            print("Claude is analyzing the company data...")
                            last_progress_time = current_time
                    elif event.content_block.type == "text":
                        text_in_progress = True
                        thinking_in_progress = False
                        text_chunks = 0
                        print("\nAnalysis complete! Claude is now generating the report...")
                
                # Handle content block delta (the actual content chunks)
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "thinking") and thinking_in_progress:
                        thinking_chunk = event.delta.thinking
                        current_thinking += thinking_chunk
                        thinking_chunks += 1
                        # Periodically show progress for thinking
                        if current_time - last_progress_time > progress_interval:
                            elapsed = current_time - start_time
                            print(f"Still thinking... ({elapsed:.1f}s elapsed, {thinking_chunks} thinking chunks processed)")
                            last_progress_time = current_time
                    elif hasattr(event.delta, "text") and text_in_progress:
                        text_chunk = event.delta.text
                        current_text += text_chunk
                        text_chunks += 1
                        # Show progress for text generation
                        if text_chunks % 20 == 0:  # Show more frequent updates for text
                            progress_char = "." * (text_chunks // 20 % 4 + 1)
                            print(f"Generating report{progress_char}", end="\r")
                
                # Handle content block stop
                elif event.type == "content_block_stop":
                    if thinking_in_progress:
                        thinking_in_progress = False
                        logger.info(f"Thinking complete: {len(current_thinking)} characters in {thinking_chunks} chunks")
                    elif text_in_progress:
                        text_in_progress = False
                        logger.info(f"Text complete: {len(current_text)} characters in {text_chunks} chunks")
                
                # Handle message delta
                elif event.type == "message_delta":
                    if event.delta.stop_reason:
                        logger.info(f"Message stopped with reason: {event.delta.stop_reason}")
                
                # Handle message stop (end of stream)
                elif event.type == "message_stop":
                    full_response = current_text
                    logger.info("Streaming complete")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Claude company analysis completed in {elapsed_time:.1f}s")
        print(f"\nCompany analysis complete! (took {elapsed_time:.1f} seconds)")
        
        return full_response
        
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