"""
Test script to examine the price data in the API response.
"""

import os
import json
import re
from dotenv import load_dotenv
from utils.config import config

def main():
    """Examine price data in API response for a specific stock."""
    print("STARTING: Price Data Test")
    
    # Load API data from file
    api_data_file = config["output"]["raw_data_file"]
    try:
        with open(api_data_file, 'r') as f:
            api_data = json.load(f)
            print(f"Loaded API data from {api_data_file}")
    except Exception as e:
        print(f"Error loading API data: {e}")
        return
    
    # Check for Berkshire Hathaway data
    ticker = "BRK.B"
    company_name = "Berkshire Hathaway B"
    
    # Try to find data by company name or ticker
    company_data = None
    if company_name in api_data:
        company_data = api_data[company_name]
        print(f"Found data for {company_name}")
    elif ticker in api_data:
        company_data = api_data[ticker]
        print(f"Found data for {ticker}")
    else:
        print(f"Could not find data for {company_name} or {ticker}")
        return
    
    # Extract statements
    statements = []
    if 'statements' in company_data:
        statements = company_data['statements']
    elif 'data' in company_data and 'companyByExchangeAndTickerSymbol' in company_data['data']:
        company_obj = company_data['data']['companyByExchangeAndTickerSymbol']
        statements = company_obj.get('statements', [])
    
    # Look for price-related information
    print(f"\nFound {len(statements)} statements")
    
    # Look for price-related fields
    price_fields = []
    for statement in statements:
        name = statement.get('name', '')
        area = statement.get('area', '')
        description = statement.get('description', '')
        value = statement.get('value')
        
        # Check if this statement might contain price information
        if ('price' in name.lower() or 
            'price' in description.lower() or 
            'value' in name.lower() or 
            'value' in description.lower() or
            'current' in name.lower() or 
            'current' in description.lower()):
            
            price_fields.append({
                'name': name,
                'area': area,
                'description': description,
                'value': value
            })
    
    # Print all potential price fields
    print(f"\nFound {len(price_fields)} potential price-related fields:")
    for i, field in enumerate(price_fields):
        print(f"\n{i+1}. Field Name: {field['name']}")
        print(f"   Area: {field['area']}")
        print(f"   Description: {field['description']}")
        print(f"   Value: {field['value']}")
    
    # Look for portfolio entry
    print("\nChecking other locations for price data...")
    if 'portfolio' in company_data:
        portfolio = company_data['portfolio']
        print(f"Portfolio data: {portfolio}")
    
    # Look through all top-level keys in the company data
    print("\nTop-level keys in company data:")
    for key in company_data.keys():
        print(f"- {key}")
    
    # If there's a 'data' key, explore one level deeper
    if 'data' in company_data:
        data_obj = company_data['data']
        if isinstance(data_obj, dict):
            print("\nKeys in data object:")
            for key in data_obj.keys():
                print(f"- {key}")
            
            if 'companyByExchangeAndTickerSymbol' in data_obj:
                company_obj = data_obj['companyByExchangeAndTickerSymbol']
                print("\nKeys in company object:")
                for key in company_obj.keys():
                    print(f"- {key}")
                
                # Look for price directly in company object
                if 'price' in company_obj:
                    print(f"\nPrice from company object: {company_obj['price']}")
                
                # Check for priceUSD or similar
                for key in company_obj.keys():
                    if 'price' in key.lower():
                        print(f"{key}: {company_obj[key]}")
    
    print("FINISHED: Price Data Test")

if __name__ == "__main__":
    load_dotenv()
    main() 