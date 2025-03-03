"""
Analysis module for generating stock analyses using OpenAI.
"""

import os
import json
import datetime
import time
from openai import OpenAI
from utils.logger import logger
from utils.config import config

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

def get_value_investing_signals(portfolio_data, api_data, openai_client, selected_model="o3-mini"):
    """Use OpenAI to analyze stocks and provide buy/sell signals.
    
    This function processes each stock individually and combines the results,
    ensuring every stock gets fully analyzed without context window limitations.
    
    Args:
        portfolio_data (list): List of stock dictionaries with name, shares, price, etc.
        api_data (dict): Dictionary of API responses from SimplyWall.st
        openai_client (OpenAI): OpenAI client.
        selected_model (str): Model to use for analysis ('o3-mini' or 'claude-3-7')
        
    Returns:
        str: Markdown-formatted analysis with buy/sell/hold signals for each stock
    """
    # Check if client is available
    if openai_client is None:
        return "Error: OpenAI client not initialized. Please check your API key."
        
    # Process each stock individually
    stock_analyses = []
    
    # Print progress header
    total_stocks = len(portfolio_data)
    print(f"\n{'='*50}")
    print(f"ANALYZING {total_stocks} STOCKS WITH {selected_model.upper()}")
    print(f"{'='*50}")
    print(f"{'Stock':<30} | {'Status':<20} | {'Signal':<10}")
    print(f"{'-'*30} | {'-'*20} | {'-'*10}")

    # Get model settings from config
    model_config = config["openai"]["models"][selected_model]
    model_name = model_config["name"]
    reasoning_effort = model_config["reasoning_effort"]
    
    for index, stock in enumerate(portfolio_data):
        from utils.portfolio import get_stock_ticker_and_exchange
        stock_info = get_stock_ticker_and_exchange(stock["name"])
        if not stock_info:
            logger.warning(f"Skipping {stock['name']} - no ticker/exchange info")
            print(f"{stock['name']:<30} | {'SKIPPED - No info':<20} | {'N/A':<10}")
            continue
            
        ticker = stock_info["ticker"]
        stock_data = api_data.get(stock["name"])
        
        # Show progress
        print(f"{stock['name']:<30} | {'ANALYZING...':<20} | {'...':<10}", end='\r')
        
        logger.info(f"Processing {stock['name']} ({ticker})...")
        
        # Check if we have data for this stock
        if stock_data is None:
            logger.error(f"No API data found for {stock['name']}")
            stock_analyses.append({
                "name": stock["name"],
                "ticker": ticker,
                "signal": "N/A",
                "rationale": "Unable to analyze due to missing data.",
                "valuation": "Unknown",
                "risks": "N/A",
                "error": True
            })
            print(f"{stock['name']:<30} | {'ERROR - No data':<20} | {'N/A':<10}")
            continue
        
        # Extract statements data for this stock
        all_statements = []
        if isinstance(stock_data, dict) and "data" in stock_data:
            data_obj = stock_data["data"]
            if data_obj and isinstance(data_obj, dict) and "companyByExchangeAndTickerSymbol" in data_obj:
                company_data = data_obj["companyByExchangeAndTickerSymbol"]
                if company_data and isinstance(company_data, dict) and "statements" in company_data:
                    all_statements = company_data["statements"]
                    logger.info(f"Including all {len(all_statements)} statements for {stock['name']}")
                else:
                    logger.warning(f"No statements found for {stock['name']}")
            else:
                logger.warning(f"No company data found for {stock['name']}")
        else:
            logger.warning(f"Invalid API response format for {stock['name']}")
        
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
            print(f"{stock['name']:<30} | {'ERROR - No statements':<20} | {'N/A':<10}")
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
            # Using the selected model with its parameters
            logger.info(f"Sending analysis request for {stock['name']} using {model_name}...")
            
            # Show analysis in progress
            start_time = time.time()
            
            # Create a chat completion with the appropriate model
            response = openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham."},
                    {"role": "user", "content": analysis_prompt}
                ],
                reasoning_effort=reasoning_effort,  # Use config value for reasoning effort
                response_format={"type": "json_object"}  # Ensure structured JSON response
            )
            
            analysis_time = time.time() - start_time
            
            if not hasattr(response, 'choices') or not response.choices:
                logger.error(f"Empty response received from OpenAI API for {stock['name']}")
                stock_analyses.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "signal": "ERROR",
                    "rationale": "API returned an empty response.",
                    "valuation": "Unknown",
                    "risks": "N/A",
                    "error": True
                })
                print(f"{stock['name']:<30} | {'ERROR - Empty response':<20} | {'ERROR':<10}")
                continue
                
            content = response.choices[0].message.content
            if not content:
                logger.error(f"Empty content in response for {stock['name']}")
                stock_analyses.append({
                    "name": stock["name"],
                    "ticker": ticker,
                    "signal": "ERROR",
                    "rationale": "API returned empty content.",
                    "valuation": "Unknown", 
                    "risks": "N/A",
                    "error": True
                })
                print(f"{stock['name']:<30} | {'ERROR - Empty content':<20} | {'ERROR':<10}")
                continue
            
            # Parse JSON response
            try:
                analysis_result = json.loads(content)
                analysis_result["name"] = stock["name"]
                analysis_result["ticker"] = ticker
                analysis_result["error"] = False
                stock_analyses.append(analysis_result)
                logger.info(f"✅ Successfully analyzed {stock['name']}: {analysis_result['signal']}")
                
                # Show completion status with timing
                print(f"{stock['name']:<30} | {'COMPLETED':<20} | {analysis_result['signal']:<10} ({analysis_time:.1f}s)")
                
                # Progress information
                progress = f"[{index+1}/{total_stocks}] "
                print(f"\n{progress}Completed analysis for {stock['name']} - Signal: {analysis_result['signal']}")
                print(f"{progress}Valuation: {analysis_result['valuation']}")
                if index < total_stocks - 1:
                    next_stock = portfolio_data[index+1]["name"]
                    print(f"{progress}Next stock: {next_stock}\n")
                    
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response for {stock['name']}")
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
                print(f"{stock['name']:<30} | {'ERROR - Parse failure':<20} | {signal:<10}")
                
        except Exception as e:
            logger.error(f"Error analyzing {stock['name']}: {e}")
            stock_analyses.append({
                "name": stock["name"],
                "ticker": ticker,
                "signal": "ERROR",
                "rationale": f"Exception during analysis: {str(e)}",
                "valuation": "Unknown",
                "risks": "N/A",
                "error": True
            })
            print(f"{stock['name']:<30} | {'ERROR - Exception':<20} | {'ERROR':<10}")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"ANALYSIS COMPLETE: {len(stock_analyses)}/{total_stocks} stocks analyzed")
    print(f"{'='*50}\n")
    
    return format_analysis_to_markdown(stock_analyses)

def format_analysis_to_markdown(stock_analyses):
    """Format the stock analyses into a markdown table.
    
    Args:
        stock_analyses (list): List of stock analysis dictionaries.
        
    Returns:
        str: Markdown-formatted analysis.
    """
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