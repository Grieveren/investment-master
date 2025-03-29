"""
Comprehensive test for the full backtesting pipeline.
This script tests all components working together: YFinanceConnector, BacktestEngine, AIAnalyzer, and BacktestPlotter.
"""

import os
import sys
import logging
import datetime
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Optional

from src.backtesting.data.yfinance_connector import YFinanceConnector
from src.backtesting.core.engine import BacktestEngine
from src.backtesting.analysis.ai_analyzer import AIAnalyzer
from src.backtesting.visualization.plotter import BacktestPlotter

# Set up logging to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_full_backtest_pipeline(strategy='momentum'):
    """
    Test the full backtest pipeline from data retrieval to visualization.
    
    Args:
        strategy: The trading strategy to use ('momentum', 'mean_reversion', 'trend_following', 'value')
    """
    print("\n========= STARTING FULL BACKTEST PIPELINE TEST =========\n")
    
    # Test parameters
    tickers = ["AAPL", "MSFT", "GOOGL"]
    start_date = datetime.date(2023, 1, 1)
    end_date = datetime.date(2023, 12, 31)
    benchmark = "SPY"
    initial_cash = 100000.0
    
    print(f"Test parameters:")
    print(f"- Tickers: {', '.join(tickers)}")
    print(f"- Strategy: {strategy}")
    print(f"- Date range: {start_date} to {end_date}")
    print(f"- Benchmark: {benchmark}")
    print(f"- Initial cash: ${initial_cash:.2f}\n")
    
    # Ensure directories exist
    os.makedirs('data/cache', exist_ok=True)
    os.makedirs('data/backtesting', exist_ok=True)
    
    logger.info("========= STARTING FULL BACKTEST PIPELINE TEST =========")
    
    # Step 1: Initialize YFinanceConnector with rate limiting and caching
    print("Step 1: Initializing YFinanceConnector")
    connector = YFinanceConnector(
        cache_dir='data/cache',
        rate_limit=0.2,  # 5 requests per second
        cache_expire_days=30  # 30 days
    )
    print("YFinanceConnector initialized successfully")
    
    # Step 2: Initialize AI Analyzer
    print("Step 2: Initializing AIAnalyzer")
    analyzer = AIAnalyzer(
        strategy=strategy,
        lookback_period=20,
        rebalance_threshold=0.05
    )
    print("AIAnalyzer initialized successfully")
    
    # Step 3: Initialize BacktestEngine
    print("Step 3: Initializing BacktestEngine")
    engine = BacktestEngine(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_cash,
        benchmark=benchmark,
        data_connector=connector,
        ai_analyzer=analyzer
    )
    print("BacktestEngine initialized successfully")
    
    # Step 4: Load price data
    print("\nStep 4: Loading price data...")
    if not engine.load_price_data(tickers):
        print("ERROR: Failed to load price data")
        return False
    
    # Validate price data
    all_data_loaded = True
    print("\nValidating price data:")
    
    # Validate ticker data
    for ticker in tickers:
        data = engine.price_data.get(ticker)
        if data is not None and not data.empty:
            print(f"✓ {ticker}: Loaded {len(data)} data points")
            print(f"  First date: {data.index[0].strftime('%Y-%m-%d')}")
            print(f"  Last date: {data.index[-1].strftime('%Y-%m-%d')}")
        else:
            print(f"✗ {ticker}: No data loaded")
            all_data_loaded = False
    
    # Validate benchmark data
    if engine.benchmark_data is not None and not engine.benchmark_data.empty:
        print(f"✓ {benchmark} (Benchmark): Loaded {len(engine.benchmark_data)} data points")
        print(f"  First date: {engine.benchmark_data.index[0].strftime('%Y-%m-%d')}")
        print(f"  Last date: {engine.benchmark_data.index[-1].strftime('%Y-%m-%d')}")
    else:
        print(f"✗ {benchmark} (Benchmark): No data loaded")
        all_data_loaded = False
    
    if not all_data_loaded:
        print("\nERROR: Not all price data was loaded. Terminating test.")
        return False
    
    # Step 5: Set initial portfolio
    print("\nStep 5: Setting initial portfolio")
    try:
        initial_portfolio = {}
        total_allocation = 0.0
        
        # Create portfolio with equal weights
        for ticker in tickers:
            if ticker in engine.price_data and not engine.price_data[ticker].empty:
                allocation = 1.0 / len(tickers)  # Equal weight allocation
                initial_portfolio[ticker] = allocation
                total_allocation += allocation
                print(f"  {ticker}: {allocation:.2%} allocation")
        
        print(f"Total allocation: {total_allocation:.2%}")
        engine.set_initial_portfolio(initial_portfolio)
        print("Initial portfolio set successfully")
    except Exception as e:
        print(f"ERROR: Failed to set initial portfolio: {e}")
        return False
    
    # Step 6: Run backtest
    print("\nStep 6: Running backtest...")
    try:
        results = engine.run_backtest()
        
        if results is None or results.empty:
            print("ERROR: Backtest returned empty results")
            return False
        
        print(f"Backtest completed with {len(results)} data points")
        print(f"Initial portfolio value: ${results['Portfolio Value'].iloc[0]:.2f}")
        print(f"Final portfolio value: ${results['Portfolio Value'].iloc[-1]:.2f}")
        
        # Calculate return
        total_return = (results['Portfolio Value'].iloc[-1] / results['Portfolio Value'].iloc[0] - 1) * 100
        print(f"Total return: {total_return:.2f}%")
        
    except Exception as e:
        print(f"ERROR: Backtest execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 7: Calculate metrics
    print("\nStep 7: Calculating performance metrics")
    try:
        metrics = engine.calculate_metrics()
        print("Performance metrics:")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
    except Exception as e:
        print(f"ERROR: Failed to calculate metrics: {e}")
        import traceback
        traceback.print_exc()
        # Continue to visualization even if metrics calculation fails
    
    # Step 8: Visualize results
    print("\nStep 8: Creating visualizations")
    try:
        plotter = BacktestPlotter(
            results=results,
            benchmark_data=engine.benchmark_data,
            start_date=start_date,
            end_date=end_date
        )
        
        # Plot performance
        perf_success = plotter.plot_portfolio_performance()
        print(f"Portfolio performance plot: {'Created' if perf_success else 'Failed'}")
        
        # Plot drawdown
        dd_success = plotter.plot_drawdown()
        print(f"Drawdown plot: {'Created' if dd_success else 'Failed'}")
        
        # Plot monthly returns
        mr_success = plotter.plot_monthly_returns()
        print(f"Monthly returns plot: {'Created' if mr_success else 'Failed'}")
        
        if perf_success and dd_success and mr_success:
            print("All visualizations created successfully")
        else:
            print("WARNING: Some visualizations failed to create")
    except Exception as e:
        print(f"ERROR: Visualization failed: {e}")
        import traceback
        traceback.print_exc()
        # Continue even if visualization fails
    
    print("\n========= FULL BACKTEST PIPELINE TEST COMPLETED =========\n")
    return True

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the full backtest pipeline test')
    parser.add_argument('--strategy', type=str, default='momentum', 
                        choices=['momentum', 'mean_reversion', 'trend_following', 'value'],
                        help='Trading strategy to use for the backtest')
    args = parser.parse_args()
    
    success = test_full_backtest_pipeline(strategy=args.strategy)
    print(f"\nTest result: {'SUCCESS' if success else 'FAILURE'}")
    sys.exit(0 if success else 1) 