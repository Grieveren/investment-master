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
  --use-cache                Use cached data if available (default: True)
  --no-cache                 Do not use cached data
  --cache-dir                Directory for cached data
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
    
    parser.add_argument(
        '--use-cache',
        action='store_true',
        default=True,
        help='Use cached data if available (default: True)'
    )
    
    parser.add_argument(
        '--no-cache',
        action='store_false',
        dest='use_cache',
        help='Do not use cached data'
    )
    
    parser.add_argument(
        '--cache-dir',
        type=str,
        default='data/cache',
        help='Directory for cached data'
    )
    
    return parser.parse_args()

def load_portfolio(portfolio_file):
    """Load the portfolio from a CSV file.
    
    Args:
        portfolio_file: Path to the portfolio CSV file
        
    Returns:
        Dictionary mapping ticker symbols to allocation percentages
    """
    logger.info(f"Loading portfolio from {portfolio_file}")
    
    try:
        df = pd.read_csv(portfolio_file)
        
        # Verify required columns
        if 'Security' not in df.columns or 'Weight' not in df.columns:
            logger.error("Portfolio file must contain 'Security' and 'Weight' columns")
            return {}
            
        # Extract portfolio with standardized ticker symbols
        portfolio = {}
        total_weight = 0
        
        for _, row in df.iterrows():
            security_name = row['Security']
            weight_str = row['Weight'].replace('%', '')
            weight = float(weight_str) / 100.0  # Convert percentage to decimal
            
            # Map the security name to a standard ticker symbol
            ticker = map_security_to_ticker(security_name)
            if ticker:
                if ticker in portfolio:
                    # If ticker already exists, add the weights
                    portfolio[ticker] += weight
                else:
                    portfolio[ticker] = weight
                    
                total_weight += weight
            else:
                logger.warning(f"Could not map security {security_name} to a ticker symbol, skipping")
        
        # Normalize weights if they don't sum to 1
        if total_weight > 0 and abs(total_weight - 1.0) > 0.01:
            logger.info(f"Normalizing portfolio weights (total was {total_weight})")
            for ticker in portfolio:
                portfolio[ticker] /= total_weight
                
        logger.info(f"Loaded portfolio with {len(portfolio)} positions")
        return portfolio
        
    except Exception as e:
        logger.error(f"Error loading portfolio: {e}")
        return {}

def map_security_to_ticker(security_name):
    """Map a security name to a standard ticker symbol.
    
    Args:
        security_name: The security name from the portfolio file
        
    Returns:
        Standard ticker symbol or None if mapping not found
    """
    # Mapping of security names to standard ticker symbols
    ticker_mapping = {
        'GitLab Inc.': 'GTLB',
        'ALLIANZ SE NA O.N.': 'ALV.DE',
        'ADVANCED MIC.DEV.  DL-,01': 'AMD',
        'BERKSH. H.B NEW DL-,00333': 'BRK-B',
        'MICROSOFT    DL-,00000625': 'MSFT',
        'ASML HOLDING    EO -,09': 'ASML',
        'ALPHABET INC.CL C DL-,001': 'GOOG',
        'CROWDSTRIKE HLD. DL-,0005': 'CRWD',
        'NUTANIX INC. A': 'NTNX',
        'NVIDIA CORP.      DL-,001': 'NVDA',
        'TAIWAN SEMICON.MANU.ADR/5': 'TSM'
    }
    
    return ticker_mapping.get(security_name)

def ensure_output_dirs():
    """Ensure output directories exist."""
    os.makedirs('data/backtesting', exist_ok=True)
    os.makedirs('data/backtesting/charts', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Make cache directory if needed
    if args.use_cache:
        os.makedirs(args.cache_dir, exist_ok=True)

def main():
    """Run the backtest."""
    # Parse command-line arguments
    global args
    args = parse_arguments()
    
    # Ensure output directories exist
    ensure_output_dirs()
    
    logger.info("Starting backtest")
    logger.info(f"Period: {args.start_date} to {args.end_date}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Frequency: {args.frequency}")
    logger.info(f"Using data cache: {args.use_cache}")
    
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
    data_connector = YFinanceConnector(
        use_cache=args.use_cache,
        cache_dir=args.cache_dir,
        max_retries=5,
        base_delay=1.0,
        batch_size=3
    )
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