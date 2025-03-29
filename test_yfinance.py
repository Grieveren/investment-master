import yfinance as yf
import pandas as pd
import datetime

# Test simple ticker retrieval
print("Testing yfinance with Microsoft (MSFT) stock data...")
msft = yf.Ticker("MSFT")

# Get stock info
print("\nGetting stock info:")
try:
    info = msft.info
    print(f"Retrieved info: Company name: {info.get('shortName', 'N/A')}")
except Exception as e:
    print(f"Error getting stock info: {e}")

# Get historical market data
print("\nGetting historical data:")
try:
    hist = msft.history(period="1mo")
    print(f"Retrieved {len(hist)} data points")
    if not hist.empty:
        print(f"Latest close price: {hist['Close'].iloc[-1]:.2f}")
except Exception as e:
    print(f"Error getting historical data: {e}")

# Get data for multiple tickers
print("\nGetting data for multiple tickers:")
try:
    tickers = ["AAPL", "GOOG", "MSFT"]
    data = yf.download(tickers, period="1wk")
    print(f"Retrieved data for {len(tickers)} tickers")
    if not data.empty:
        print("Latest closing prices:")
        for ticker in tickers:
            print(f"{ticker}: {data['Close'][ticker].iloc[-1]:.2f}")
except Exception as e:
    print(f"Error getting multiple ticker data: {e}")

print("\nTest completed.") 