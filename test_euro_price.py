"""
Specific test for extracting Euro currency price from API data.
"""

import json
import re
from dotenv import load_dotenv
from utils.config import config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("euro_price_test")

def main():
    """Test Euro price extraction."""
    logger.info("STARTING: Euro Price Extraction Test")
    
    # Load API data from file
    api_data_file = config["output"]["raw_data_file"]
    try:
        with open(api_data_file, 'r') as f:
            api_data = json.load(f)
            logger.info(f"Loaded API data from {api_data_file}")
    except Exception as e:
        logger.error(f"Error loading API data: {e}")
        return
    
    # Get Allianz data
    company_name = "Allianz SE"
    ticker = "ALV"
    
    if company_name not in api_data:
        logger.error(f"Could not find data for {company_name}")
        return
        
    company_data = api_data[company_name]
    logger.info(f"Found data for {company_name}")
    
    # Extract statements
    statements = []
    if 'statements' in company_data:
        statements = company_data['statements']
    elif 'data' in company_data and 'companyByExchangeAndTickerSymbol' in company_data['data']:
        company_obj = company_data['data']['companyByExchangeAndTickerSymbol']
        statements = company_obj.get('statements', [])
    
    logger.info(f"Found {len(statements)} statements")
    
    # Find DCF statement
    dcf_statement = None
    for statement in statements:
        if statement.get('name') == 'IsUndervaluedBasedOnDCF':
            dcf_statement = statement
            break
    
    if dcf_statement:
        description = dcf_statement.get('description', '')
        logger.info(f"DCF statement: {description}")
        
        # Try different regex patterns
        patterns = [
            (r'[\(\$€](\d+\.?\d*)[\)]', "Standard"),
            (r'\(€(\d+\.?\d*)\)', "Euro specific"),
            (r'\(€(\d+[.,]\d*)\)', "Euro with comma or period"),
            (r'ALV \(€(\d+\.?\d*)\)', "ALV Euro specific"),
            (r'\([€$]([0-9.,]+)\)', "Currency in parentheses"),
            (r'[\$€]([0-9.,]+)', "Any currency symbol"),
        ]
        
        for pattern, name in patterns:
            matches = re.findall(pattern, description)
            logger.info(f"Pattern '{name}': {pattern}")
            logger.info(f"  Matches: {matches}")
            
            # If we have matches, try to convert to float
            if matches:
                for match in matches:
                    try:
                        # Handle European number format (replace comma with period)
                        value = match.replace(',', '.')
                        price = float(value)
                        logger.info(f"  Converted to price: {price}")
                    except ValueError:
                        logger.info(f"  Could not convert '{match}' to float")
    else:
        logger.info("No DCF statement found")
    
    logger.info("FINISHED: Euro Price Extraction Test")

if __name__ == "__main__":
    load_dotenv()
    main() 