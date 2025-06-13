"""
API module for interacting with the SimplyWall.st API.
"""

import time
import random
import requests
from src.core.logger import logger
from src.core.config import config

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

    # Step 1: Search for company by ticker and exchange to get ID
    search_query = f"{ticker} {exchange}"
    logger.info(f"Searching for company: {search_query}")
    
    search_query_gql = """
    query searchCompanies($query: String!) {
      searchCompanies(query: $query) {
        id
        name
        exchangeSymbol
        tickerSymbol
      }
    }
    """
    
    search_variables = {
        "query": search_query
    }
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    # First search for the company ID
    company_id = None
    retries = 0
    while retries <= max_retries and company_id is None:
        try:
            if retries > 0:
                delay = min(retry_base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), retry_max_delay)
                logger.info(f"Search retry attempt {retries}/{max_retries} after {delay:.2f}s delay...")
                time.sleep(delay)
            
            search_response = requests.post(
                sws_api_url,
                headers=headers,
                json={"query": search_query_gql, "variables": search_variables},
                timeout=30
            )
            
            logger.info(f"Search response status code: {search_response.status_code}")
            search_response.raise_for_status()
            
            search_data = search_response.json()
            
            if "errors" in search_data:
                logger.error(f"GraphQL search error: {search_data['errors']}")
                retries += 1
                continue
            
            # Find the company in search results that matches our ticker and exchange
            if "data" in search_data and "searchCompanies" in search_data["data"]:
                companies = search_data["data"]["searchCompanies"]
                for company in companies:
                    if (company["tickerSymbol"].upper() == ticker.upper() and 
                        company["exchangeSymbol"].upper() == exchange.upper()):
                        company_id = company["id"]
                        logger.info(f"Found company ID: {company_id} for {ticker} on {exchange}")
                        break
                
                # If exact match not found but we have results, use the first one
                if company_id is None and companies:
                    company_id = companies[0]["id"]
                    logger.warning(f"Exact match not found. Using first result with ID: {company_id}")
            
            if company_id is None:
                logger.warning(f"Company not found in search results. Retrying...")
                retries += 1
            
        except Exception as e:
            logger.error(f"Error searching for company {ticker} on {exchange}: {e}")
            retries += 1
    
    if company_id is None:
        logger.error(f"Failed to find company ID for {ticker} on {exchange} after {max_retries} retries")
        return None
    
    # Step 2: Fetch company details using the ID
    company_query = """
    query company($id: ID!) {
      company(id: $id) {
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
    
    company_variables = {
        "id": company_id
    }
    
    # Now fetch the company details
    retries = 0
    while retries <= max_retries:
        response = None
        try:
            if retries > 0:
                delay = min(retry_base_delay * (2 ** (retries - 1)) + random.uniform(0, 1), retry_max_delay)
                logger.info(f"Details retry attempt {retries}/{max_retries} after {delay:.2f}s delay...")
                time.sleep(delay)
                
            response = requests.post(
                sws_api_url,
                headers=headers,
                json={"query": company_query, "variables": company_variables},
                timeout=30
            )
            
            logger.info(f"Details response status code: {response.status_code}")
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
            
            # Transform the response to match the expected structure in the rest of the codebase
            if "data" in response_data and "company" in response_data["data"]:
                # Create a response structure that matches the old API format
                transformed_response = {
                    "data": {
                        "companyByExchangeAndTickerSymbol": response_data["data"]["company"]
                    }
                }
                return transformed_response
            
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
    from src.core.portfolio import get_stock_ticker_and_exchange
    
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