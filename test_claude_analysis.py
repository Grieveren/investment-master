#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script for verifying Claude implementation with extended thinking.
This allows testing the Claude analysis functionality without running the entire portfolio analysis.
"""

import os
import json
import logging
import argparse
from dotenv import load_dotenv
import anthropic
import sys
from datetime import datetime

# Add the project root to the path so we can import the utils modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the analysis module
from utils.analysis import create_anthropic_client

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('claude_test')

def load_sample_data(sample_file="sample_stock_data.json"):
    """Load sample stock data for testing."""
    try:
        with open(sample_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Sample data file {sample_file} not found.")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error parsing sample data file {sample_file}.")
        return None

def get_sample_data():
    """Create a minimal sample data structure for testing."""
    # This is a fallback if no sample file is available
    return {
        "company": {
            "name": "Test Company",
            "ticker": "TEST",
            "exchange": "NASDAQ",
            "description": "A fictitious company for testing purposes."
        },
        "financial_data": {
            "pe_ratio": 15.5,
            "price_to_book": 2.3,
            "debt_to_equity": 0.8,
            "revenue_growth": 12.5,
            "profit_margin": 8.7,
            "dividend_yield": 2.1,
            "free_cash_flow": 500000000
        },
        "valuation": {
            "intrinsic_value": 150,
            "current_price": 120,
            "margin_of_safety": 20
        }
    }

def build_analysis_prompt(sample_data):
    """Build a comprehensive analysis prompt based on the available data."""
    prompt = f"""
    You are a value investing expert analyzing stock data.
    
    Stock Information:
    Company: {sample_data['company']['name']} ({sample_data['company']['ticker']} on {sample_data['company']['exchange']})
    Description: {sample_data['company'].get('description', 'No description available')}
    
    Financial Data:
    - P/E Ratio: {sample_data['financial_data']['pe_ratio']}
    - Price to Book: {sample_data['financial_data']['price_to_book']}
    - Debt to Equity: {sample_data['financial_data']['debt_to_equity']}
    - Revenue Growth: {sample_data['financial_data']['revenue_growth']}%
    - Profit Margin: {sample_data['financial_data']['profit_margin']}%
    - Dividend Yield: {sample_data['financial_data']['dividend_yield']}%
    - Free Cash Flow: ${sample_data['financial_data']['free_cash_flow']:,}
    """
    
    # Add additional financial metrics if available
    additional_metrics = ['return_on_equity', 'earnings_growth_5yr', 'current_ratio']
    for metric in additional_metrics:
        if metric in sample_data['financial_data']:
            metric_name = metric.replace('_', ' ').title()
            prompt += f"- {metric_name}: {sample_data['financial_data'][metric]}"
            if metric == 'return_on_equity' or metric == 'earnings_growth_5yr':
                prompt += "%\n"
            else:
                prompt += "\n"
    
    prompt += f"""
    Valuation:
    - Estimated Intrinsic Value: ${sample_data['valuation']['intrinsic_value']}
    - Current Price: ${sample_data['valuation']['current_price']}
    - Margin of Safety: {sample_data['valuation']['margin_of_safety']}%
    """
    
    # Add industry comparison if available
    if 'industry_comparison' in sample_data:
        prompt += "\nIndustry Comparison:\n"
        for key, value in sample_data['industry_comparison'].items():
            metric_name = key.replace('_', ' ').replace('sector', 'sector').title()
            prompt += f"- {metric_name}: {value}"
            if 'average' in key:
                prompt += "\n"
    
    # Add risk factors if available
    if 'risk_factors' in sample_data and sample_data['risk_factors']:
        prompt += "\nRisk Factors:\n"
        for risk in sample_data['risk_factors']:
            prompt += f"- {risk}\n"
    
    # Add growth catalysts if available
    if 'growth_catalysts' in sample_data and sample_data['growth_catalysts']:
        prompt += "\nGrowth Catalysts:\n"
        for catalyst in sample_data['growth_catalysts']:
            prompt += f"- {catalyst}\n"
    
    prompt += """
    Based on the principles of value investing, analyze this stock and provide:
    1. Whether this appears to be undervalued or overvalued
    2. Key strengths and weaknesses from a value investing perspective
    3. A recommendation (Buy, Hold, or Sell) with explanation
    4. Any potential red flags for value investors
    
    Format your response in a structured way with clear headings.
    """
    
    return prompt

def test_claude_analysis(api_key=None, sample_data=None, model="claude-3-7-sonnet-20250219", save_prompt=False):
    """Test the Claude analysis with extended thinking."""
    logger.info(f"Testing Claude analysis with model {model}")
    
    if not api_key:
        load_dotenv()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.error("No Anthropic API key found. Please provide one or set ANTHROPIC_API_KEY in your .env file.")
            return False
    
    try:
        logger.info("Creating Anthropic client...")
        client = create_anthropic_client(api_key)
        logger.info("Anthropic client created successfully")
    except Exception as e:
        logger.error(f"Error creating Anthropic client: {e}")
        return False
    
    if not sample_data:
        sample_data = get_sample_data()
    
    prompt = build_analysis_prompt(sample_data)
    
    # Save prompt to file if requested
    if save_prompt:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f"claude_prompt_{timestamp}.txt", "w") as f:
            f.write(prompt)
        logger.info(f"Prompt saved to claude_prompt_{timestamp}.txt")
    
    logger.info("Sending analysis request to Claude with extended thinking...")
    
    try:
        # Using extended thinking as specified in documentation
        response = client.messages.create(
            model=model,
            max_tokens=20000,  # Increased to be greater than thinking budget
            system="You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            thinking={"type": "enabled", "budget_tokens": 16000},
            temperature=1.0  # Must be 1.0 when thinking is enabled
        )
        
        logger.info("Received response from Claude")
        
        # Log thinking content if available
        thinking_content = None
        for block in response.content:
            if isinstance(block, anthropic.types.ThinkingBlock):
                thinking_content = block.thinking
                break
                
        if thinking_content:
            logger.info(f"Extended thinking used {len(thinking_content)} characters")
            
            # Write thinking to file for inspection
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            with open(f"claude_thinking_{timestamp}.txt", "w") as f:
                f.write(thinking_content)
            logger.info(f"Saved thinking content to claude_thinking_{timestamp}.txt")
        
        # Extract and return the text response
        text_content = ""
        for block in response.content:
            if isinstance(block, anthropic.types.TextBlock):
                text_content += block.text
        
        # Save the full response to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        with open(f"claude_response_{timestamp}.txt", "w") as f:
            f.write(text_content)
        logger.info(f"Saved response to claude_response_{timestamp}.txt")
        
        logger.info("Analysis completed successfully")
        
        return text_content
        
    except Exception as e:
        logger.error(f"Error during Claude analysis: {e}")
        return f"Error: {e}"

def parse_args():
    parser = argparse.ArgumentParser(description='Test Claude analysis with extended thinking')
    parser.add_argument('--sample-file', type=str, help='Path to sample stock data JSON file')
    parser.add_argument('--model', type=str, default='claude-3-7-sonnet-20250219', 
                      help='Claude model to use (default: claude-3-7-sonnet-20250219)')
    parser.add_argument('--save-prompt', action='store_true', help='Save the generated prompt to a file')
    parser.add_argument('--api-key', type=str, help='Anthropic API key (overrides .env file)')
    return parser.parse_args()

def main():
    args = parse_args()
    
    print("=== Claude Analysis Test ===")
    print(f"Testing with model: {args.model}")
    
    sample_data = None
    if args.sample_file:
        sample_data = load_sample_data(args.sample_file)
        if sample_data:
            print(f"Using sample data from: {args.sample_file}")
        else:
            print("Using default sample data")
    else:
        print("Using default sample data")
    
    result = test_claude_analysis(
        api_key=args.api_key,
        sample_data=sample_data, 
        model=args.model,
        save_prompt=args.save_prompt
    )
    
    if result:
        print("\n=== Analysis Result ===")
        print(result)
    else:
        print("\nTest failed. Check logs for details.")

if __name__ == "__main__":
    main() 