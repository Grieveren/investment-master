import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt
from stock_analyzer import StockAnalyzer, analyze_multiple_stocks, analyze_portfolio

def print_header(title):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f" {title} ".center(80, "*"))
    print("=" * 80 + "\n")

def format_dollar(value):
    """Format a value as a dollar amount"""
    if value is None:
        return "N/A"
    return f"${value:.2f}"

def format_percent(value):
    """Format a value as a percentage"""
    if value is None:
        return "N/A"
    return f"{value:.2f}%"

def analyze_single_stock(ticker, save_report=False):
    """Analyze a single stock and display the results"""
    print(f"Analyzing {ticker}...")
    
    analyzer = StockAnalyzer(ticker)
    analysis = analyzer.analyze_stock()
    
    print_header(f"Analysis for {analysis['company_name']} ({ticker})")
    
    # Basic info
    print(f"Current Price: {format_dollar(analysis['metrics'].get('current_price'))}")
    print(f"Analysis Date: {analysis['analysis_date']}")
    
    # Key metrics
    print_header("Key Metrics")
    metrics = analysis['metrics']
    print(f"P/E Ratio: {metrics.get('pe_ratio', 'N/A')}")
    print(f"P/B Ratio: {metrics.get('pb_ratio', 'N/A')}")
    print(f"Debt-to-Equity: {metrics.get('debt_to_equity', 'N/A')}")
    print(f"Return on Equity: {format_percent(None if metrics.get('roe') is None else metrics.get('roe')*100)}")
    print(f"Return on Assets: {format_percent(None if metrics.get('roa') is None else metrics.get('roa')*100)}")
    print(f"Profit Margin: {format_percent(None if metrics.get('profit_margin') is None else metrics.get('profit_margin')*100)}")
    print(f"Dividend Yield: {format_percent(None if metrics.get('dividend_yield') is None else metrics.get('dividend_yield')*100)}")
    print(f"EPS (TTM): {format_dollar(metrics.get('eps'))}")
    print(f"Book Value Per Share: {format_dollar(metrics.get('book_value_per_share'))}")
    
    # Valuation methods
    print_header("Valuation Methods")
    
    # DCF
    if 'error' not in analysis['dcf_valuation']:
        dcf = analysis['dcf_valuation']
        print("1. Discounted Cash Flow (DCF) Valuation:")
        print(f"   Intrinsic Value: {format_dollar(dcf.get('intrinsic_value_per_share'))}")
        print(f"   Upside Potential: {format_percent(dcf.get('upside_potential'))}")
        print(f"   Total Present Value: {format_dollar(dcf.get('total_present_value'))}")
        print(f"   Terminal Value: {format_dollar(dcf.get('terminal_value'))}")
    else:
        print("1. Discounted Cash Flow (DCF) Valuation: Error - " + analysis['dcf_valuation']['error'])
    
    # Graham Number
    if 'error' not in analysis['graham_valuation']:
        graham = analysis['graham_valuation']
        print("\n2. Benjamin Graham Valuation:")
        print(f"   Graham Number: {format_dollar(graham.get('graham_number'))}")
        print(f"   Upside Potential: {format_percent(graham.get('upside_potential'))}")
    else:
        print("\n2. Benjamin Graham Valuation: Error - " + analysis['graham_valuation']['error'])
    
    # Buffett
    if 'error' not in analysis['buffett_valuation']:
        buffett = analysis['buffett_valuation']
        print("\n3. Warren Buffett Approach:")
        print(f"   Intrinsic Value: {format_dollar(buffett.get('intrinsic_value'))}")
        print(f"   Upside Potential: {format_percent(buffett.get('upside_potential'))}")
        print(f"   Expected Future Book Value: {format_dollar(buffett.get('future_book_value'))}")
        print(f"   Expected Future EPS: {format_dollar(buffett.get('future_eps'))}")
        print(f"   Expected Future Price: {format_dollar(buffett.get('future_price'))}")
    else:
        print("\n3. Warren Buffett Approach: Error - " + analysis['buffett_valuation']['error'])
    
    # Margin of Safety
    if 'margin_of_safety' in analysis:
        mos = analysis['margin_of_safety']
        print("\n4. Margin of Safety:")
        print(f"   Margin of Safety: {format_percent(mos.get('margin_of_safety_percent'))}")
        print(f"   Stock is {'UNDERVALUED' if mos.get('is_undervalued', False) else 'OVERVALUED'}")
    
    # Summary
    print_header("Investment Summary")
    summary = analysis['summary']
    
    # Assessments
    if 'dcf_assessment' in summary:
        print(f"- {summary['dcf_assessment']}")
    if 'graham_assessment' in summary:
        print(f"- {summary['graham_assessment']}")
    if 'buffett_assessment' in summary:
        print(f"- {summary['buffett_assessment']}")
    
    # Strengths and concerns
    if summary.get('strengths'):
        print("\nStrengths:")
        for strength in summary['strengths']:
            print(f"+ {strength}")
    
    if summary.get('concerns'):
        print("\nConcerns:")
        for concern in summary['concerns']:
            print(f"- {concern}")
    
    # Recommendation
    print("\nRecommendation:")
    print(f">>> {summary.get('recommendation', 'No recommendation available')}")
    
    # Visualizations
    if 'error' not in analysis.get('historical_pe', {'error': 'No data'}):
        plot_path = analysis['historical_pe'].get('plot_saved')
        if plot_path and os.path.exists(plot_path):
            print(f"\nP/E Ratio chart saved: {plot_path}")
    
    # Save report if requested
    if save_report:
        report_dir = 'analysis_reports'
        os.makedirs(report_dir, exist_ok=True)
        
        with open(f"{report_dir}/{ticker}_analysis.txt", 'w') as f:
            f.write(f"Analysis for {analysis['company_name']} ({ticker})\n")
            f.write(f"Analysis Date: {analysis['analysis_date']}\n\n")
            
            f.write("RECOMMENDATION: " + summary.get('recommendation', 'No recommendation available') + "\n\n")
            
            # Include all the detailed analysis in the report
            # ... (formatted report content)
            
        print(f"\nAnalysis report saved to {report_dir}/{ticker}_analysis.txt")
    
    return analysis

def compare_stocks(tickers):
    """Compare multiple stocks and rank them by investment potential"""
    print(f"Comparing stocks: {', '.join(tickers)}...")
    
    results = analyze_multiple_stocks(tickers)
    
    if results.empty:
        print("No valid analysis results were found.")
        return
    
    print_header("Stock Comparison Results")
    
    # Display results in a table
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 160)
    
    # Format the DataFrame for display
    display_df = results.copy()
    
    # Format price columns
    for col in ['current_price', 'dcf_intrinsic_value', 'graham_number', 'buffett_intrinsic_value']:
        display_df[col] = display_df[col].apply(lambda x: f"${x:.2f}" if pd.notnull(x) else "N/A")
    
    # Format percentage columns
    for col in ['dcf_upside', 'graham_upside', 'buffett_upside', 'avg_upside']:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    
    # Format ratio columns
    for col in ['pe_ratio', 'pb_ratio']:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notnull(x) else "N/A")
    
    # Format ROE as percentage
    display_df['roe'] = display_df['roe'].apply(lambda x: f"{x*100:.2f}%" if pd.notnull(x) else "N/A")
    
    # Select and reorder columns for display
    display_cols = [
        'ticker', 
        'company_name', 
        'current_price', 
        'avg_upside',
        'recommendation',
        'pe_ratio', 
        'pb_ratio', 
        'roe',
        'dcf_intrinsic_value', 
        'dcf_upside',
        'graham_number', 
        'graham_upside',
        'buffett_intrinsic_value', 
        'buffett_upside'
    ]
    
    display_df = display_df[display_cols]
    
    # Rename columns for better readability
    display_df.columns = [
        'Ticker', 
        'Company', 
        'Price', 
        'Avg Upside',
        'Recommendation',
        'P/E', 
        'P/B', 
        'ROE',
        'DCF Value', 
        'DCF Upside',
        'Graham Value', 
        'Graham Upside',
        'Buffett Value', 
        'Buffett Upside'
    ]
    
    print(display_df)
    
    # Create a visualization of the average upside potential
    plt.figure(figsize=(12, 6))
    
    # Sort by upside potential for the chart
    chart_data = results.sort_values('avg_upside', ascending=True)
    
    # Create bar colors (green for positive, red for negative)
    colors = ['green' if x >= 0 else 'red' for x in chart_data['avg_upside']]
    
    # Create the bar chart
    plt.barh(chart_data['ticker'], chart_data['avg_upside'], color=colors)
    plt.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    plt.title('Average Upside Potential by Stock')
    plt.xlabel('Potential Return (%)')
    plt.ylabel('Stock')
    
    # Add values to the end of each bar
    for i, value in enumerate(chart_data['avg_upside']):
        if pd.notnull(value):
            plt.text(value + (2 if value >= 0 else -2), 
                    i, 
                    f"{value:.1f}%", 
                    va='center',
                    ha='left' if value >= 0 else 'right')
    
    plt.tight_layout()
    
    # Save the plot
    plot_dir = 'analysis_outputs'
    os.makedirs(plot_dir, exist_ok=True)
    
    plot_file = f"{plot_dir}/stock_comparison.png"
    plt.savefig(plot_file)
    plt.close()
    
    print(f"\nComparison chart saved to: {plot_file}")
    
    # Display top investment choices
    best_stocks = results[results['avg_upside'] > 0].sort_values('avg_upside', ascending=False)
    
    if not best_stocks.empty:
        print_header("Top Investment Choices")
        for i, (_, row) in enumerate(best_stocks.head(3).iterrows(), 1):
            print(f"{i}. {row['ticker']} - {row['company_name']}")
            print(f"   Current Price: ${row['current_price']:.2f}")
            print(f"   Average Upside: {row['avg_upside']:.2f}%")
            print(f"   Recommendation: {row['recommendation']}")
            print()
    
    return results

def analyze_portfolio_holdings(portfolio_file):
    """Analyze a portfolio of stocks from a CSV file"""
    print(f"Analyzing portfolio from: {portfolio_file}")
    
    df, portfolio_upside, total_value = analyze_portfolio(portfolio_file)
    
    if df.empty:
        print("No valid portfolio data was found.")
        return
    
    print_header("Portfolio Analysis Results")
    
    # Portfolio overview
    print(f"Total Portfolio Value: ${total_value:.2f}")
    print(f"Overall Portfolio Upside Potential: {portfolio_upside:.2f}%")
    print(f"Number of Holdings: {len(df)}")
    print()
    
    # Display results in a table
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 160)
    
    # Format the DataFrame for display
    display_df = df.copy()
    
    # Format price columns
    for col in ['current_price', 'dcf_intrinsic_value', 'graham_number', 'buffett_intrinsic_value']:
        display_df[col] = display_df[col].apply(lambda x: f"${x:.2f}" if pd.notnull(x) else "N/A")
    
    # Format percentage columns
    for col in ['dcf_upside', 'graham_upside', 'buffett_upside', 'avg_upside', 'weight']:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}%" if pd.notnull(x) else "N/A")
    
    # Format dollar value columns
    display_df['position_value'] = display_df['position_value'].apply(lambda x: f"${x:.2f}" if pd.notnull(x) else "N/A")
    
    # Select and reorder columns for display
    display_cols = [
        'ticker', 
        'company_name', 
        'shares',
        'current_price', 
        'position_value',
        'weight',
        'avg_upside',
        'recommendation'
    ]
    
    display_df = display_df[display_cols]
    
    # Rename columns for better readability
    display_df.columns = [
        'Ticker', 
        'Company', 
        'Shares',
        'Price', 
        'Value',
        'Weight',
        'Upside',
        'Recommendation'
    ]
    
    print(display_df)
    
    # Create a pie chart of portfolio allocation
    plt.figure(figsize=(10, 8))
    plt.pie(df['position_value'], 
            labels=df['ticker'], 
            autopct='%1.1f%%',
            startangle=90,
            explode=[0.05 if i == df['position_value'].argmax() else 0 for i in range(len(df))])
    plt.axis('equal')
    plt.title('Portfolio Allocation by Value')
    
    # Save the allocation chart
    plot_dir = 'analysis_outputs'
    os.makedirs(plot_dir, exist_ok=True)
    
    allocation_file = f"{plot_dir}/portfolio_allocation.png"
    plt.savefig(allocation_file)
    plt.close()
    
    print(f"\nPortfolio allocation chart saved to: {allocation_file}")
    
    # Create a bar chart of upside potential by holding
    plt.figure(figsize=(12, 6))
    
    # Sort by upside potential for the chart
    chart_data = df.sort_values('avg_upside', ascending=True)
    
    # Create bar colors (green for positive, red for negative)
    colors = ['green' if x >= 0 else 'red' for x in chart_data['avg_upside']]
    
    # Create the bar chart
    plt.barh(chart_data['ticker'], chart_data['avg_upside'], color=colors)
    plt.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    plt.title('Upside Potential by Holding')
    plt.xlabel('Potential Return (%)')
    plt.ylabel('Stock')
    
    # Add values to the end of each bar
    for i, value in enumerate(chart_data['avg_upside']):
        if pd.notnull(value):
            plt.text(value + (2 if value >= 0 else -2), 
                    i, 
                    f"{value:.1f}%", 
                    va='center',
                    ha='left' if value >= 0 else 'right')
    
    plt.tight_layout()
    
    # Save the upside chart
    upside_file = f"{plot_dir}/portfolio_upside.png"
    plt.savefig(upside_file)
    plt.close()
    
    print(f"Portfolio upside chart saved to: {upside_file}")
    
    # Portfolio insights
    print_header("Portfolio Insights")
    
    # Holdings by potential
    undervalued = df[df['avg_upside'] > 0]
    overvalued = df[df['avg_upside'] <= 0]
    
    print(f"Undervalued holdings: {len(undervalued)} ({len(undervalued)/len(df)*100:.1f}% of portfolio)")
    print(f"Overvalued holdings: {len(overvalued)} ({len(overvalued)/len(df)*100:.1f}% of portfolio)")
    print()
    
    # Top performing holdings
    if not undervalued.empty:
        print("Top performing holdings:")
        for i, (_, row) in enumerate(undervalued.sort_values('avg_upside', ascending=False).head(3).iterrows(), 1):
            print(f"{i}. {row['ticker']} - {row['company_name']}")
            print(f"   Upside: {row['avg_upside']:.2f}%")
            print(f"   Portfolio Weight: {row['weight']*100:.2f}%")
            print()
    
    # Concerning holdings
    if not overvalued.empty:
        print("Holdings to review:")
        for i, (_, row) in enumerate(overvalued.sort_values('avg_upside', ascending=True).head(3).iterrows(), 1):
            print(f"{i}. {row['ticker']} - {row['company_name']}")
            print(f"   Downside: {-row['avg_upside']:.2f}%")
            print(f"   Portfolio Weight: {row['weight']*100:.2f}%")
            print()
    
    return df, portfolio_upside, total_value

def main():
    parser = argparse.ArgumentParser(description="Value Investor - Stock Analysis Tool")
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Single stock analysis
    stock_parser = subparsers.add_parser('stock', help='Analyze a single stock')
    stock_parser.add_argument('ticker', type=str, help='Stock ticker symbol')
    stock_parser.add_argument('--save', action='store_true', help='Save analysis report to file')
    
    # Multiple stock comparison
    compare_parser = subparsers.add_parser('compare', help='Compare multiple stocks')
    compare_parser.add_argument('tickers', type=str, nargs='+', help='List of stock ticker symbols')
    
    # Portfolio analysis
    portfolio_parser = subparsers.add_parser('portfolio', help='Analyze a portfolio')
    portfolio_parser.add_argument('file', type=str, help='Path to CSV file with portfolio holdings')
    
    args = parser.parse_args()
    
    if args.command == 'stock':
        analyze_single_stock(args.ticker, args.save)
    elif args.command == 'compare':
        compare_stocks(args.tickers)
    elif args.command == 'portfolio':
        analyze_portfolio_holdings(args.file)
    else:
        # If no command is provided, show help
        parser.print_help()

if __name__ == "__main__":
    main() 