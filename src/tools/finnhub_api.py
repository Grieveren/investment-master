"""
Finnhub API module for fetching stock data
Free tier allows 60 API calls/minute
"""

import os
import json
import requests
from datetime import datetime, timedelta
from src.core.logger import logger

# You can get a free API key from https://finnhub.io/
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

def fetch_company_data_finnhub(ticker: str, exchange: str = None) -> dict:
    """
    Fetch company data from Finnhub (free tier)
    
    Args:
        ticker (str): Stock ticker symbol
        exchange (str): Exchange (optional)
        
    Returns:
        dict: Company financial data
    """
    if not FINNHUB_API_KEY:
        # If no Finnhub key, return mock data for testing
        return get_mock_company_data(ticker)
    
    try:
        base_url = "https://finnhub.io/api/v1"
        headers = {"X-Finnhub-Token": FINNHUB_API_KEY}
        
        # Get quote data
        quote_response = requests.get(f"{base_url}/quote", 
                                    params={"symbol": ticker},
                                    headers=headers)
        
        # Get company profile
        profile_response = requests.get(f"{base_url}/stock/profile2",
                                      params={"symbol": ticker},
                                      headers=headers)
        
        # Get basic financials
        metrics_response = requests.get(f"{base_url}/stock/metric",
                                      params={"symbol": ticker, "metric": "all"},
                                      headers=headers)
        
        if quote_response.status_code != 200:
            logger.error(f"Failed to fetch quote for {ticker}: {quote_response.status_code}")
            return get_mock_company_data(ticker)
        
        quote = quote_response.json()
        profile = profile_response.json() if profile_response.status_code == 200 else {}
        metrics = metrics_response.json() if metrics_response.status_code == 200 else {"metric": {}}
        
        # Build company data
        company_data = {
            "ticker": ticker,
            "name": profile.get("name", ticker),
            "exchange": profile.get("exchange", exchange or ""),
            "current_price": quote.get("c", 0),  # Current price
            "previous_close": quote.get("pc", 0),
            "change": quote.get("d", 0),
            "change_percent": quote.get("dp", 0),
            "high": quote.get("h", 0),
            "low": quote.get("l", 0),
            "market_cap": profile.get("marketCapitalization", 0) * 1_000_000,
            
            # Metrics
            "pe_ratio": metrics.get("metric", {}).get("peBasicExclExtraTTM", 0),
            "price_to_book": metrics.get("metric", {}).get("pbQuarterly", 0),
            "roe": metrics.get("metric", {}).get("roeTTM", 0),
            "revenue_growth": metrics.get("metric", {}).get("revenueGrowthTTMYoy", 0),
            "eps": metrics.get("metric", {}).get("epsBasicExclExtraItemsTTM", 0),
            "debt_to_equity": metrics.get("metric", {}).get("totalDebt/totalEquityQuarterly", 0),
            
            # Company info
            "industry": profile.get("finnhubIndustry", ""),
            "currency": profile.get("currency", "USD"),
            "country": profile.get("country", ""),
            "ipo_date": profile.get("ipo", ""),
            "website": profile.get("weburl", ""),
            
            # For compatibility with our analyzer
            "target_mean": metrics.get("metric", {}).get("priceTargetConsensus", 0),
            "recommendation": "hold"  # Finnhub uses different format
        }
        
        logger.info(f"Successfully fetched Finnhub data for {ticker}")
        return company_data
        
    except Exception as e:
        logger.error(f"Error fetching Finnhub data for {ticker}: {e}")
        return get_mock_company_data(ticker)

def get_mock_company_data(ticker: str) -> dict:
    """
    Return mock data for testing when API is not available
    """
    mock_data = {
        "MSFT": {
            "ticker": "MSFT",
            "name": "Microsoft Corporation",
            "current_price": 420.55,
            "market_cap": 3_100_000_000_000,
            "pe_ratio": 36.5,
            "price_to_book": 15.8,
            "roe": 0.47,
            "revenue_growth": 0.17,
            "eps": 11.52,
            "debt_to_equity": 0.69,
            "target_mean": 465.00,
            "industry": "Technology",
            "currency": "USD"
        },
        "NVDA": {
            "ticker": "NVDA", 
            "name": "NVIDIA Corporation",
            "current_price": 125.20,
            "market_cap": 3_080_000_000_000,
            "pe_ratio": 65.2,
            "price_to_book": 45.3,
            "roe": 0.85,
            "revenue_growth": 1.22,
            "eps": 1.92,
            "debt_to_equity": 0.42,
            "target_mean": 145.00,
            "industry": "Technology",
            "currency": "USD"
        },
        "ALV": {
            "ticker": "ALV",
            "name": "Allianz SE",
            "current_price": 328.80,
            "market_cap": 120_000_000_000,
            "pe_ratio": 12.5,
            "price_to_book": 1.8,
            "roe": 0.15,
            "revenue_growth": 0.08,
            "eps": 26.30,
            "debt_to_equity": 0.25,
            "target_mean": 350.00,
            "industry": "Insurance",
            "currency": "EUR"
        }
    }
    
    # Return mock data or generate generic data
    if ticker in mock_data:
        return mock_data[ticker]
    else:
        return {
            "ticker": ticker,
            "name": f"{ticker} Company",
            "current_price": 100.00,
            "market_cap": 50_000_000_000,
            "pe_ratio": 20.0,
            "price_to_book": 3.0,
            "roe": 0.15,
            "revenue_growth": 0.10,
            "eps": 5.00,
            "debt_to_equity": 0.50,
            "target_mean": 110.00,
            "industry": "Unknown",
            "currency": "USD"
        }

def fetch_batch_quotes_finnhub(tickers: list) -> dict:
    """
    Fetch quotes for multiple tickers
    Note: Finnhub doesn't have batch endpoint in free tier, so we simulate it
    """
    quotes = {}
    for ticker in tickers:
        data = fetch_company_data_finnhub(ticker)
        if data:
            quotes[ticker] = {
                "price": data.get("current_price", 0),
                "change": data.get("change", 0),
                "change_percent": data.get("change_percent", 0)
            }
    return quotes