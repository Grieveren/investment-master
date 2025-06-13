"""
Yahoo Finance API module for fetching stock data
Replaces the discontinued SimplyWall.st API
"""

import json
import requests
from datetime import datetime, timedelta
from src.core.logger import logger

def fetch_company_data_yfinance(ticker: str, exchange: str = None) -> dict:
    """
    Fetch company data from Yahoo Finance
    
    Args:
        ticker (str): Stock ticker symbol
        exchange (str): Exchange (not used for yfinance)
        
    Returns:
        dict: Company financial data
    """
    try:
        # Yahoo Finance API endpoints
        base_url = "https://query1.finance.yahoo.com/v8/finance/chart"
        quote_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
        
        # Get basic quote data
        chart_response = requests.get(f"{base_url}/{ticker}", 
                                    params={"interval": "1d", "range": "1y"},
                                    headers={"User-Agent": "Mozilla/5.0"})
        
        if chart_response.status_code != 200:
            logger.error(f"Failed to fetch chart data for {ticker}: {chart_response.status_code}")
            return None
            
        chart_data = chart_response.json()
        
        # Get detailed company data
        modules = "price,summaryProfile,financialData,defaultKeyStatistics,recommendationTrend"
        quote_response = requests.get(quote_url,
                                    params={"modules": modules},
                                    headers={"User-Agent": "Mozilla/5.0"})
        
        if quote_response.status_code != 200:
            logger.error(f"Failed to fetch quote data for {ticker}: {quote_response.status_code}")
            return None
            
        quote_data = quote_response.json()
        
        # Extract relevant data
        result = quote_data.get("quoteSummary", {}).get("result", [{}])[0]
        price_data = result.get("price", {})
        financial_data = result.get("financialData", {})
        key_stats = result.get("defaultKeyStatistics", {})
        profile = result.get("summaryProfile", {})
        
        # Build company data structure
        company_data = {
            "ticker": ticker,
            "name": price_data.get("longName", ticker),
            "exchange": price_data.get("exchangeName", ""),
            "current_price": price_data.get("regularMarketPrice", {}).get("raw", 0),
            "currency": price_data.get("currency", "USD"),
            "market_cap": price_data.get("marketCap", {}).get("raw", 0),
            
            # Valuation metrics
            "pe_ratio": key_stats.get("trailingPE", {}).get("raw", 0),
            "forward_pe": key_stats.get("forwardPE", {}).get("raw", 0),
            "peg_ratio": key_stats.get("pegRatio", {}).get("raw", 0),
            "price_to_book": key_stats.get("priceToBook", {}).get("raw", 0),
            "enterprise_value": key_stats.get("enterpriseValue", {}).get("raw", 0),
            
            # Financial metrics
            "revenue": financial_data.get("totalRevenue", {}).get("raw", 0),
            "revenue_growth": financial_data.get("revenueGrowth", {}).get("raw", 0),
            "profit_margins": financial_data.get("profitMargins", {}).get("raw", 0),
            "operating_margins": financial_data.get("operatingMargins", {}).get("raw", 0),
            "roe": financial_data.get("returnOnEquity", {}).get("raw", 0),
            "roa": financial_data.get("returnOnAssets", {}).get("raw", 0),
            "debt_to_equity": financial_data.get("debtToEquity", {}).get("raw", 0),
            "current_ratio": financial_data.get("currentRatio", {}).get("raw", 0),
            "free_cash_flow": financial_data.get("freeCashflow", {}).get("raw", 0),
            
            # Price targets
            "target_high": financial_data.get("targetHighPrice", {}).get("raw", 0),
            "target_low": financial_data.get("targetLowPrice", {}).get("raw", 0),
            "target_mean": financial_data.get("targetMeanPrice", {}).get("raw", 0),
            "recommendation": financial_data.get("recommendationKey", "none"),
            
            # Company info
            "industry": profile.get("industry", ""),
            "sector": profile.get("sector", ""),
            "business_summary": profile.get("longBusinessSummary", ""),
            
            # Historical data (last 30 days)
            "price_history": _extract_price_history(chart_data)
        }
        
        logger.info(f"Successfully fetched data for {ticker}")
        return company_data
        
    except Exception as e:
        logger.error(f"Error fetching data for {ticker}: {e}")
        return None

def _extract_price_history(chart_data: dict) -> list:
    """Extract price history from chart data"""
    try:
        result = chart_data.get("chart", {}).get("result", [{}])[0]
        timestamps = result.get("timestamp", [])
        quotes = result.get("indicators", {}).get("quote", [{}])[0]
        closes = quotes.get("close", [])
        
        # Get last 30 days
        history = []
        for i in range(max(0, len(timestamps) - 30), len(timestamps)):
            if i < len(closes) and closes[i] is not None:
                history.append({
                    "date": datetime.fromtimestamp(timestamps[i]).strftime("%Y-%m-%d"),
                    "close": closes[i]
                })
        
        return history
    except:
        return []

def fetch_batch_quotes(tickers: list) -> dict:
    """
    Fetch quotes for multiple tickers at once
    
    Args:
        tickers (list): List of ticker symbols
        
    Returns:
        dict: Dictionary mapping tickers to current prices
    """
    try:
        # Yahoo Finance batch quote endpoint
        symbols = ",".join(tickers)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote"
        
        response = requests.get(url,
                              params={"symbols": symbols},
                              headers={"User-Agent": "Mozilla/5.0"})
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch batch quotes: {response.status_code}")
            return {}
            
        data = response.json()
        quotes = data.get("quoteResponse", {}).get("result", [])
        
        result = {}
        for quote in quotes:
            ticker = quote.get("symbol")
            if ticker:
                result[ticker] = {
                    "price": quote.get("regularMarketPrice", 0),
                    "change": quote.get("regularMarketChange", 0),
                    "change_percent": quote.get("regularMarketChangePercent", 0),
                    "volume": quote.get("regularMarketVolume", 0)
                }
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching batch quotes: {e}")
        return {}