"""
English CSV Portfolio Parser
Handles the combined_portfolio.csv format
"""

import csv
from src.core.logger import logger
from src.core.portfolio import get_stock_ticker_and_exchange

def parse_portfolio_csv_english(csv_path):
    """Parse English format portfolio CSV.
    
    Args:
        csv_path (str): Path to the CSV file.
        
    Returns:
        dict: Portfolio data with stocks list and summary.
    """
    stocks = []
    total_value = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Skip empty rows or cash entries
                if not row.get('Security') or 'Cash' in row.get('Security', ''):
                    continue
                
                # Extract stock data
                name = row['Security'].strip().strip('"')
                
                # Get ticker mapping
                ticker_info = get_stock_ticker_and_exchange(name)
                if not ticker_info:
                    logger.warning(f"No ticker mapping for {name}")
                    continue
                
                try:
                    # Handle empty or missing values
                    shares_str = row.get('Shares', '0').strip()
                    shares = int(shares_str) if shares_str else 0
                    
                    price_str = row.get('Current Price (EUR)', '0').strip()
                    price = float(price_str) if price_str else 0
                    
                    value_str = row.get('Market Value (EUR)', '0').strip()
                    value = float(value_str) if value_str else 0
                    
                    weight_str = row.get('Weight', '0%').replace('%', '').strip()
                    weight = float(weight_str) if weight_str else 0
                    
                    stock_data = {
                        'name': name,
                        'ticker': ticker_info['ticker'],
                        'exchange': ticker_info['exchange'],
                        'shares': shares,
                        'price': price,
                        'value': value,
                        'weight': weight,
                        'portfolio': row.get('Portfolio', '')
                    }
                    
                    stocks.append(stock_data)
                    total_value += value
                    
                except (ValueError, KeyError) as e:
                    logger.warning(f"Error parsing row for {name}: {e}")
                    
    except Exception as e:
        logger.error(f"Error reading portfolio CSV: {e}")
        return None
    
    # Calculate cash (assuming small positions or rounding)
    cash_amount = 0
    cash_percentage = 0
    
    logger.info(f"Parsed {len(stocks)} stocks with total value €{total_value:,.2f}")
    
    return {
        'stocks': stocks,
        'total_value': total_value,
        'cash_amount': cash_amount,
        'cash_percentage': cash_percentage,
        'date': '2025-06-13'  # Could extract from filename or use today
    }