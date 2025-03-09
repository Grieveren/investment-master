"""
Debug script to test the Claude API connection and prompt generation
"""

import os
import json
import sys
from dotenv import load_dotenv
import anthropic
from utils.logger import logger
from utils.config import config
from utils.portfolio_optimizer import parse_portfolio_csv
from claude_portfolio_optimizer import read_company_analyses, create_claude_portfolio_prompt

def test_claude_connection():
    """Test the connection to Claude API."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Anthropic API key not found in environment variables.")
        return False
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        print("Successfully created Anthropic client.")
        
        # Test a simple API call
        print("Testing API connection with a simple message...")
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Hello, Claude. This is a test message. Please respond with only one sentence."}
            ]
        )
        
        print(f"Response from Claude: {message.content[0].text}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to connect to Claude API: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prompt_creation():
    """Test generating the portfolio optimization prompt."""
    # Parse portfolio data
    csv_path = config["portfolio"]["csv_file"]
    print(f"Parsing portfolio data from CSV: {csv_path}")
    portfolio_data = parse_portfolio_csv(csv_path)
    
    if not portfolio_data:
        print("ERROR: Failed to parse portfolio data.")
        return False
    
    # Read company analyses
    print("Reading company analyses...")
    analyses = read_company_analyses()
    
    if not analyses:
        print("ERROR: Failed to read company analyses.")
        return False
    
    # Create prompt
    print("Creating portfolio optimization prompt...")
    prompt = create_claude_portfolio_prompt(portfolio_data, analyses)
    
    # Print prompt length and preview
    print(f"Prompt length: {len(prompt)} characters")
    print(f"Using FULL company analyses (not just extracts)")
    print(f"Using Claude thinking budget: {config['claude'].get('thinking_budget', 16000)} tokens")
    
    # Count total words in the prompt as a rough estimate of tokens
    word_count = len(prompt.split())
    print(f"Estimated word count: {word_count} (roughly {word_count * 0.75:.0f} tokens)")
    
    print("\nPrompt preview (first 500 characters):")
    print(prompt[:500])
    print("...")
    
    # Print each ticker in the prompt
    tickers_found = []
    for ticker in analyses.keys():
        if ticker in prompt:
            tickers_found.append(ticker)
    
    print(f"\nFound analyses for {len(tickers_found)} tickers in prompt: {', '.join(tickers_found)}")
    
    print("\nPrompt end (last 500 characters):")
    print(prompt[-500:])
    
    return True

if __name__ == "__main__":
    load_dotenv()
    print("Testing Claude connection and prompt generation...")
    
    # Test Claude connection
    print("\n=== Testing Claude API Connection ===")
    api_success = test_claude_connection()
    
    if api_success:
        # Test prompt creation
        print("\n=== Testing Prompt Creation ===")
        prompt_success = test_prompt_creation()
        
        if prompt_success:
            print("\nAll tests completed successfully.")
        else:
            print("\nPrompt creation test failed.")
    else:
        print("\nClaude API connection test failed.")
    
    print("\nTest complete.") 