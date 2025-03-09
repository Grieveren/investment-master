"""
Test script to debug Euro price extraction.
"""

import json
import re
from utils.config import config

def main():
    """Test Euro price extraction with various regex patterns."""
    print("STARTING: Euro Price Extraction Test")
    
    # Load API data 
    with open(config["output"]["raw_data_file"], 'r') as f:
        api_data = json.load(f)
    
    # Get Allianz data
    alv_data = api_data.get("Allianz SE", {})
    
    # Find DCF statement
    dcf_statement = None
    statements = []
    
    if 'statements' in alv_data:
        statements = alv_data['statements']
    elif 'data' in alv_data and 'companyByExchangeAndTickerSymbol' in alv_data['data']:
        company_obj = alv_data['data']['companyByExchangeAndTickerSymbol']
        statements = company_obj.get('statements', [])
    
    for statement in statements:
        if statement.get('name') == 'IsUndervaluedBasedOnDCF':
            dcf_statement = statement
            break
            
    if dcf_statement:
        desc = dcf_statement.get('description', '')
        print(f"DCF statement: {desc}")
        
        # Try different regex patterns
        print("\nTesting different regex patterns:")
        
        # Original pattern
        pattern1 = r'\$(\d+\.\d+)\)'
        match1 = re.search(pattern1, desc)
        print(f"Pattern 1 (original dollar): {pattern1}")
        print(f"  Match: {match1.group(1) if match1 else 'No match'}")
        
        # Enhanced pattern handling both $ and €
        pattern2 = r'[($€](\d+\.?\d*)[)]'
        match2 = re.search(pattern2, desc)
        print(f"Pattern 2 (enhanced): {pattern2}")
        print(f"  Match: {match2.group(1) if match2 else 'No match'}")
        
        # Pattern with explicit euro symbol
        pattern3 = r'€(\d+\.?\d*)'
        match3 = re.search(pattern3, desc)
        print(f"Pattern 3 (euro specific): {pattern3}")
        print(f"  Match: {match3.group(1) if match3 else 'No match'}")
        
        # Pattern looking for any digit sequence after currency
        pattern4 = r'[€$]([\d,.]+)'
        match4 = re.search(pattern4, desc)
        print(f"Pattern 4 (any digits after currency): {pattern4}")
        print(f"  Match: {match4.group(1) if match4 else 'No match'}")
        
        # Pattern checking Unicode representation
        pattern5 = r'[\u20AC$](\d+\.?\d*)'
        match5 = re.search(pattern5, desc)
        print(f"Pattern 5 (Unicode): {pattern5}")
        print(f"  Match: {match5.group(1) if match5 else 'No match'}")
        
        # Pattern for the exact character sequence (debugging)
        print("\nCharacter by Character Analysis:")
        for i, c in enumerate(desc):
            if i > 0 and i < 20:  # Focus on the beginning
                print(f"Character at position {i}: '{c}' (ord: {ord(c)})")
        
        # Final recommended pattern
        pattern_final = r'[\u20AC$€]([0-9.,]+)'
        match_final = re.search(pattern_final, desc)
        print(f"\nFinal recommended pattern: {pattern_final}")
        if match_final:
            price_str = match_final.group(1).replace(',', '.')
            try:
                price = float(price_str)
                print(f"  Extracted price: {price}")
            except ValueError:
                print(f"  Could not convert to float: {price_str}")
        else:
            print("  No match with final pattern")
            
    else:
        print("DCF statement not found for Allianz")
    
    print("FINISHED: Euro Price Extraction Test")

if __name__ == "__main__":
    main() 