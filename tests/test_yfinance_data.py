import sys
import pandas as pd
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add src directory to path if needed
sys.path.append('.')

from src.backtesting.data.yfinance_connector import YFinanceConnector

def main():
    """Test YFinanceConnector output format."""
    print("Testing YFinanceConnector output format")
    
    # Initialize connector
    connector = YFinanceConnector()
    
    # Define date range
    start_date = datetime(2023, 1, 1)
    end_date = datetime(2023, 12, 31)
    
    # Test with a single ticker - pass as a list
    tickers = ['MSFT']
    
    print(f"Getting data for {tickers} from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    data = connector.get_historical_prices(tickers, start_date, end_date)
    
    print(f"Data type: {type(data)}")
    print(f"Data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dictionary'}")
    
    # Print sample data for each key if it's a dictionary
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, pd.DataFrame) or isinstance(value, pd.Series):
                print(f"\nKey: {key}")
                print(f"Type: {type(value)}")
                print(f"Shape: {value.shape if hasattr(value, 'shape') else 'No shape'}")
                print(f"Sample data (first 5 rows):")
                print(value.head())
            else:
                print(f"\nKey: {key}")
                print(f"Type: {type(value)}")
                print(f"Value: {value}")

if __name__ == "__main__":
    main() 