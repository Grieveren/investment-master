"""
Test script to debug the price extraction from API data.
"""

import os
import json
import re
from dotenv import load_dotenv
from utils.config import config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("price_debug")

def debug_price_extraction(company_data, ticker):
    """Debug the price extraction logic from the build_analysis_prompt function."""
    
    # Extract statements from API response based on data structure
    statements = []
    if 'statements' in company_data:
        # Direct statements array
        statements = company_data['statements']
    elif 'data' in company_data and 'companyByExchangeAndTickerSymbol' in company_data['data']:
        # Nested structure from GraphQL
        company_obj = company_data['data']['companyByExchangeAndTickerSymbol']
        statements = company_obj.get('statements', [])
    
    logger.info(f"Found {len(statements)} statements")
    
    # Extract key information - CURRENT PRICE
    current_price = None
    
    # First look for price directly
    for statement in statements:
        stmt_name = statement.get('name', '').lower()
        stmt_area = statement.get('area', '').lower()
        description = statement.get('description', '').lower()
        value = statement.get('value')
        
        # Debug price-related statements
        if 'price' in stmt_name or 'price' in description:
            logger.info(f"PRICE CHECK 1: {stmt_name} | {description} | Value: {value}")
            
            # Try multiple approaches to find the current price
            if value is not None and (isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '').isdigit())):
                try:
                    current_price = float(value)
                    logger.info(f"FOUND DIRECT PRICE: {current_price}")
                    break
                except (ValueError, TypeError):
                    logger.info(f"Could not convert value to float: {value}")
    
    # If still no price, check statement descriptions
    if current_price is None:
        logger.info("Direct price not found, checking descriptions")
        # Check statement descriptions for price mentions
        for statement in statements:
            description = statement.get('description', '')
            
            # Debug for price-related text
            if 'price' in description.lower() or '$' in description:
                logger.info(f"PRICE TEXT: {description}")
            
            # First try to find ticker with price in parentheses format: "BRK.B ($495.62)"
            ticker_price_match = re.search(r'{}?\s*\(\$([0-9,.]+)\)'.format(re.escape(ticker)), description)
            if ticker_price_match:
                try:
                    price_str = ticker_price_match.group(1).replace(',', '')
                    current_price = float(price_str)
                    logger.info(f"FOUND TICKER PRICE FORMAT: {current_price}")
                    break
                except (ValueError, TypeError):
                    logger.info(f"Could not convert ticker price to float: {ticker_price_match.group(1)}")
            
            # Then try normal ticker format without parentheses
            ticker_price_match2 = re.search(r'{}\s+\$([0-9,.]+)'.format(re.escape(ticker)), description)
            if ticker_price_match2:
                try:
                    price_str = ticker_price_match2.group(1).replace(',', '')
                    current_price = float(price_str)
                    logger.info(f"FOUND TICKER PRICE FORMAT 2: {current_price}")
                    break
                except (ValueError, TypeError):
                    logger.info(f"Could not convert ticker price to float: {ticker_price_match2.group(1)}")
            
            # Then try other common price formats
            if 'current price' in description.lower() or 'share price' in description.lower() or 'trading at' in description.lower():
                # Try to extract price from description text
                price_match = re.search(r'(?:price|value|trading at)[^\d]*?\$([0-9,.]+)', description.lower())
                if price_match:
                    try:
                        price_str = price_match.group(1).replace(',', '')
                        current_price = float(price_str)
                        logger.info(f"FOUND GENERAL PRICE FORMAT: {current_price}")
                        break
                    except (ValueError, TypeError):
                        logger.info(f"Could not convert general price to float: {price_match.group(1)}")
    
            # Try to find any dollar amount
            dollar_match = re.search(r'\$([0-9,.]+)', description)
            if dollar_match:
                logger.info(f"DOLLAR MATCH: {dollar_match.group(0)} in: {description}")
    
    # Format price for readability
    if current_price is not None:
        current_price_formatted = f"${current_price:.2f}"
        logger.info(f"Final extracted price: {current_price_formatted}")
    else:
        current_price_formatted = "Not available in API data"
        logger.info("No price could be extracted")
    
    return current_price, current_price_formatted

def main():
    """Test price extraction logic."""
    logger.info("STARTING: Price Extraction Test")
    
    # Load API data from file
    api_data_file = config["output"]["raw_data_file"]
    try:
        with open(api_data_file, 'r') as f:
            api_data = json.load(f)
            logger.info(f"Loaded API data from {api_data_file}")
    except Exception as e:
        logger.error(f"Error loading API data: {e}")
        return
    
    # Test with Berkshire Hathaway data
    company_name = "Berkshire Hathaway B"
    ticker = "BRK.B"
    
    # Try to find data by company name or ticker
    company_data = None
    if company_name in api_data:
        company_data = api_data[company_name]
        logger.info(f"Found data for {company_name}")
    elif ticker in api_data:
        company_data = api_data[ticker]
        logger.info(f"Found data for {ticker}")
    else:
        logger.error(f"Could not find data for {company_name} or {ticker}")
        return
    
    # Test price extraction
    logger.info(f"Testing price extraction for {ticker}")
    price, formatted_price = debug_price_extraction(company_data, ticker)
    
    # Look for 'IsUndervaluedBasedOnDCF' statement specifically
    statements = []
    if 'statements' in company_data:
        statements = company_data['statements']
    elif 'data' in company_data and 'companyByExchangeAndTickerSymbol' in company_data['data']:
        company_obj = company_data['data']['companyByExchangeAndTickerSymbol']
        statements = company_obj.get('statements', [])
    
    for statement in statements:
        if statement.get('name') == 'IsUndervaluedBasedOnDCF':
            logger.info(f"Found IsUndervaluedBasedOnDCF statement: {statement}")
            # Try custom extraction for this specific statement
            desc = statement.get('description', '')
            price_match = re.search(r'\$(\d+\.\d+)\)', desc)
            if price_match:
                logger.info(f"Special extraction found price: ${price_match.group(1)}")
    
    logger.info("FINISHED: Price Extraction Test")

if __name__ == "__main__":
    load_dotenv()
    main() 