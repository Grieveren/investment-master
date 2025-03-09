"""
Debug script to test the company analysis loading functionality
"""

import os
import glob
import re
from dotenv import load_dotenv
from utils.logger import logger
from utils.config import config

def test_read_company_analyses():
    """Test reading company analyses from the Claude output directory."""
    analyses = {}
    model_companies_dir = os.path.join(config["output"]["companies_dir"], "claude")
    
    print(f"Looking for company analyses in: {model_companies_dir}")
    
    if not os.path.exists(model_companies_dir):
        print(f"ERROR: Company analyses directory not found: {model_companies_dir}")
        return analyses
    
    company_files = glob.glob(os.path.join(model_companies_dir, "*.md"))
    print(f"Found {len(company_files)} company analysis files:")
    for file_path in company_files:
        print(f"  - {os.path.basename(file_path)}")
    
    for file_path in company_files:
        ticker = os.path.basename(file_path).replace(".md", "")
        # Handle tickers with underscores that should be periods (like BRK_B → BRK.B)
        ticker = ticker.replace("_", ".")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Extract recommendation
                recommendation_match = re.search(r'(?:^## |^#|^)Recommendation:?\s*(.*?)$', content, re.MULTILINE | re.IGNORECASE)
                recommendation = "N/A"
                if recommendation_match:
                    recommendation = recommendation_match.group(1).strip()
                
                # Print ticker and recommendation
                print(f"Loaded analysis for {ticker}: {recommendation}")
                
                analyses[ticker] = recommendation
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return analyses

if __name__ == "__main__":
    load_dotenv()
    print("Testing company analysis loading...")
    analyses = test_read_company_analyses()
    print(f"\nSuccessfully loaded {len(analyses)} analyses.")
    print("\nTest complete.") 