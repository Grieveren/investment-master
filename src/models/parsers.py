"""
Parsing module for stock analysis results.

This module contains functions for parsing and extracting structured
data from AI-generated analysis responses.
"""

import re as _re
import datetime as _datetime

def _extract_recommendation(response):
    """Extract BUY/SELL/HOLD recommendation from the response.
    
    Args:
        response (str): AI model response text
        
    Returns:
        str or None: Normalized recommendation or None if not found
    """
    recommendation_match = _re.search(r'(?:^## |^#|^)Recommendation:?\s*(.*?)$', response, _re.MULTILINE | _re.IGNORECASE)
    if recommendation_match:
        recommendation = recommendation_match.group(1).strip()
        # Normalize to just BUY, SELL, or HOLD
        if 'buy' in recommendation.lower():
            return 'BUY'
        elif 'sell' in recommendation.lower():
            return 'SELL'
        elif 'hold' in recommendation.lower():
            return 'HOLD'
        else:
            return recommendation
    return None

def _extract_section_content(response, section_name):
    """Extract content from a specific section of the analysis.
    
    Args:
        response (str): AI model response text
        section_name (str): Name of the section to extract
        
    Returns:
        str or None: Section content or None if not found
    """
    pattern = r'(?:^## |^#|^){}:?\s*(.*?)(?=(?:^## |^#|$))'.format(section_name)
    match = _re.search(pattern, response, _re.MULTILINE | _re.DOTALL | _re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def _extract_bullet_points(section_text):
    """Extract bullet points from a section.
    
    Args:
        section_text (str): Text of a section containing bullet points
        
    Returns:
        list: List of bullet point items
    """
    if not section_text:
        return []
        
    items = _re.findall(r'^-\s*(.*?)$', section_text, _re.MULTILINE)
    return [item.strip() for item in items if item.strip()]

def _extract_price_targets(response):
    """Extract price targets and valuation metrics from the price analysis section.
    
    Args:
        response (str): AI model response text
        
    Returns:
        dict: Dictionary of price targets and metrics
    """
    price_targets = {}
    
    # First get the price analysis section
    price_analysis = _extract_section_content(response, "Price Analysis")
    if not price_analysis:
        return price_targets
    
    # Extract current price
    current_price_match = _re.search(r'Current Price:.*?[$€£¥]([0-9.,]+)', price_analysis, _re.IGNORECASE)
    if current_price_match:
        try:
            # Handle potential commas in number format
            price_str = current_price_match.group(1).replace(',', '')
            price_targets['current_price'] = float(price_str)
        except (ValueError, IndexError):
            pass
    
    # Extract intrinsic value
    intrinsic_match = _re.search(r'Intrinsic Value:.*?[$€£¥]([0-9.,]+)', price_analysis, _re.IGNORECASE)
    if intrinsic_match:
        try:
            value_str = intrinsic_match.group(1).replace(',', '')
            price_targets['intrinsic_value'] = float(value_str)
        except (ValueError, IndexError):
            pass
    
    # Extract margin of safety
    safety_match = _re.search(r'Margin of Safety:.*?([0-9.,]+)%', price_analysis, _re.IGNORECASE)
    if safety_match:
        try:
            safety_str = safety_match.group(1).replace(',', '')
            price_targets['margin_of_safety'] = float(safety_str)
        except (ValueError, IndexError):
            pass
            
    # Extract valuation method
    valuation_method_match = _re.search(r'Valuation Method\(s\):.*?([^\n]+)', price_analysis, _re.IGNORECASE)
    if valuation_method_match:
        price_targets['valuation_method'] = valuation_method_match.group(1).strip()
    
    return price_targets

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
        'competitive_analysis': None,
        'management_assessment': None,
        'financial_health': None,
        'growth_prospects': None,
        'risk_factors': None
    }
    
    # Extract individual components using helper functions
    components['recommendation'] = _extract_recommendation(response)
    components['summary'] = _extract_section_content(response, "Summary")
    
    # Extract bullet point lists
    strengths_section = _extract_section_content(response, "Strengths")
    components['strengths'] = _extract_bullet_points(strengths_section)
    
    weaknesses_section = _extract_section_content(response, "Weaknesses")
    components['weaknesses'] = _extract_bullet_points(weaknesses_section)
    
    # Extract price targets
    components['price_targets'] = _extract_price_targets(response)
    
    # Extract other narrative sections
    components['rationale'] = _extract_section_content(response, "Investment Rationale")
    components['competitive_analysis'] = _extract_section_content(response, "Competitive Analysis")
    components['management_assessment'] = _extract_section_content(response, "Management Assessment")
    components['financial_health'] = _extract_section_content(response, "Financial Health")
    components['growth_prospects'] = _extract_section_content(response, "Growth Prospects")
    components['risk_factors'] = _extract_section_content(response, "Risk Factors")
    
    return components

def _truncate_and_format_text(text, max_length=200):
    """Truncate and format text for markdown table cells.
    
    Args:
        text (str): Text to format
        max_length (int): Maximum length before truncation
        
    Returns:
        str: Formatted text
    """
    if not text:
        return "No information provided"
        
    formatted = text.replace('\n', ' ').replace('|', '/').strip()
    
    if len(formatted) > max_length:
        return formatted[:max_length-3] + "..."
    
    return formatted

def _format_list_for_table(items, max_items=2):
    """Format a list of items for a markdown table cell.
    
    Args:
        items (list): List of items
        max_items (int): Maximum number of items to include
        
    Returns:
        str: Comma-separated list with ellipsis if truncated
    """
    if not items:
        return ""
        
    text = ", ".join(items[:max_items])
    if len(items) > max_items:
        text += ", ..."
    
    return text

def format_analysis_to_markdown(stock_analyses):
    """Format stock analyses into markdown.
    
    Args:
        stock_analyses (list): List of dictionaries with stock analysis results.
        
    Returns:
        str: Markdown-formatted analysis.
    """
    # Combine all analyses into a single markdown table
    markdown_output = "# Portfolio Value Investing Analysis\n\n"
    markdown_output += f"Analysis Date: {_datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
    
    # Create the table header
    markdown_output += "| Stock (Ticker) | Recommendation | Summary | Key Strengths | Key Weaknesses |\n"
    markdown_output += "|----------------|---------------|---------|--------------|----------------|\n"
    
    # Add each stock's analysis to the table
    for analysis in stock_analyses:
        name = analysis.get('name', 'Unknown')
        ticker = analysis.get('ticker', 'N/A')
        name_with_ticker = f"{name} ({ticker})"
        
        recommendation = analysis.get('recommendation', 'N/A')
        
        # Format summary and key points using helper functions
        summary = _truncate_and_format_text(analysis.get('summary', 'No summary provided'))
        strengths_text = _format_list_for_table(analysis.get('strengths', []))
        weaknesses_text = _format_list_for_table(analysis.get('weaknesses', []))
        
        # Format cells for markdown table
        markdown_output += f"| {name_with_ticker} | {recommendation} | {summary} | {strengths_text} | {weaknesses_text} |\n"
    
    # Add summary and notes
    markdown_output += "\n## Analysis Summary\n\n"
    markdown_output += "This analysis was performed using SimplyWall.st financial statements data processed through AI analysis. "
    markdown_output += "Each recommendation is based on value investing principles, focusing on company fundamentals, competitive advantages, and margin of safety.\n\n"
    markdown_output += "Remember that this analysis is one input for investment decisions and should be combined with your own research and risk assessment."
    
    return markdown_output 