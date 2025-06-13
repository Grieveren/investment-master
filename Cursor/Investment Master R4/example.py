#!/usr/bin/env python3
"""
Example script demonstrating how to use the investment analysis tool programmatically.
"""

from stock_analyzer import StockAnalyzer, analyze_multiple_stocks, analyze_portfolio
import pandas as pd
import os
import matplotlib.pyplot as plt

def example_single_stock_analysis():
    """Demonstrate single stock analysis"""
    print("\n=== Example: Single Stock Analysis ===\n")
    
    # Create an analyzer object for Apple
    apple = StockAnalyzer('AAPL')
    
    # Get financial data
    financial_data = apple.get_financial_data()
    print(f"Retrieved financial data for {apple.company_name}")
    
    # Calculate key metrics
    metrics = apple.calculate_key_metrics()
    print("\nKey Metrics:")
    for key, value in metrics.items():
        print(f"{key}: {value}")
    
    # Calculate intrinsic value using DCF
    dcf = apple.calculate_dcf(growth_rate=0.12, discount_rate=0.09)
    print("\nDCF Valuation:")
    for key, value in dcf.items():
        print(f"{key}: {value}")
    
    # Calculate Graham Number
    graham = apple.calculate_graham_number()
    print("\nGraham Number Valuation:")
    for key, value in graham.items():
        print(f"{key}: {value}")
    
    # Full analysis
    print("\nPerforming full analysis...")
    analysis = apple.analyze_stock()
    
    # Print recommendation
    print(f"\nRecommendation: {analysis['summary']['recommendation']}")
    
    return analysis

def example_stock_comparison():
    """Demonstrate comparing multiple stocks"""
    print("\n=== Example: Stock Comparison ===\n")
    
    # Define a list of big tech stocks
    tech_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META']
    
    print(f"Comparing stocks: {', '.join(tech_stocks)}")
    
    # Analyze and compare
    results = analyze_multiple_stocks(tech_stocks)
    
    # Print results
    print("\nComparison Results (sorted by potential upside):")
    print(results[['ticker', 'company_name', 'current_price', 'avg_upside', 'recommendation']])
    
    # Create a simple visualization
    plt.figure(figsize=(10, 5))
    plt.bar(results['ticker'], results['avg_upside'])
    plt.axhline(y=0, color='r', linestyle='-', alpha=0.3)
    plt.title('Investment Potential by Stock')
    plt.xlabel('Stock')
    plt.ylabel('Average Upside Potential (%)')
    
    os.makedirs('example_outputs', exist_ok=True)
    plt.savefig('example_outputs/comparison_chart.png')
    plt.close()
    
    print("\nComparison chart saved to example_outputs/comparison_chart.png")
    
    return results

def example_portfolio_analysis():
    """Demonstrate portfolio analysis"""
    print("\n=== Example: Portfolio Analysis ===\n")
    
    # Use the sample portfolio file
    portfolio_file = 'sample_portfolio.csv'
    
    # Check if the file exists
    if not os.path.exists(portfolio_file):
        print(f"Error: {portfolio_file} not found.")
        return
    
    print(f"Analyzing portfolio in {portfolio_file}")
    
    # Analyze portfolio
    df, portfolio_upside, total_value = analyze_portfolio(portfolio_file)
    
    # Print summary
    print(f"\nPortfolio Summary:")
    print(f"Total Value: ${total_value:.2f}")
    print(f"Overall Upside Potential: {portfolio_upside:.2f}%")
    print(f"Number of Holdings: {len(df)}")
    
    # Show top 3 holdings by value
    print("\nTop Holdings by Value:")
    top_holdings = df.sort_values('position_value', ascending=False).head(3)
    for _, row in top_holdings.iterrows():
        print(f"{row['ticker']} - ${row['position_value']:.2f} ({row['weight']*100:.2f}% of portfolio)")
    
    # Show most undervalued stocks
    print("\nMost Undervalued Holdings:")
    undervalued = df[df['avg_upside'] > 0].sort_values('avg_upside', ascending=False).head(3)
    for _, row in undervalued.iterrows():
        print(f"{row['ticker']} - Upside: {row['avg_upside']:.2f}%")
    
    return df, portfolio_upside, total_value

def main():
    """Run all examples"""
    try:
        # Run single stock analysis
        analysis = example_single_stock_analysis()
        
        # Run stock comparison
        results = example_stock_comparison()
        
        # Run portfolio analysis
        portfolio_results = example_portfolio_analysis()
        
        print("\n=== All examples completed successfully ===")
        
    except Exception as e:
        print(f"\nError running examples: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 