#!/usr/bin/env python3
"""
Stock Screener based on Value Investing Principles

This script allows you to screen stocks based on value investing criteria
from the book "Build Wealth with Common Stocks" and other value investing methodologies.
"""

import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Default screening criteria
DEFAULT_CRITERIA = {
    'min_market_cap': 1e9,          # Minimum market cap of $1 billion
    'max_pe': 20,                    # Maximum P/E ratio
    'min_dividend_yield': 0,         # Minimum dividend yield
    'max_debt_to_equity': 2,         # Maximum debt-to-equity ratio
    'min_roe': 0.1,                  # Minimum return on equity (10%)
    'min_current_ratio': 1.5,        # Minimum current ratio
    'min_profit_margin': 0.05,       # Minimum profit margin (5%)
    'max_pb': 3,                     # Maximum price-to-book ratio
    'min_graham_upside': 10,         # Minimum Graham Number upside potential (%)
    'min_earnings_growth': 0.05      # Minimum earnings growth (5%)
}

def get_stock_data(ticker):
    """Get basic stock data for screening"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Basic information
        data = {
            'ticker': ticker,
            'company_name': info.get('longName', ticker),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'market_cap': info.get('marketCap', None),
            'current_price': info.get('currentPrice', info.get('previousClose', None)),
            
            # Valuation metrics
            'pe_ratio': info.get('trailingPE', None),
            'forward_pe': info.get('forwardPE', None),
            'pb_ratio': info.get('priceToBook', None),
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            
            # Financial health
            'debt_to_equity': info.get('debtToEquity', None),
            'current_ratio': info.get('currentRatio', None),
            'quick_ratio': info.get('quickRatio', None),
            
            # Profitability
            'profit_margin': info.get('profitMargins', None) * 100 if info.get('profitMargins') else None,
            'operating_margin': info.get('operatingMargins', None) * 100 if info.get('operatingMargins') else None,
            'roe': info.get('returnOnEquity', None) * 100 if info.get('returnOnEquity') else None,
            'roa': info.get('returnOnAssets', None) * 100 if info.get('returnOnAssets') else None,
            
            # Growth
            'revenue_growth': info.get('revenueGrowth', None) * 100 if info.get('revenueGrowth') else None,
            'earnings_growth': info.get('earningsGrowth', None) * 100 if info.get('earningsGrowth') else None,
            
            # Value metrics
            'eps': info.get('trailingEps', None),
            'book_value': info.get('bookValue', None)
        }
        
        # Calculate Graham Number if possible
        if data['eps'] and data['eps'] > 0 and data['book_value'] and data['book_value'] > 0:
            graham_number = np.sqrt(22.5 * data['eps'] * data['book_value'])
            data['graham_number'] = graham_number
            
            if data['current_price']:
                data['graham_upside'] = (graham_number / data['current_price'] - 1) * 100
            else:
                data['graham_upside'] = None
        else:
            data['graham_number'] = None
            data['graham_upside'] = None
        
        return data
        
    except Exception as e:
        print(f"Error retrieving data for {ticker}: {str(e)}")
        return {
            'ticker': ticker,
            'error': str(e)
        }

def screen_stocks(tickers, criteria=None, max_workers=5):
    """
    Screen a list of stocks based on value investing criteria
    
    Parameters:
    - tickers: List of stock ticker symbols
    - criteria: Dictionary of screening criteria
    - max_workers: Maximum number of concurrent workers for fetching data
    
    Returns:
    - DataFrame with screened results
    """
    if criteria is None:
        criteria = DEFAULT_CRITERIA
    
    print(f"Screening {len(tickers)} stocks using {max_workers} parallel workers...")
    
    # Fetch data for all tickers
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {executor.submit(get_stock_data, ticker): ticker for ticker in tickers}
        
        completed = 0
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                data = future.result()
                if 'error' not in data:
                    results.append(data)
                
                # Show progress
                completed += 1
                if completed % 10 == 0 or completed == len(tickers):
                    print(f"Progress: {completed}/{len(tickers)} stocks processed")
            
            except Exception as e:
                print(f"Error processing {ticker}: {str(e)}")
    
    # Convert to DataFrame
    if not results:
        print("No valid stock data was found.")
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # Apply screening criteria
    print("\nApplying screening criteria...")
    
    original_count = len(df)
    
    # Market cap filter
    if 'min_market_cap' in criteria and criteria['min_market_cap'] > 0:
        df = df[df['market_cap'] >= criteria['min_market_cap']]
        print(f"Market cap >= ${criteria['min_market_cap']/1e9:.1f}B: {len(df)} stocks remaining")
    
    # P/E ratio filter
    if 'max_pe' in criteria and criteria['max_pe'] > 0:
        # Keep stocks with P/E below threshold or with no P/E data
        df = df[(df['pe_ratio'] <= criteria['max_pe']) | (df['pe_ratio'].isna())]
        print(f"P/E ratio <= {criteria['max_pe']}: {len(df)} stocks remaining")
    
    # Dividend yield filter
    if 'min_dividend_yield' in criteria and criteria['min_dividend_yield'] > 0:
        df = df[df['dividend_yield'] >= criteria['min_dividend_yield']]
        print(f"Dividend yield >= {criteria['min_dividend_yield']}%: {len(df)} stocks remaining")
    
    # Debt-to-equity filter
    if 'max_debt_to_equity' in criteria and criteria['max_debt_to_equity'] > 0:
        # Keep stocks with debt-to-equity below threshold or with no data
        df = df[(df['debt_to_equity'] <= criteria['max_debt_to_equity']) | (df['debt_to_equity'].isna())]
        print(f"Debt-to-equity <= {criteria['max_debt_to_equity']}: {len(df)} stocks remaining")
    
    # ROE filter
    if 'min_roe' in criteria and criteria['min_roe'] > 0:
        df = df[df['roe'] >= criteria['min_roe'] * 100]  # Convert to percentage
        print(f"ROE >= {criteria['min_roe']*100}%: {len(df)} stocks remaining")
    
    # Current ratio filter
    if 'min_current_ratio' in criteria and criteria['min_current_ratio'] > 0:
        # Keep stocks with current_ratio above threshold or with no data
        df = df[(df['current_ratio'] >= criteria['min_current_ratio']) | (df['current_ratio'].isna())]
        print(f"Current ratio >= {criteria['min_current_ratio']}: {len(df)} stocks remaining")
    
    # Profit margin filter
    if 'min_profit_margin' in criteria and criteria['min_profit_margin'] > 0:
        df = df[df['profit_margin'] >= criteria['min_profit_margin'] * 100]  # Convert to percentage
        print(f"Profit margin >= {criteria['min_profit_margin']*100}%: {len(df)} stocks remaining")
    
    # P/B ratio filter
    if 'max_pb' in criteria and criteria['max_pb'] > 0:
        # Keep stocks with P/B below threshold or with no P/B data
        df = df[(df['pb_ratio'] <= criteria['max_pb']) | (df['pb_ratio'].isna())]
        print(f"P/B ratio <= {criteria['max_pb']}: {len(df)} stocks remaining")
    
    # Graham Number upside filter
    if 'min_graham_upside' in criteria and criteria['min_graham_upside'] > 0:
        # Only consider stocks with valid Graham Number calculations
        df = df[(df['graham_upside'] >= criteria['min_graham_upside']) | (df['graham_upside'].isna())]
        print(f"Graham upside >= {criteria['min_graham_upside']}%: {len(df)} stocks remaining")
    
    # Earnings growth filter
    if 'min_earnings_growth' in criteria and criteria['min_earnings_growth'] > 0:
        # Keep stocks with earnings growth above threshold or with no data
        df = df[(df['earnings_growth'] >= criteria['min_earnings_growth'] * 100) | (df['earnings_growth'].isna())]
        print(f"Earnings growth >= {criteria['min_earnings_growth']*100}%: {len(df)} stocks remaining")
    
    # Final results
    final_count = len(df)
    print(f"\nScreening complete: {final_count} stocks out of {original_count} passed all criteria.")
    
    # Sort by market cap (descending)
    if not df.empty:
        df = df.sort_values('market_cap', ascending=False)
    
    return df

def get_index_tickers(index_name):
    """Get tickers from common indices"""
    indices = {
        'sp500': '^GSPC',
        'nasdaq100': '^NDX',
        'dowjones': '^DJI',
        'russell2000': '^RUT'
    }
    
    if index_name.lower() not in indices:
        raise ValueError(f"Unsupported index: {index_name}. Supported indices: {', '.join(indices.keys())}")
    
    # Get index constituents
    if index_name.lower() == 'sp500':
        # S&P 500 constituents
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        tables = pd.read_html(url)
        df = tables[0]
        return df['Symbol'].tolist()
    
    elif index_name.lower() == 'nasdaq100':
        # NASDAQ-100 constituents
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        df = tables[4]  # Table index may change if Wikipedia page changes
        return df['Ticker'].tolist()
    
    elif index_name.lower() == 'dowjones':
        # Dow Jones constituents
        url = "https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average"
        tables = pd.read_html(url)
        df = tables[1]  # Table index may change if Wikipedia page changes
        return df['Symbol'].tolist()
    
    elif index_name.lower() == 'russell2000':
        # Getting Russell 2000 is more complex - use iShares ETF as proxy
        iwm = yf.Ticker("IWM")
        return [holding['symbol'] for holding in iwm.get_holdings()['holdings']]
    
    return []

def load_tickers_from_file(file_path):
    """Load ticker symbols from a file"""
    with open(file_path, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    return tickers

def parse_criteria(args):
    """Parse criteria from command-line arguments"""
    criteria = {}
    
    if args.min_market_cap is not None:
        criteria['min_market_cap'] = args.min_market_cap * 1e9  # Convert to billions
    
    if args.max_pe is not None:
        criteria['max_pe'] = args.max_pe
    
    if args.min_dividend_yield is not None:
        criteria['min_dividend_yield'] = args.min_dividend_yield
    
    if args.max_debt_to_equity is not None:
        criteria['max_debt_to_equity'] = args.max_debt_to_equity
    
    if args.min_roe is not None:
        criteria['min_roe'] = args.min_roe / 100  # Convert from percentage
    
    if args.min_current_ratio is not None:
        criteria['min_current_ratio'] = args.min_current_ratio
    
    if args.min_profit_margin is not None:
        criteria['min_profit_margin'] = args.min_profit_margin / 100  # Convert from percentage
    
    if args.max_pb is not None:
        criteria['max_pb'] = args.max_pb
    
    if args.min_graham_upside is not None:
        criteria['min_graham_upside'] = args.min_graham_upside
    
    if args.min_earnings_growth is not None:
        criteria['min_earnings_growth'] = args.min_earnings_growth / 100  # Convert from percentage
    
    return criteria

def export_results(df, output_format='csv'):
    """Export screening results to a file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create output directory
    output_dir = 'screening_results'
    os.makedirs(output_dir, exist_ok=True)
    
    if output_format == 'csv':
        output_file = f"{output_dir}/stock_screen_{timestamp}.csv"
        df.to_csv(output_file, index=False)
        return output_file
    
    elif output_format == 'excel':
        output_file = f"{output_dir}/stock_screen_{timestamp}.xlsx"
        df.to_excel(output_file, index=False)
        return output_file
    
    elif output_format == 'html':
        output_file = f"{output_dir}/stock_screen_{timestamp}.html"
        df.to_html(output_file, index=False)
        return output_file
    
    else:
        raise ValueError(f"Unsupported output format: {output_format}")

def display_results(df, limit=None):
    """Display screening results"""
    if df.empty:
        print("No stocks matching the criteria.")
        return
    
    # Display only a subset of columns
    display_columns = [
        'ticker', 'company_name', 'sector', 'industry',
        'current_price', 'market_cap', 'pe_ratio', 'pb_ratio',
        'dividend_yield', 'roe', 'debt_to_equity', 'graham_upside'
    ]
    
    # Filter to columns that exist in the DataFrame
    display_columns = [col for col in display_columns if col in df.columns]
    
    # Format the DataFrame for display
    display_df = df[display_columns].copy()
    
    # Limit the number of rows if specified
    if limit and limit > 0:
        display_df = display_df.head(limit)
    
    # Format market cap as billions
    if 'market_cap' in display_df:
        display_df['market_cap'] = display_df['market_cap'].apply(
            lambda x: f"${x/1e9:.1f}B" if pd.notnull(x) else "N/A"
        )
    
    # Format percentages
    for col in ['dividend_yield', 'roe', 'graham_upside']:
        if col in display_df:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:.1f}%" if pd.notnull(x) else "N/A"
            )
    
    # Format price with dollar sign
    if 'current_price' in display_df:
        display_df['current_price'] = display_df['current_price'].apply(
            lambda x: f"${x:.2f}" if pd.notnull(x) else "N/A"
        )
    
    # Format ratios with decimals
    for col in ['pe_ratio', 'pb_ratio', 'debt_to_equity']:
        if col in display_df:
            display_df[col] = display_df[col].apply(
                lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A"
            )
    
    # Rename columns for display
    display_df.columns = [col.replace('_', ' ').title() for col in display_df.columns]
    
    # Print the results
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 160)
    print("\nScreening Results:")
    print(display_df)
    
    # Print sector breakdown
    if 'sector' in df.columns:
        print("\nSector Breakdown:")
        sector_counts = df['sector'].value_counts()
        for sector, count in sector_counts.items():
            print(f"{sector}: {count} stocks ({count/len(df)*100:.1f}%)")

def create_visualizations(df):
    """Create visualizations of the screening results"""
    if df.empty:
        return
    
    # Create output directory
    output_dir = 'screening_results'
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. Sector breakdown
    if 'sector' in df.columns:
        plt.figure(figsize=(12, 8))
        sector_counts = df['sector'].value_counts()
        sector_counts.plot(kind='pie', autopct='%1.1f%%')
        plt.title('Screened Stocks by Sector')
        plt.ylabel('')
        plt.tight_layout()
        
        sector_chart = f"{output_dir}/sector_breakdown_{timestamp}.png"
        plt.savefig(sector_chart)
        plt.close()
        print(f"\nSector breakdown chart saved to: {sector_chart}")
    
    # 2. Market cap distribution
    if 'market_cap' in df.columns:
        plt.figure(figsize=(12, 8))
        
        # Create market cap categories
        df['market_cap_category'] = pd.cut(
            df['market_cap'],
            bins=[0, 2e9, 10e9, 50e9, 200e9, 1e12, float('inf')],
            labels=['Micro (<$2B)', 'Small ($2-10B)', 'Mid ($10-50B)', 
                    'Large ($50-200B)', 'Mega ($200B-1T)', 'Super ($1T+)']
        )
        
        market_cap_counts = df['market_cap_category'].value_counts().sort_index()
        market_cap_counts.plot(kind='bar')
        plt.title('Market Cap Distribution of Screened Stocks')
        plt.xlabel('Market Cap Range')
        plt.ylabel('Number of Stocks')
        plt.tight_layout()
        
        mcap_chart = f"{output_dir}/market_cap_dist_{timestamp}.png"
        plt.savefig(mcap_chart)
        plt.close()
        print(f"Market cap distribution chart saved to: {mcap_chart}")
    
    # 3. P/E vs ROE scatter plot
    if 'pe_ratio' in df.columns and 'roe' in df.columns:
        plt.figure(figsize=(12, 8))
        
        # Filter out NaN values
        plot_df = df.dropna(subset=['pe_ratio', 'roe'])
        
        # Limit P/E to reasonable range for better visualization
        plot_df = plot_df[plot_df['pe_ratio'] < 50]
        
        plt.scatter(plot_df['pe_ratio'], plot_df['roe'], alpha=0.6)
        
        # Add company labels to points
        for i, row in plot_df.iterrows():
            plt.annotate(row['ticker'], 
                        (row['pe_ratio'], row['roe']),
                        xytext=(5, 5),
                        textcoords='offset points',
                        fontsize=8)
        
        plt.title('P/E Ratio vs Return on Equity')
        plt.xlabel('P/E Ratio')
        plt.ylabel('Return on Equity (%)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()
        
        pe_roe_chart = f"{output_dir}/pe_vs_roe_{timestamp}.png"
        plt.savefig(pe_roe_chart)
        plt.close()
        print(f"P/E vs ROE chart saved to: {pe_roe_chart}")

def main():
    """Main function for stock screening"""
    parser = argparse.ArgumentParser(description='Stock Screener based on Value Investing Principles')
    
    # Input source options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--tickers', type=str, nargs='+', help='Space-separated list of ticker symbols')
    input_group.add_argument('--file', type=str, help='File containing ticker symbols (one per line)')
    input_group.add_argument('--index', type=str, choices=['sp500', 'nasdaq100', 'dowjones', 'russell2000'], 
                           help='Use tickers from a stock index')
    
    # Screening criteria
    criteria_group = parser.add_argument_group('Screening Criteria')
    criteria_group.add_argument('--min-market-cap', type=float, help='Minimum market cap in billions of dollars')
    criteria_group.add_argument('--max-pe', type=float, help='Maximum P/E ratio')
    criteria_group.add_argument('--min-dividend-yield', type=float, help='Minimum dividend yield (%)')
    criteria_group.add_argument('--max-debt-to-equity', type=float, help='Maximum debt-to-equity ratio')
    criteria_group.add_argument('--min-roe', type=float, help='Minimum return on equity (%)')
    criteria_group.add_argument('--min-current-ratio', type=float, help='Minimum current ratio')
    criteria_group.add_argument('--min-profit-margin', type=float, help='Minimum profit margin (%)')
    criteria_group.add_argument('--max-pb', type=float, help='Maximum price-to-book ratio')
    criteria_group.add_argument('--min-graham-upside', type=float, help='Minimum Graham Number upside potential (%)')
    criteria_group.add_argument('--min-earnings-growth', type=float, help='Minimum earnings growth (%)')
    
    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument('--limit', type=int, default=25, help='Limit the number of results displayed')
    output_group.add_argument('--export', type=str, choices=['csv', 'excel', 'html'], 
                             help='Export results to a file in the specified format')
    output_group.add_argument('--visualize', action='store_true', help='Create visualizations of the results')
    output_group.add_argument('--workers', type=int, default=5, 
                             help='Number of parallel workers for fetching data')
    
    args = parser.parse_args()
    
    # Get ticker symbols from the specified source
    if args.tickers:
        tickers = args.tickers
        print(f"Using {len(tickers)} ticker symbols from command line")
    
    elif args.file:
        tickers = load_tickers_from_file(args.file)
        print(f"Loaded {len(tickers)} ticker symbols from file: {args.file}")
    
    elif args.index:
        tickers = get_index_tickers(args.index)
        print(f"Loaded {len(tickers)} ticker symbols from {args.index.upper()}")
    
    # Parse screening criteria
    criteria = parse_criteria(args)
    if not criteria:
        print("Using default screening criteria")
        criteria = DEFAULT_CRITERIA
    
    # Screen stocks
    results = screen_stocks(tickers, criteria, max_workers=args.workers)
    
    # Display results
    display_results(results, limit=args.limit)
    
    # Export results if requested
    if args.export and not results.empty:
        output_file = export_results(results, output_format=args.export)
        print(f"\nResults exported to: {output_file}")
    
    # Create visualizations if requested
    if args.visualize and not results.empty:
        create_visualizations(results)

if __name__ == "__main__":
    main() 