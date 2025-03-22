"""
API module for interacting with the SimplyWall.st API.
"""

import time
import random
import requests
from utils.logger import logger
from utils.config import config

def fetch_company_data(ticker, exchange, api_token, max_retries=None):
    """Fetch company data from SimplyWall.st GraphQL API with retry logic.

    Args:
        ticker (str): Stock ticker symbol.
        exchange (str): Stock exchange.
        api_token (str): SimplyWall.st API token.
        max_retries (int, optional): Maximum number of retries.
            If None, uses the value from the configuration.

    Returns:
        dict: API response data, or None if the request failed.
    """
    if max_retries is None:
        max_retries = config["retry"]["max_retries"]
    
    retry_base_delay = config["retry"]["retry_base_delay"]
    retry_max_delay = config["retry"]["retry_max_delay"]
    sws_api_url = config["api"]["sws_api_url"]

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
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    retries = 0
    while retries <= max_retries:
        response = None
        try:
            if retries > 0:
                # Calculate exponential backoff delay with jitter
                delay = min(retry_base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), retry_max_delay)
                logger.info(f"Retry attempt {retries}/{max_retries} after {delay:.2f}s delay...")
                time.sleep(delay)
                
            response = requests.post(
                sws_api_url,
                headers=headers,
                json={"query": query, "variables": variables},
                timeout=30  # Set a timeout to avoid hanging requests
            )
            
            # Debug output to see raw response
            logger.info(f"Response status code: {response.status_code}")
            
            response.raise_for_status()
            response_data = response.json()
            
            # Check for server-side errors in the GraphQL response
            if "errors" in response_data and response_data.get("data") is None:
                error_msg = response_data["errors"][0]["message"] if response_data["errors"] else "Unknown GraphQL error"
                
                if "socket hang up" in error_msg or "INTERNAL_SERVER_ERROR" in str(response_data):
                    if retries < max_retries:
                        logger.warning(f"Server-side error: {error_msg}. Will retry.")
                        retries += 1
                        continue
                    else:
                        logger.error(f"Max retries reached. Last error: {error_msg}")
                        return None
                else:
                    logger.error(f"GraphQL error: {error_msg}")
                    return response_data  # Return the error response for further analysis
            
            # If we got here, the request was successful
            return response_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching data for {ticker} on {exchange}: {e}")
            
            if response and hasattr(response, 'status_code') and response.status_code != 200:
                logger.error(f"Response: {response.text}")
            
            if retries < max_retries:
                retries += 1
            else:
                logger.error(f"Max retries reached. Last error: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Unexpected error fetching data for {ticker} on {exchange}: {e}")
            
            if retries < max_retries:
                retries += 1
            else:
                logger.error(f"Max retries reached. Last error: {e}")
                return None
    
    return None  # Should never reach here but added for safety

def fetch_all_companies(stocks, api_token):
    """Fetch data for all companies in the portfolio.

    Args:
        stocks (list): List of stock dictionaries.
        api_token (str): SimplyWall.st API token.

    Returns:
        dict: Dictionary mapping stock names to API response data.
    """
    from utils.portfolio import get_stock_ticker_and_exchange
    
    api_data = {}
    
    for stock in stocks:
        stock_info = get_stock_ticker_and_exchange(stock["name"])
        if stock_info:
            ticker = stock_info["ticker"]
            exchange = stock_info["exchange"]
            logger.info(f"Fetching data for {stock['name']} ({ticker} on {exchange})...")
            
            stock_data = fetch_company_data(ticker, exchange, api_token)
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
                    logger.info(f"✅ Successfully fetched data for {stock['name']}: {statement_count} statements")
                else:
                    logger.warning(f"⚠️ Data received for {stock['name']} but structure is not as expected")
                    logger.debug(f"Response structure: {stock_data}")
            else:
                logger.error(f"❌ Failed to fetch data for {stock['name']}")
        else:
            logger.warning(f"⚠️ No ticker/exchange found for {stock['name']}")
    
    return api_data 