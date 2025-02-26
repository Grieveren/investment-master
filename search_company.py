"""
SimplyWall.st Company Search

This script searches for a company by name using the SimplyWall.st API
to find the correct exchange and ticker symbol.

Usage:
1. Create a .env file with your SimplyWall.st API token (SWS_API_TOKEN=your_token)
2. Run the script: python search_company.py
"""

import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API key
SWS_API_TOKEN = os.getenv("SWS_API_TOKEN")

# API endpoint
SWS_API_URL = "https://api.simplywall.st/graphql"

def search_companies(query):
    """Search for companies by name using the SimplyWall.st GraphQL API"""
    query_string = """
    query searchCompanies($query: String!) {
      searchCompanies(query: $query) {
        id
        name
        exchangeSymbol
        tickerSymbol
      }
    }
    """
    
    variables = {
        "query": query
    }
    
    headers = {
        "Authorization": f"Bearer {SWS_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            SWS_API_URL,
            headers=headers,
            json={"query": query_string, "variables": variables}
        )
        
        print(f"Response status code: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error searching for companies: {e}")
        return None

def list_exchanges():
    """List all exchanges supported by the SimplyWall.st API"""
    query_string = """
    query {
      exchanges {
        symbol
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {SWS_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            SWS_API_URL,
            headers=headers,
            json={"query": query_string}
        )
        
        print(f"Response status code: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error listing exchanges: {e}")
        return None

def main():
    if not SWS_API_TOKEN:
        print("Error: SimplyWall.st API token not found. Please add it to your .env file.")
        return
    
    print(f"Using SimplyWall.st API token: {SWS_API_TOKEN[:5]}...{SWS_API_TOKEN[-4:] if SWS_API_TOKEN else 'None'}")
    
    # First, let's search for Allianz
    print("\nSearching for 'Allianz'...")
    search_results = search_companies("Allianz")
    
    if search_results and "data" in search_results and "searchCompanies" in search_results["data"]:
        companies = search_results["data"]["searchCompanies"]
        
        if companies:
            print(f"\nFound {len(companies)} companies matching 'Allianz':")
            for company in companies:
                print(f"- {company['name']} ({company['exchangeSymbol']}:{company['tickerSymbol']})")
        else:
            print("No companies found matching 'Allianz'")
    else:
        print("Failed to search for companies or no results returned")
    
    # List all available exchanges
    print("\nListing all supported exchanges...")
    exchanges_result = list_exchanges()
    
    if exchanges_result and "data" in exchanges_result and "exchanges" in exchanges_result["data"]:
        exchanges = exchanges_result["data"]["exchanges"]
        
        if exchanges:
            print(f"\nFound {len(exchanges)} supported exchanges:")
            for exchange in exchanges:
                print(f"- {exchange['symbol']}")
        else:
            print("No exchanges found")
    else:
        print("Failed to list exchanges or no results returned")

if __name__ == "__main__":
    main() 