"""
Prompting module for financial analysis.

This module contains functions for building and processing prompts for financial analysis.
"""

import re
from src.core.logger import logger

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

def format_statement(stmt):
    """Format a financial statement for inclusion in the analysis prompt.
    
    Args:
        stmt (dict): Financial statement data
        
    Returns:
        str: Formatted statement string
    """
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

def get_openai_system_prompt():
    """Get the system prompt for OpenAI analysis.
    
    Returns:
        str: System prompt for OpenAI
    """
    return """You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham.

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