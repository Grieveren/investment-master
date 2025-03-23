"""
Portfolio data module for the portfolio analyzer.
"""

from src.core.logger import logger
from src.core.config import config

def parse_portfolio(portfolio_file=None):
    """Parse the portfolio data from a markdown file.

    Args:
        portfolio_file (str, optional): Path to the portfolio markdown file.
            If None, uses the path from the configuration.

    Returns:
        list: List of stock dictionaries with name, shares, price, etc.
    """
    if portfolio_file is None:
        portfolio_file = config["api"]["portfolio_file"]
    
    try:
        with open(portfolio_file, "r") as f:
            content = f.read()
    except FileNotFoundError:
        logger.error(f"Portfolio file {portfolio_file} not found.")
        return []
    
    stocks = []
    
    for line in content.split('\n'):
        if '|' in line and not line.startswith('|--') and "Cash EUR" not in line:
            parts = [part.strip() for part in line.split('|')]
            if len(parts) >= 6 and parts[1] != "Security" and "Cash" not in parts[1]:
                try:
                    stocks.append({
                        "name": parts[1].strip(),
                        "shares": int(parts[2].strip()),
                        "current_price": float(parts[3].strip()),
                        "market_value": float(parts[4].strip().replace(',', '')),
                        "weight": float(parts[5].strip().replace('%', ''))
                    })
                except (ValueError, IndexError) as e:
                    logger.error(f"Error parsing line: {line}, Error: {e}")
    
    logger.info(f"Found {len(stocks)} stocks in portfolio.")
    return stocks

def get_stock_ticker_and_exchange(stock_name):
    """Map stock names to tickers and exchanges for the API.

    Args:
        stock_name (str): Stock name to map.

    Returns:
        dict: Dictionary with ticker and exchange, or None if not found.
    """
    # Stock mapping dictionary that maps company names to their ticker symbols and exchanges
    # Multiple entries are provided for companies that may be referenced in different ways
    # For example, TSM (Taiwan Semiconductor) has multiple mappings to handle various
    # ways it might appear in portfolio data (ticker symbol, full name, abbreviated name)
    stock_map = {
        # Company names
        "Berkshire Hathaway B": {"ticker": "BRK.B", "exchange": "NYSE"},
        "Allianz SE": {"ticker": "ALV", "exchange": "XTRA"},
        "GitLab Inc.": {"ticker": "GTLB", "exchange": "NasdaqGS"},
        "NVIDIA": {"ticker": "NVDA", "exchange": "NasdaqGS"},
        "Microsoft": {"ticker": "MSFT", "exchange": "NasdaqGS"},
        "Alphabet C": {"ticker": "GOOG", "exchange": "NasdaqGS"},
        "CrowdStrike": {"ticker": "CRWD", "exchange": "NasdaqGS"},
        "Advanced Micro Devices": {"ticker": "AMD", "exchange": "NasdaqGS"},
        "Nutanix": {"ticker": "NTNX", "exchange": "NasdaqGS"},
        "ASML Holding": {"ticker": "ASML", "exchange": "NasdaqGS"},
        "Taiwan Semiconductor ADR": {"ticker": "TSM", "exchange": "NYSE"},
        "Taiwan Semiconductor": {"ticker": "TSM", "exchange": "NYSE"},
        "Taiwan Semiconductor Manufacturing Company": {"ticker": "TSM", "exchange": "NYSE"},
        "Taiwan Semiconductor Manufacturing": {"ticker": "TSM", "exchange": "NYSE"},
        "TSMC": {"ticker": "TSM", "exchange": "NYSE"},
        
        # Direct ticker mappings for all companies
        "MSFT": {"ticker": "MSFT", "exchange": "NasdaqGS"},
        "NVDA": {"ticker": "NVDA", "exchange": "NasdaqGS"},
        "GOOG": {"ticker": "GOOG", "exchange": "NasdaqGS"},
        "GTLB": {"ticker": "GTLB", "exchange": "NasdaqGS"},
        "ALV": {"ticker": "ALV", "exchange": "XTRA"},
        "AMD": {"ticker": "AMD", "exchange": "NasdaqGS"},
        "BRK.B": {"ticker": "BRK.B", "exchange": "NYSE"},
        "ASML": {"ticker": "ASML", "exchange": "NasdaqGS"},
        "CRWD": {"ticker": "CRWD", "exchange": "NasdaqGS"},
        "NTNX": {"ticker": "NTNX", "exchange": "NasdaqGS"},
        "TSM": {"ticker": "TSM", "exchange": "NYSE"}
    }
    
    stock_info = stock_map.get(stock_name)
    if not stock_info:
        logger.warning(f"No ticker/exchange mapping found for {stock_name}")
    
    return stock_info 