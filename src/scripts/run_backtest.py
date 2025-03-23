#!/usr/bin/env python
"""
Run a backtest of AI investment recommendations over a historical time period.

This script runs a backtest simulation of AI-based investment recommendations
on historical data, allowing you to evaluate how the recommendations would
have performed over a given time period.

Usage:
  python run_backtest.py --start-date YYYY-MM-DD --end-date YYYY-MM-DD [options]

Options:
  --start-date YYYY-MM-DD     Start date for the backtest
  --end-date YYYY-MM-DD       End date for the backtest
  --model MODEL               AI model to use (claude-3-7 or o3-mini)
  --portfolio FILE            Initial portfolio file (CSV)
  --capital AMOUNT            Initial capital (default: 100000)
  --frequency PERIOD          Rebalancing frequency (day, week, month, quarter) (default: month)
  --benchmark TICKER          Benchmark ticker symbol (default: SPY)
"""

import argparse
import datetime
import json
import logging
import os
import sys
import pandas as pd
from typing import Dict, List, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/backtest.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('backtest')

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import backtesting modules
from src.backtesting.core.engine import BacktestEngine
from src.backtesting.data.yfinance_connector import YFinanceConnector
from src.backtesting.visualization.plotter import BacktestPlotter

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Run a backtest of AI investment recommendations')
    
    parser.add_argument(
        '--start-date',
        type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(),
        required=True,
        help='Start date for the backtest (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--end-date',
        type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d').date(),
        required=True,
        help='End date for the backtest (YYYY-MM-DD)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='claude-3-7',
        choices=['claude-3-7', 'o3-mini'],
        help='AI model to use (claude-3-7 or o3-mini)'
    )
    
    parser.add_argument(
        '--portfolio',
        type=str,
        default='data/source/combined_portfolio.csv',
        help='Initial portfolio file (CSV)'
    )
    
    parser.add_argument(
        '--capital',
        type=float,
        default=100000.0,
        help='Initial capital'
    )
    
    parser.add_argument(
        '--frequency',
        type=str,
        default='month',
        choices=['day', 'week', 'month', 'quarter'],
        help='Rebalancing frequency'
    )
    
    parser.add_argument(
        '--benchmark',
        type=str,
        default='SPY',
        help='Benchmark ticker symbol'
    )
    
    return parser.parse_args()

def load_portfolio(portfolio_file: str) -> Dict[str, float]:
    """Load portfolio from CSV file.
    
    Args:
        portfolio_file: Path to CSV file
        
    Returns:
        Dictionary mapping ticker symbols to allocation percentages
    """
    logger.info(f"Loading portfolio from {portfolio_file}")
    
    try:
        # This is a simplified implementation - in a real system,
        # you would adapt this to match your actual CSV format
        df = pd.read_csv(portfolio_file)
        
        # Assuming the CSV has 'ticker' and 'allocation' columns
        # Adapt this to match your actual CSV format
        if 'ticker' in df.columns and 'allocation' in df.columns:
            portfolio = {row['ticker']: row['allocation'] for _, row in df.iterrows()}
        elif 'Symbol' in df.columns and 'Weight' in df.columns:
            portfolio = {row['Symbol']: row['Weight'] for _, row in df.iterrows()}
        else:
            # Fallback approach - try to guess which columns are relevant
            # This would need to be adapted to your specific file format
            ticker_col = None
            alloc_col = None
            
            for col in df.columns:
                if col.lower() in ['ticker', 'symbol', 'stock', 'security']:
                    ticker_col = col
                elif col.lower() in ['allocation', 'weight', 'percentage', 'alloc']:
                    alloc_col = col
                    
            if ticker_col and alloc_col:
                portfolio = {row[ticker_col]: row[alloc_col] for _, row in df.iterrows()}
            else:
                logger.error("Could not identify ticker and allocation columns in portfolio file")
                return {}
                
        logger.info(f"Loaded portfolio with {len(portfolio)} positions")
        return portfolio
        
    except Exception as e:
        logger.error(f"Error loading portfolio from {portfolio_file}: {e}")
        return {}

def ensure_output_dirs():
    """Ensure output directories exist."""
    os.makedirs('data/backtesting', exist_ok=True)
    os.makedirs('data/backtesting/charts', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

def main():
    """Run the backtest."""
    # Parse command-line arguments
    args = parse_arguments()
    
    # Ensure output directories exist
    ensure_output_dirs()
    
    logger.info("Starting backtest")
    logger.info(f"Period: {args.start_date} to {args.end_date}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Frequency: {args.frequency}")
    
    # Load portfolio
    portfolio = load_portfolio(args.portfolio)
    if not portfolio:
        logger.error("Failed to load portfolio. Exiting.")
        return
    
    # Set up backtest engine
    engine = BacktestEngine(
        start_date=args.start_date,
        end_date=args.end_date,
        initial_capital=args.capital,
        rebalance_frequency=args.frequency
    )
    
    # Set initial portfolio
    engine.set_initial_portfolio(portfolio)
    
    # Load historical price data
    data_connector = YFinanceConnector()
    tickers = list(portfolio.keys())
    
    # Get historical price data for portfolio and benchmark
    try:
        price_data = data_connector.get_historical_prices(
            tickers=tickers,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        benchmark_data = data_connector.get_benchmark_data(
            benchmark=args.benchmark,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        # Set the price data in the engine
        engine.price_data = price_data
        
    except Exception as e:
        logger.error(f"Error loading historical data: {e}")
        return
    
    # Run the backtest
    try:
        logger.info("Running backtest simulation")
        results = engine.run_backtest(model_name=args.model)
        
        # Calculate performance metrics
        metrics = engine.calculate_metrics()
        
        # Compare to benchmark
        comparison = engine.compare_to_benchmark(benchmark=args.benchmark)
        
        # Generate visualizations
        plotter = BacktestPlotter()
        
        # Plot portfolio performance
        nav_history = engine.results  # Assuming results includes nav_history
        
        plotter.plot_portfolio_performance(
            nav_history=nav_history,
            benchmark_history=benchmark_data,
            title=f"Portfolio Performance: {args.start_date} to {args.end_date}"
        )
        
        # Plot drawdown
        plotter.plot_drawdown(
            nav_history=nav_history,
            title=f"Portfolio Drawdown: {args.start_date} to {args.end_date}"
        )
        
        # Save results to file
        output_file = f"data/backtesting/backtest_results_{args.start_date}_{args.end_date}.json"
        
        with open(output_file, 'w') as f:
            output = {
                'backtest_period': {
                    'start_date': args.start_date.isoformat(),
                    'end_date': args.end_date.isoformat()
                },
                'model': args.model,
                'rebalance_frequency': args.frequency,
                'initial_capital': args.capital,
                'performance_metrics': metrics,
                'benchmark_comparison': comparison
            }
            json.dump(output, f, indent=2)
            
        logger.info(f"Backtest completed successfully. Results saved to {output_file}")
        
    except Exception as e:
        logger.error(f"Error during backtest: {e}")

if __name__ == '__main__':
    main() 