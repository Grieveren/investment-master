"""
Simple test to verify we can fetch TSM data from SimplyWall.st API.
This script bypasses the module path issues by importing directly.
"""

import os
import sys
import json
import time
import random
import requests

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Relying on environment variables already set.")

# Get API configuration
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except:
    # Default configuration if config.json can't be loaded
    config = {
        "api": {
            "sws_api_url": "https://api.simplywall.st/graphql"
        },
        "retry": {
            "max_retries": 3,
            "retry_base_delay": 1,
            "retry_max_delay": 10
        }
    }

def simple_fetch_company_data(ticker, exchange, api_token, max_retries=3):
    """Simplified version of fetch_company_data to avoid import issues."""
    
    retry_base_delay = config["retry"]["retry_base_delay"]
    retry_max_delay = config["retry"]["retry_max_delay"]
    sws_api_url = config["api"]["sws_api_url"]

    # Step 1: Search for company by ticker and exchange to get ID
    search_query = f"{ticker} {exchange}"
    print(f"Searching for company: {search_query}")
    
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
                print(f"Search retry attempt {retries}/{max_retries} after {delay:.2f}s delay...")
                time.sleep(delay)
            
            search_response = requests.post(
                sws_api_url,
                headers=headers,
                json={"query": search_query_gql, "variables": search_variables},
                timeout=30
            )
            
            print(f"Search response status code: {search_response.status_code}")
            search_response.raise_for_status()
            
            search_data = search_response.json()
            
            if "errors" in search_data:
                print(f"GraphQL search error: {search_data['errors']}")
                retries += 1
                continue
            
            # Find the company in search results that matches our ticker and exchange
            if "data" in search_data and "searchCompanies" in search_data["data"]:
                companies = search_data["data"]["searchCompanies"]
                for company in companies:
                    if (company["tickerSymbol"].upper() == ticker.upper() and 
                        company["exchangeSymbol"].upper() == exchange.upper()):
                        company_id = company["id"]
                        print(f"Found company ID: {company_id} for {ticker} on {exchange}")
                        break
                
                # If exact match not found but we have results, use the first one
                if company_id is None and companies:
                    company_id = companies[0]["id"]
                    print(f"Exact match not found. Using first result with ID: {company_id}")
            
            if company_id is None:
                print(f"Company not found in search results. Retrying...")
                retries += 1
            
        except Exception as e:
            print(f"Error searching for company {ticker} on {exchange}: {e}")
            retries += 1
    
    if company_id is None:
        print(f"Failed to find company ID for {ticker} on {exchange} after {max_retries} retries")
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
                print(f"Details retry attempt {retries}/{max_retries} after {delay:.2f}s delay...")
                time.sleep(delay)
                
            response = requests.post(
                sws_api_url,
                headers=headers,
                json={"query": company_query, "variables": company_variables},
                timeout=30
            )
            
            print(f"Details response status code: {response.status_code}")
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

def test_tsm_fetch():
    """Test that we can fetch TSM data from SimplyWall.st API."""
    
    # Get API token from environment
    api_token = os.getenv("SWS_API_TOKEN")
    if not api_token:
        print("ERROR: SWS_API_TOKEN not found in environment")
        return False
    
    # Fetch TSM data
    ticker = "TSM"
    exchange = "NYSE"
    print(f"Fetching data for {ticker} on {exchange}...")
    
    # Attempt to fetch data
    result = simple_fetch_company_data(ticker, exchange, api_token)
    
    # Check if we got a valid response
    if result:
        # Verify the structure
        if (isinstance(result, dict) and 
            "data" in result and 
            "companyByExchangeAndTickerSymbol" in result["data"] and
            result["data"]["companyByExchangeAndTickerSymbol"] is not None):
            
            company = result["data"]["companyByExchangeAndTickerSymbol"]
            name = company.get("name", "Unknown")
            statements_count = len(company.get("statements", []))
            
            print(f"✅ SUCCESS: Got data for {name}")
            print(f"Found {statements_count} statements")
            
            return True
        else:
            print("❌ ERROR: Data structure not as expected")
            print(f"Response: {result}")
            return False
    else:
        print("❌ ERROR: Failed to fetch data")
        return False

if __name__ == "__main__":
    success = test_tsm_fetch()
    exit(0 if success else 1) 