"""
Test script to check price extraction for all stocks in the API data.
"""

import os
import json
import re
from dotenv import load_dotenv
from utils.config import config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("price_test")

def extract_price_info(company_data, ticker):
    """Test the price extraction logic for a specific company."""
    
    # Extract statements from API response based on data structure
    statements = []
    if 'statements' in company_data:
        # Direct statements array
        statements = company_data['statements']
    elif 'data' in company_data and 'companyByExchangeAndTickerSymbol' in company_data['data']:
        # Nested structure from GraphQL
        company_obj = company_data['data']['companyByExchangeAndTickerSymbol']
        statements = company_obj.get('statements', [])
    
    # Check for IsUndervaluedBasedOnDCF statement
    dcf_statement = None
    for statement in statements:
        if statement.get('name') == 'IsUndervaluedBasedOnDCF':
            dcf_statement = statement
            break
            
    # Return the statement if found
    return dcf_statement

def main():
    """Test price extraction for all stocks in API data."""
    logger.info("STARTING: All Prices Test")
    
    # Load API data from file
    api_data_file = config["output"]["raw_data_file"]
    try:
        with open(api_data_file, 'r') as f:
            api_data = json.load(f)
            logger.info(f"Loaded API data from {api_data_file}")
    except Exception as e:
        logger.error(f"Error loading API data: {e}")
        return
    
    # Test for specific problematic stocks plus all others
    problem_stocks = ["ALV", "ASML", "CRWD", "NVDA"]
    problem_names = ["Allianz SE", "ASML Holding", "CrowdStrike", "NVIDIA"]
    
    # Process all stocks
    logger.info("Checking price extraction for all stocks...")
    
    for company_name, company_data in api_data.items():
        # Try to determine ticker
        ticker = None
        if 'ticker' in company_data:
            ticker = company_data['ticker']
        elif 'data' in company_data and 'companyByExchangeAndTickerSymbol' in company_data['data']:
            company_obj = company_data['data']['companyByExchangeAndTickerSymbol']
            if 'tickerSymbol' in company_obj:
                ticker = company_obj['tickerSymbol']
            
        # Fall back to guessing ticker from company name if still not found
        if not ticker:
            for prob_ticker, prob_name in zip(problem_stocks, problem_names):
                if prob_name in company_name:
                    ticker = prob_ticker
                    break
        
        if ticker:
            # Special handling for tickers with dots
            safe_ticker = ticker.replace(".", "_")
            
            # Check if this is one of our problem stocks
            is_problem = ticker in problem_stocks or any(name in company_name for name in problem_names)
            
            # Get price info
            dcf_statement = extract_price_info(company_data, ticker)
            
            # Output information
            if is_problem:
                logger.info(f"PROBLEM STOCK: {company_name} ({ticker})")
            else:
                logger.info(f"Regular stock: {company_name} ({ticker})")
                
            if dcf_statement:
                logger.info(f"  DCF statement: {dcf_statement.get('description')}")
                # Try to extract price from "BRK.B ($495.62) is trading below..." or "ALV (€343.2)"
                desc = dcf_statement.get('description', '')
                price_match = re.search(r'[\$€]([0-9.,]+)\)', desc)
                if price_match:
                    logger.info(f"  Extracted price: ${price_match.group(1)}")
                else:
                    logger.info(f"  No price found in DCF statement")
            else:
                logger.info(f"  No DCF statement found")
            
            # Check for the analysis file's current stated price
            analysis_file = f"data/processed/companies/claude/{safe_ticker}.md"
            if os.path.exists(analysis_file):
                try:
                    with open(analysis_file, 'r') as f:
                        content = f.read()
                        # Look for Price Analysis section
                        price_section = re.search(r'## Price Analysis\s+\*\*Current Price:\*\* (\$?[\d,.]+|Not.*?)\s+', content)
                        if price_section:
                            logger.info(f"  Analysis file shows price as: {price_section.group(1)}")
                        else:
                            logger.info(f"  Could not find price in analysis file")
                except Exception as e:
                    logger.info(f"  Error reading analysis file: {e}")
            else:
                logger.info(f"  Analysis file not found at {analysis_file}")
            
            logger.info("-" * 50)
    
    logger.info("FINISHED: All Prices Test")

if __name__ == "__main__":
    load_dotenv()
    main() 