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
import time
import random
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

# Retry settings
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2  # Base delay in seconds between retries
RETRY_MAX_DELAY = 10  # Maximum delay in seconds between retries

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
        "Allianz SE": {"ticker": "ALV", "exchange": "XTRA"},
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

def fetch_company_data(ticker, exchange, max_retries=MAX_RETRIES):
    """Fetch company data from SimplyWall.st GraphQL API with retry logic"""
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
    
    retries = 0
    while retries <= max_retries:
        response = None
        try:
            if retries > 0:
                # Calculate exponential backoff delay with jitter
                delay = min(RETRY_BASE_DELAY * (2 ** (retries - 1)) + random.uniform(0, 1), RETRY_MAX_DELAY)
                print(f"Retry attempt {retries}/{max_retries} after {delay:.2f}s delay...")
                time.sleep(delay)
                
            response = requests.post(
                SWS_API_URL,
                headers=headers,
                json={"query": query, "variables": variables}
            )
            
            # Debug output to see raw response
            print(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            response_data = response.json()
            
            # Check for server-side errors in the GraphQL response
            if "errors" in response_data and response_data.get("data") is None:
                error_msg = response_data["errors"][0]["message"] if response_data["errors"] else "Unknown GraphQL error"
                
                if "socket hang up" in error_msg or "INTERNAL_SERVER_ERROR" in str(response_data):
                    if retries < max_retries:
                        print(f"Server-side error: {error_msg}. Will retry.")
                        retries += 1
                        continue
                    else:
                        print(f"Max retries reached. Last error: {error_msg}")
                        return None
                else:
                    print(f"GraphQL error: {error_msg}")
                    return response_data  # Return the error response for further analysis
            
            # If we got here, the request was successful
            return response_data
            
        except requests.exceptions.RequestException as e:
            print(f"Request error fetching data for {ticker} on {exchange}: {e}")
            
            if response and hasattr(response, 'status_code') and response.status_code != 200:
                print(f"Response: {response.text}")
            
            if retries < max_retries:
                retries += 1
            else:
                print(f"Max retries reached. Last error: {e}")
                return None
                
        except Exception as e:
            print(f"Unexpected error fetching data for {ticker} on {exchange}: {e}")
            
            if retries < max_retries:
                retries += 1
            else:
                print(f"Max retries reached. Last error: {e}")
                return None
    
    return None  # Should never reach here but added for safety

def get_value_investing_signals(portfolio_data, api_data):
    """Use OpenAI's o3-mini model to analyze stocks and provide buy/sell signals
    
    This function processes each stock individually and combines the results,
    ensuring every stock gets fully analyzed without context window limitations.
    
    Args:
        portfolio_data (list): List of stock dictionaries with name, shares, price, etc.
        api_data (dict): Dictionary of API responses from SimplyWall.st
        
    Returns:
        str: Markdown-formatted analysis with buy/sell/hold signals for each stock
    """
    # Check if client is available
    if client is None:
        return "Error: OpenAI client not initialized. Please check your API key."
        
    # Process each stock individually
    stock_analyses = []
    
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
            stock_analyses.append({
                "name": stock["name"],
                "ticker": ticker,
                "signal": "N/A",
                "rationale": "Unable to analyze due to missing data.",
                "valuation": "Unknown",
                "risks": "N/A",
                "error": True
            })
            continue
        
        # Extract statements data for this stock
        all_statements = []
        if isinstance(stock_data, dict) and "data" in stock_data:
            data_obj = stock_data["data"]
            if data_obj and isinstance(data_obj, dict) and "companyByExchangeAndTickerSymbol" in data_obj:
                company_data = data_obj["companyByExchangeAndTickerSymbol"]
                if company_data and isinstance(company_data, dict) and "statements" in company_data:
                    all_statements = company_data["statements"]
                    print(f"Including all {len(all_statements)} statements for {stock['name']}")
                else:
                    print(f"No statements found for {stock['name']}")
            else:
                print(f"No company data found for {stock['name']}")
        else:
            print(f"Invalid API response format for {stock['name']}")
        
        # Prepare stock data for analysis
        stock_analysis_data = {
            "name": stock["name"],
            "ticker": ticker,
            "shares": stock["shares"],
            "current_price": stock["current_price"],
            "market_value": stock["market_value"],
            "weight": stock["weight"],
            "statements": all_statements,
            "no_data": len(all_statements) == 0
        }
        
        # Skip analysis if we don't have statements
        if len(all_statements) == 0:
            stock_analyses.append({
                "name": stock["name"],
                "ticker": ticker,
                "signal": "N/A",
                "rationale": "Unable to analyze due to missing financial statements.",
                "valuation": "Unknown",
                "risks": "N/A",
                "error": True
            })
            continue
        
        # Create analysis prompt for this specific stock
        analysis_prompt = f"""
        Analyze the following stock from a value investing perspective and provide a buy/sell/hold signal.
        Consider:
        1. Price-to-earnings ratio
        2. Price-to-book ratio
        3. Debt levels
        4. Return on equity
        5. Competitive advantage
        6. Current valuation vs. intrinsic value
        
        The SimplyWall.st statements data contains insights about the company's financial health, risks, and potential rewards.
        
        Stock data: {json.dumps(stock_analysis_data, indent=2)}
        
        Provide:
        1. Signal (BUY/SELL/HOLD)
        2. Detailed rationale based on value investing principles, explaining how key metrics support the recommendation
        3. Current valuation assessment (overvalued, fairly valued, undervalued)
        4. Top 2-3 risk factors to consider
        
        Format your response using JSON with these exact keys: "signal", "rationale", "valuation", "risks"
        Example: {{"signal": "BUY", "rationale": "Strong financials with...", "valuation": "Undervalued", "risks": "Competition from..."}}
        """
        
        try:
            # Using o3-mini with the correct parameters for this stock
            print(f"Sending analysis request for {stock['name']}...")
            response = client.chat.completions.create(
                model="o3-mini",
                messages=[
                    {"role": "system", "content": "You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham."},
                    {"role": "user", "content": analysis_prompt}
                ],
                reasoning_effort="high",  # Set to high mode for more thorough analysis
                response_format={"type": "json_object"}  # Ensure structured JSON response
            )
            
            if not hasattr(response, 'choices') or not response.choices:
                print(f"Empty response received from OpenAI API for {stock['name']}")
                stock_analyses.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "signal": "ERROR",
                    "rationale": "API returned an empty response.",
                    "valuation": "Unknown",
                    "risks": "N/A",
                    "error": True
                })
                continue
                
            content = response.choices[0].message.content
            if not content:
                print(f"Empty content in response for {stock['name']}")
                stock_analyses.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "signal": "ERROR",
                    "rationale": "API returned empty content.",
                    "valuation": "Unknown", 
                    "risks": "N/A",
                    "error": True
                })
                continue
            
            # Parse JSON response
            try:
                analysis_result = json.loads(content)
                analysis_result["name"] = stock["name"]
                analysis_result["ticker"] = ticker
                analysis_result["error"] = False
                stock_analyses.append(analysis_result)
                print(f"✅ Successfully analyzed {stock['name']}: {analysis_result['signal']}")
            except json.JSONDecodeError:
                print(f"Failed to parse JSON response for {stock['name']}")
                # Try to extract signal from text response
                if "BUY" in content.upper():
                    signal = "BUY"
                elif "SELL" in content.upper():
                    signal = "SELL"
                elif "HOLD" in content.upper():
                    signal = "HOLD"
                else:
                    signal = "UNKNOWN"
                    
                stock_analyses.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "signal": signal,
                    "rationale": "Failed to parse structured response. Raw content: " + content[:100] + "...",
                    "valuation": "Unknown",
                    "risks": "N/A",
                    "error": True
                })
                
        except Exception as e:
            print(f"Error analyzing {stock['name']}: {e}")
            stock_analyses.append({
                "name": stock["name"],
                "ticker": ticker,
                "signal": "ERROR",
                "rationale": f"Exception during analysis: {str(e)}",
                "valuation": "Unknown",
                "risks": "N/A",
                "error": True
            })
    
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
                # Safely check the response structure
                has_valid_data = (
                    isinstance(stock_data, dict) and 
                    "data" in stock_data and 
                    isinstance(stock_data["data"], dict) and
                    "companyByExchangeAndTickerSymbol" in stock_data["data"] and
                    stock_data["data"]["companyByExchangeAndTickerSymbol"] is not None
                )
                
                if has_valid_data:
                    api_data[stock["name"]] = stock_data
                    
                    company = stock_data["data"]["companyByExchangeAndTickerSymbol"]
                    statement_count = len(company.get("statements", [])) if company else 0
                    print(f"✅ Successfully fetched data for {stock['name']}: {statement_count} statements")
                else:
                    print(f"⚠️ Data received for {stock['name']} but structure is not as expected:")
                    print(json.dumps(stock_data, indent=2)[:500] + "..." if len(json.dumps(stock_data)) > 500 else json.dumps(stock_data, indent=2))
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
        print("\nAnalyzing stocks for value investing signals using OpenAI o3-mini (individual stock approach)...")
        signals = get_value_investing_signals(stocks, api_data)
        
        # Print results
        print("\n=== VALUE INVESTING ANALYSIS COMPLETE ===\n")
        print("Analysis has been generated for all stocks in your portfolio.")
        
        # Save results to file
        with open("portfolio_analysis.md", "w") as f:
            f.write(signals)
        
        print("\nAnalysis complete! Results saved to portfolio_analysis.md")
    else:
        print("\nSkipping analysis because OpenAI API key is not valid or missing.")
        print("You can add your OpenAI API key to the .env file and run the script again.")
        print("Raw API data has been saved to api_data.json for manual analysis.")

if __name__ == "__main__":
    main() 