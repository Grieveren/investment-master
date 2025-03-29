import logging
import argparse
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd

from src.backtesting.data.yfinance_connector import YFinanceConnector
from src.backtesting.models.ai_analyzer import AIAnalyzer
from src.backtesting.core.engine import BacktestEngine
from src.backtesting.visualization.plotter import BacktestPlotter
from src.backtesting.metrics.performance_metrics import calculate_performance_metrics
from src.backtesting.core.portfolio import Position

def test_portfolio_backtest(
    strategy: str = 'value',
    start_date: str = '2023-01-01',
    end_date: str = '2023-12-31',
    initial_capital: float = 100000.0,
    benchmark: str = 'SPY'
) -> None:
    """Run a portfolio backtest.
    
    Args:
        strategy: Trading strategy to use
        start_date: Start date for backtest (YYYY-MM-DD)
        end_date: End date for backtest (YYYY-MM-DD)
        initial_capital: Initial capital amount
        benchmark: Benchmark ticker symbol
    """
    print("\n================================================================================")
    print("Starting Portfolio Backtest")
    print("================================================================================")
    print("Parameters:")
    print(f"- Tickers: User's portfolio (5 stocks)")
    print(f"- Strategy: {strategy}")
    print(f"- Date range: {start_date} to {end_date}")
    print(f"- Benchmark: {benchmark}")
    print(f"- Initial capital: ${initial_capital:,.2f}")
    print("================================================================================\n")
    
    # Convert string dates to datetime.date objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Initialize components
    print("Initializing YFinanceConnector...")
    data_connector = YFinanceConnector()
    
    print(f"Initializing AIAnalyzer with strategy: {strategy}...")
    analyzer = AIAnalyzer(strategy=strategy)
    
    print("Initializing BacktestEngine...")
    engine = BacktestEngine(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        data_connector=data_connector,
        ai_analyzer=analyzer,
        benchmark=benchmark
    )
    
    # Define test tickers
    tickers = ['MSFT', 'AAPL', 'GOOGL', 'NVDA', 'TSLA']  # Simplified selection for testing
    
    # Load historical price data
    print("Loading historical price data...")
    engine.load_price_data(tickers)
    
    # Validate price data
    print("\nValidating price data:")
    for ticker in tickers:
        if ticker in engine.price_data:
            data = engine.price_data[ticker]
            print(f"✓ {ticker}: Loaded {len(data)} data points")
            print(f"  First date: {data.index[0].strftime('%Y-%m-%d')}")
            print(f"  Last date: {data.index[-1].strftime('%Y-%m-%d')}")
    
    if engine.benchmark_data is not None:
        print(f"✓ {benchmark} (Benchmark): Loaded {len(engine.benchmark_data)} data points")
        print(f"  First date: {engine.benchmark_data.index[0].strftime('%Y-%m-%d')}")
        print(f"  Last date: {engine.benchmark_data.index[-1].strftime('%Y-%m-%d')}")
    
    # Set initial portfolio
    print("\nSetting initial portfolio...")
    total_allocation = 0.0
    for ticker in tickers:
        allocation = 0.20  # Equal weight allocation
        shares = (allocation * initial_capital) / engine.price_data[ticker]['Close'].iloc[0]
        position = Position(
            ticker=ticker,
            shares=shares,
            entry_price=engine.price_data[ticker]['Close'].iloc[0],
            entry_date=start_date
        )
        engine.portfolio.add_position(position)
        print(f"Allocated {allocation*100:.2f}% to {ticker}")
        total_allocation += allocation
    print(f"Total allocation: {total_allocation*100:.2f}%")
    
    # Run backtest
    print("\nStarting backtest simulation...")
    results = engine.run_backtest()
    
    print("\nBacktest completed with", len(results), "data points")
    print(f"Initial portfolio value: ${results.iloc[0]['portfolio_value']:.2f}")
    print(f"Final portfolio value: ${results.iloc[-1]['portfolio_value']:.2f}")
    print(f"Total return: {((results.iloc[-1]['portfolio_value'] / results.iloc[0]['portfolio_value']) - 1) * 100:.2f}%")
    
    print("\nCalculating performance metrics...")
    metrics = calculate_performance_metrics(results)
    
    print("\nPerformance Metrics:")
    print(f"Total Return: {metrics['total_return']*100:.2f}%")
    print(f"Annualized Return: {metrics['annualized_return']*100:.2f}%")
    print(f"Volatility: {metrics['volatility']*100:.2f}%")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"Maximum Drawdown: {metrics['max_drawdown']*100:.2f}%")
    
    # Plot results
    print("\nPlotting results...")
    plot_backtest_results(results, engine.benchmark_data)

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description='Run a backtest on user portfolio')
    parser.add_argument('--strategy', type=str, default='value',
                        choices=['momentum', 'mean_reversion', 'trend_following', 'value'],
                        help='Strategy to use for analysis')
    parser.add_argument('--start_date', type=str, default='2023-01-01',
                        help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end_date', type=str, default='2023-12-31',
                        help='End date for backtest (YYYY-MM-DD)')
    parser.add_argument('--benchmark', type=str, default='SPY',
                        help='Benchmark ticker symbol')
    parser.add_argument('--initial_capital', type=float, default=100000.0,
                        help='Initial capital amount')
    
    args = parser.parse_args()
    
    # Run the backtest with command line arguments
    test_portfolio_backtest(
        strategy=args.strategy,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_capital=args.initial_capital,
        benchmark=args.benchmark
    ) 