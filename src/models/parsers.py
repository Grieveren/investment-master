"""
Parsing module for stock analysis results.

This module contains functions for parsing and extracting structured
data from AI-generated analysis responses.
"""

import re
import datetime

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