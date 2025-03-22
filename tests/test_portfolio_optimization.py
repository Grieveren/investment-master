"""
Test portfolio optimization using existing analysis results.

This script tests only the portfolio optimization functionality without
re-fetching data or re-running the stock analysis.
"""

import os
import json
import datetime
import glob
from dotenv import load_dotenv
from utils.logger import logger
from utils.config import config
from utils.portfolio_optimizer import parse_portfolio_csv, map_portfolio_to_analysis, optimize_portfolio, format_optimization_to_markdown
from utils.file_operations import save_markdown

def main():
    """Test only the portfolio optimization."""
    print("STARTING: Portfolio Optimization Test")
    print(f"Working directory: {os.getcwd()}")
    
    # Load environment variables (not strictly needed but keeping for consistency)
    load_dotenv()
    
    # Ensure output directory exists
    os.makedirs("data/processed", exist_ok=True)
    
    # Load the analysis results from files
    stocks = []
    model_companies_dir = os.path.join(config["output"]["companies_dir"], "claude")
    company_files = glob.glob(os.path.join(model_companies_dir, "*.md"))
    
    print(f"Found {len(company_files)} company analysis files.")
    
    # Process each company file to extract the analysis results
    for file_path in company_files:
        ticker = os.path.basename(file_path).replace("_", ".").replace(".md", "")
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Extract company name and recommendation
            name_match = None
            recommendation = None
            
            # Try to extract name and ticker from first line
            first_line = content.split('\n')[0] if content else ""
            if "Analysis" in first_line:
                name_match = first_line.replace(" Analysis", "").strip()
            
            # Try to extract recommendation
            for line in content.split('\n'):
                if "**Recommendation:**" in line:
                    recommendation = line.replace("**Recommendation:**", "").strip()
                    break
            
            if name_match:
                # Name might be in format "Company Name (TICKER)"
                if "(" in name_match and ")" in name_match:
                    name = name_match.split('(')[0].strip()
                else:
                    name = name_match
                
                # Build a simple analysis structure
                stock = {
                    'name': name,
                    'ticker': ticker,
                    'recommendation': recommendation or 'HOLD'  # Default to HOLD if not found
                }
                
                stocks.append(stock)
                print(f"Loaded analysis for {name} ({ticker}): {recommendation}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    if not stocks:
        print("No stock analyses found. Please run the full analysis first.")
        return
    
    # Run the portfolio optimization
    print("\nPerforming portfolio optimization...")
    try:
        # Parse portfolio CSV file
        csv_path = config["portfolio"]["csv_file"]
        print(f"Parsing portfolio data from CSV: {csv_path}")
        portfolio_csv_data = parse_portfolio_csv(csv_path)
        
        if portfolio_csv_data:
            # Map portfolio positions to analysis results
            print("Mapping portfolio data to analysis results...")
            mapped_positions = map_portfolio_to_analysis(portfolio_csv_data, stocks)
            print(f"Mapped {len(mapped_positions)} positions to analysis results")
            
            # Generate optimization recommendations
            print("Generating optimization recommendations...")
            optimization_results = optimize_portfolio(
                mapped_positions, 
                total_value=portfolio_csv_data['summary'].get('Depotwert (inkl. Stückzinsen) in EUR')
            )
            
            # Format and save optimization results
            optimization_md = format_optimization_to_markdown(optimization_results, portfolio_csv_data)
            optimization_file = config["output"]["optimization_file"]
            
            print(f"Saving optimization results to {optimization_file}...")
            save_markdown(optimization_md, optimization_file)
            print(f"Optimization results saved to {optimization_file}")
        else:
            print("Error: Failed to parse portfolio CSV data.")
    except Exception as e:
        print(f"Error during portfolio optimization: {e}")
        import traceback
        traceback.print_exc()
    
    print("FINISHED: Portfolio Optimization Test")

if __name__ == "__main__":
    main() 