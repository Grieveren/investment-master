"""
Portfolio Analyzer - Value Investing Analysis Tool

This script analyzes a portfolio of stocks using financial data from SimplyWall.st
and generates a value investing analysis using OpenAI's o3-mini model.

Features:
- Parses portfolio data from a markdown file
- Fetches detailed financial data from SimplyWall.st GraphQL API
- Processes ALL statements data (166 per company) for comprehensive analysis
- Leverages OpenAI's o3-mini model (200K token context window) for analysis
- Generates buy/sell/hold recommendations with rationales
- Saves raw API data and analysis results to files

Requirements:
- Python 3.6+
- SimplyWall.st API token
- OpenAI API key

Usage:
1. Create a .env file with your API keys
2. Run the script: python portfolio_analyzer.py
3. Review the generated analysis in portfolio_analysis.md
"""

import os
import re
import json
import requests
import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# API keys
SWS_API_TOKEN = os.getenv("SWS_API_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Print debug info
print(f"OpenAI API Key: {OPENAI_API_KEY[:8]}...{OPENAI_API_KEY[-4:] if OPENAI_API_KEY else 'None'}")

# API endpoints
SWS_API_URL = "https://api.simplywall.st/graphql"

# Initialize OpenAI client (only if key is available)
client = None
if OPENAI_API_KEY and not OPENAI_API_KEY.startswith("your_"):
    client = OpenAI(api_key=OPENAI_API_KEY)

def parse_portfolio():
    """Parse the portfolio data from combined_portfolio.md"""
    with open("combined_portfolio.md", "r") as f:
        content = f.read()
    
    stocks = []
    
    for line in content.split('\n'):
        if '|' in line and not line.startswith('|--') and "Cash EUR" not in line:
            parts = [part.strip() for part in line.split('|')]
            if len(parts) >= 6 and parts[1] != "Security" and "Cash" not in parts[1]:
                try:
                    stocks.append({
                        "name": parts[1].strip(),
                        "shares": int(parts[2].strip()),
                        "current_price": float(parts[3].strip()),
                        "market_value": float(parts[4].strip().replace(',', '')),
                        "weight": float(parts[5].strip().replace('%', ''))
                    })
                except (ValueError, IndexError) as e:
                    print(f"Error parsing line: {line}, Error: {e}")
    
    return stocks

def get_stock_ticker_and_exchange(stock_name):
    """Map stock names to tickers and exchanges for the API"""
    stock_map = {
        "Berkshire Hathaway B": {"ticker": "BRK.B", "exchange": "NYSE"},
        "Allianz SE": {"ticker": "ALV", "exchange": "XETRA"},
        "GitLab Inc.": {"ticker": "GTLB", "exchange": "NasdaqGS"},
        "NVIDIA": {"ticker": "NVDA", "exchange": "NasdaqGS"},
        "Microsoft": {"ticker": "MSFT", "exchange": "NasdaqGS"},
        "Alphabet C": {"ticker": "GOOG", "exchange": "NasdaqGS"},
        "CrowdStrike": {"ticker": "CRWD", "exchange": "NasdaqGS"},
        "Advanced Micro Devices": {"ticker": "AMD", "exchange": "NasdaqGS"},
        "Nutanix": {"ticker": "NTNX", "exchange": "NasdaqGS"},
        "ASML Holding": {"ticker": "ASML", "exchange": "NasdaqGS"},
        "Taiwan Semiconductor ADR": {"ticker": "TSM", "exchange": "NYSE"}
    }
    
    return stock_map.get(stock_name)

def fetch_company_data(ticker, exchange):
    """Fetch company data from SimplyWall.st GraphQL API"""
    query = """
    query companyByExchangeAndTickerSymbol($exchange: String!, $symbol: String!) {
      companyByExchangeAndTickerSymbol(exchange: $exchange, tickerSymbol: $symbol) {
        id
        name
        exchangeSymbol
        tickerSymbol
        marketCapUSD
        statements {
          name
          title
          area
          type
          value
          outcome
          description
          severity
          outcomeName
        }
      }
    }
    """
    
    variables = {
        "exchange": exchange,
        "symbol": ticker
    }
    
    headers = {
        "Authorization": f"Bearer {SWS_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            SWS_API_URL,
            headers=headers,
            json={"query": query, "variables": variables}
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {ticker} on {exchange}: {e}")
        if response.status_code != 200:
            print(f"Response: {response.text}")
        return None

def get_value_investing_signals(portfolio_data, api_data):
    """Use OpenAI's o3-mini model to analyze stocks and provide buy/sell signals
    
    This function processes all available financial statements (166 per company)
    from SimplyWall.st and sends them to OpenAI's o3-mini model, which has a 
    200K token context window capable of handling the full dataset.
    
    Args:
        portfolio_data (list): List of stock dictionaries with name, shares, price, etc.
        api_data (dict): Dictionary of API responses from SimplyWall.st
        
    Returns:
        str: Markdown-formatted analysis with buy/sell/hold signals for each stock
    """
    # Check if client is available
    if client is None:
        return "Error: OpenAI client not initialized. Please check your API key."
        
    # Convert the data to a more digestible format for the AI
    stock_analysis_data = []
    
    for stock in portfolio_data:
        stock_info = get_stock_ticker_and_exchange(stock["name"])
        if not stock_info:
            print(f"Skipping {stock['name']} - no ticker/exchange info")
            continue
            
        ticker = stock_info["ticker"]
        stock_data = api_data.get(stock["name"])
        
        print(f"Processing {stock['name']} ({ticker})...")
        
        # Check if we have data for this stock
        if stock_data is None:
            print(f"No API data found for {stock['name']}")
            stock_analysis_data.append({
                "name": stock["name"],
                "ticker": ticker,
                "shares": stock["shares"],
                "current_price": stock["current_price"],
                "market_value": stock["market_value"],
                "weight": stock["weight"],
                "statements": [],
                "no_data": True
            })
            continue
        
        # Extract ALL statements data for analysis
        all_statements = []
        if isinstance(stock_data, dict) and "data" in stock_data:
            data_obj = stock_data["data"]
            if data_obj and isinstance(data_obj, dict) and "companyByExchangeAndTickerSymbol" in data_obj:
                company_data = data_obj["companyByExchangeAndTickerSymbol"]
                if company_data and isinstance(company_data, dict) and "statements" in company_data:
                    # Include ALL statements
                    all_statements = company_data["statements"]
                    print(f"Including all {len(all_statements)} statements for {stock['name']}")
                else:
                    print(f"No statements found for {stock['name']}")
            else:
                print(f"No company data found for {stock['name']}")
        else:
            print(f"Invalid API response format for {stock['name']}")
        
        stock_analysis_data.append({
            "name": stock["name"],
            "ticker": ticker,
            "shares": stock["shares"],
            "current_price": stock["current_price"],
            "market_value": stock["market_value"],
            "weight": stock["weight"],
            "statements": all_statements,
            "no_data": len(all_statements) == 0
        })
    
    analysis_prompt = f"""
    Analyze the following stocks from a value investing perspective and provide buy/sell/hold signals.
    For each stock, consider:
    1. Price-to-earnings ratio
    2. Price-to-book ratio
    3. Debt levels
    4. Return on equity
    5. Competitive advantage
    6. Current valuation vs. intrinsic value
    
    The SimplyWall.st statements data contains insights about each company's financial health, risks, and potential rewards.
    
    Portfolio data: {json.dumps(stock_analysis_data, indent=2)}
    
    For each stock, provide:
    - Signal (BUY/SELL/HOLD)
    - Brief rationale based on value investing principles
    - Current valuation assessment (overvalued, fairly valued, undervalued)
    - Any risk factors to consider
    
    Format your response as a markdown table with clear recommendations.
    """
    
    try:
        # Using o3-mini with the correct parameters
        response = client.chat.completions.create(
            model="o3-mini",
            messages=[
                {"role": "system", "content": "You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham."},
                {"role": "user", "content": analysis_prompt}
            ]
        )
        
        print("Successfully received a response from OpenAI o3-mini")
        
        if not hasattr(response, 'choices') or not response.choices:
            print("Empty response received from OpenAI API")
            return "Error: Empty response from OpenAI API"
            
        if not hasattr(response.choices[0], 'message') or not hasattr(response.choices[0].message, 'content'):
            print("Response does not contain message content")
            return "Error: No content in OpenAI API response"
            
        content = response.choices[0].message.content
        if not content:
            print("Empty content in response")
            return "Error: Empty content in OpenAI API response"
            
        return content
    except Exception as e:
        print(f"Error getting AI analysis: {e}")
        return f"Error: Could not get AI analysis. {str(e)}"

def main():
    if not SWS_API_TOKEN:
        print("Error: SimplyWall.st API token not found. Please add it to your .env file.")
        return
        
    openai_available = False
    if not OPENAI_API_KEY:
        print("Warning: OpenAI API key not found. Will save raw data but cannot generate analysis.")
    elif OPENAI_API_KEY.startswith("your_"):
        print("Warning: OpenAI API key appears to be a placeholder. Please update it with a real key.")
        print("Will continue to fetch data but analysis may not be available.")
    else:
        openai_available = True
        print("OpenAI API key found. Will attempt to generate analysis.")
    
    # Parse portfolio data
    print("Parsing portfolio data...")
    stocks = parse_portfolio()
    print(f"Found {len(stocks)} stocks in portfolio.")
    
    # Fetch data from SimplyWall.st API
    print("\nFetching data from SimplyWall.st API...")
    api_data = {}
    
    for stock in stocks:
        stock_info = get_stock_ticker_and_exchange(stock["name"])
        if stock_info:
            ticker = stock_info["ticker"]
            exchange = stock_info["exchange"]
            print(f"Fetching data for {stock['name']} ({ticker} on {exchange})...")
            
            stock_data = fetch_company_data(ticker, exchange)
            if stock_data:
                api_data[stock["name"]] = stock_data
                print(f"✅ Successfully fetched data for {stock['name']}")
            else:
                print(f"❌ Failed to fetch data for {stock['name']}")
        else:
            print(f"⚠️ Warning: No ticker/exchange found for {stock['name']}")
    
    # Save raw API data
    print("\nSaving raw API data...")
    with open("api_data.json", "w") as f:
        json.dump(api_data, f, indent=2)
    print("Raw API data saved to api_data.json")
    
    # Get value investing signals
    if openai_available and client is not None:
        print("\nAnalyzing stocks for value investing signals using OpenAI o3-mini with ALL statements...")
        signals = get_value_investing_signals(stocks, api_data)
        
        # Print results
        print("\n=== VALUE INVESTING ANALYSIS (via OpenAI o3-mini - FULL DATA) ===\n")
        print(signals)
        
        # Save results to file
        with open("portfolio_analysis.md", "w") as f:
            f.write("# Portfolio Value Investing Analysis\n\n")
            f.write(f"Analysis Date: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n")
            f.write(signals)
        
        print("\nAnalysis complete! Results saved to portfolio_analysis.md")
    else:
        print("\nSkipping analysis because OpenAI API key is not valid or missing.")
        print("You can add your OpenAI API key to the .env file and run the script again.")
        print("Raw API data has been saved to api_data.json for manual analysis.")

if __name__ == "__main__":
    main() 