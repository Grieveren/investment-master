#!/usr/bin/env python
"""
End-to-end test for the backtesting system with mock data.

This script runs a complete backtest with simulated historical data for a small test portfolio.
"""

import sys
import os
import datetime
import pandas as pd
import numpy as np
import logging
from typing import Dict
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/end_to_end_backtest.log', mode='w'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger('end_to_end_backtest')

# Import backtesting components
from src.backtesting.core.engine import BacktestEngine
from src.backtesting.data.yfinance_connector import YFinanceConnector
from src.backtesting.visualization.plotter import BacktestPlotter

def create_mock_price_data(start_date, end_date, tickers):
    """Create mock price data for testing.
    
    Args:
        start_date: Start date for the data
        end_date: End date for the data
        tickers: List of ticker symbols
        
    Returns:
        Dictionary mapping ticker symbols to price DataFrames
    """
    # Create date range for business days
    dates = pd.date_range(start_date, end_date, freq='B')
    
    # Dictionary to store price data
    price_data = {}
    
    # Base values for different tickers
    base_values = {
        'AAPL': 150,
        'MSFT': 300,
        'GOOGL': 2700,
        'SPY': 450
    }
    
    # Create price data for each ticker
    for ticker in tickers:
        base = base_values.get(ticker, 100)
        
        # Create random walk with overall upward trend
        np.random.seed(hash(ticker) % 10000)  # Use ticker as seed for reproducibility
        
        # Generate random price movements
        random_walk = np.random.normal(0.0005, 0.015, len(dates)).cumsum()
        trend = np.linspace(0, 0.2, len(dates))  # 20% upward trend
        
        # Combine trend and random walk
        movements = trend + random_walk
        
        # Generate price series
        closes = base * (1 + movements)
        opens = closes * np.random.uniform(0.99, 1.01, len(dates))
        highs = closes * np.random.uniform(1.0, 1.02, len(dates))
        lows = closes * np.random.uniform(0.98, 1.0, len(dates))
        volumes = np.random.randint(1000000, 10000000, len(dates))
        
        # Create DataFrame
        df = pd.DataFrame({
            'Open': opens,
            'High': highs,
            'Low': lows,
            'Close': closes,
            'Volume': volumes
        }, index=dates)
        
        price_data[ticker] = df
    
    return price_data

def run_end_to_end_test():
    """Run an end-to-end test of the backtesting system with mock data."""
    logger.info("Starting end-to-end backtest test")
    
    # Test parameters
    start_date = datetime.date(2022, 1, 1)
    end_date = datetime.date(2022, 12, 31)
    initial_capital = 100000.0
    rebalance_frequency = 'month'
    benchmark = 'SPY'
    
    # Test portfolio (simple 3-stock portfolio)
    portfolio = {
        'AAPL': 0.33,  # Apple
        'MSFT': 0.33,  # Microsoft
        'GOOGL': 0.34  # Alphabet (Google)
    }
    
    logger.info(f"Test portfolio: {portfolio}")
    logger.info(f"Test period: {start_date} to {end_date}")
    
    # Ensure output directories exist
    os.makedirs('data/backtesting', exist_ok=True)
    os.makedirs('data/backtesting/charts', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    # Create the backtest engine
    engine = BacktestEngine(
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        rebalance_frequency=rebalance_frequency
    )
    
    # Set initial portfolio
    engine.set_initial_portfolio(portfolio)
    
    # Create mock price data
    logger.info("Creating mock historical price data")
    all_tickers = list(portfolio.keys()) + [benchmark]
    price_data = create_mock_price_data(start_date, end_date, all_tickers)
    
    # Split price data into portfolio and benchmark
    portfolio_price_data = {ticker: data for ticker, data in price_data.items() if ticker in portfolio}
    benchmark_data = price_data.get(benchmark)
    
    logger.info(f"Created mock price data for {len(portfolio_price_data)} stocks and benchmark")
    
    # Set price data in the engine
    engine.price_data = portfolio_price_data
    
    # Run the backtest
    try:
        logger.info("Running backtest simulation")
        
        # Mock the AI analyzer to return simple recommendations
        with patch('src.backtesting.models.ai_analyzer.AIAnalyzer') as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer
            
            # Configure the mock analyzer to return recommendations
            def mock_analyze(date, ticker, price_data, fundamental_data, context=None):
                # Simple mock recommendation logic based on recent price movement
                recent_close = price_data['Close'].iloc[-5:]
                if recent_close.iloc[-1] > recent_close.iloc[0]:
                    recommendation = 'buy'
                else:
                    recommendation = 'sell'
                    
                return {
                    'date': date,
                    'ticker': ticker,
                    'recommendation': recommendation,
                    'target_allocation': portfolio[ticker] * 1.1 if recommendation == 'buy' else portfolio[ticker] * 0.9,
                    'reasoning': f"Mock reasoning for {ticker}"
                }
                
            mock_analyzer.analyze_snapshot.side_effect = mock_analyze
            
            # Run backtest
            results = engine.run_backtest(model_name='claude-3-7')
        
        if results is None or results.empty:
            logger.error("Backtest produced no results")
            return False
            
        logger.info(f"Backtest completed with {len(results)} data points")
        
        # Calculate performance metrics
        metrics = engine.calculate_metrics()
        logger.info(f"Performance metrics: {metrics}")
        
        # Compare to benchmark
        if benchmark_data is not None:
            comparison = engine.compare_to_benchmark(benchmark=benchmark)
            logger.info(f"Benchmark comparison: {comparison}")
        
        # Visualize results
        plotter = BacktestPlotter()
        
        # Plot portfolio performance
        logger.info("Generating performance visualization")
        with patch('src.backtesting.visualization.plotter.MATPLOTLIB_AVAILABLE', True):
            plotter.plot_portfolio_performance(
                nav_history=results,
                benchmark_history=benchmark_data,
                title=f"Tech Portfolio Performance: {start_date} to {end_date}",
                filename="e2e_test_performance.png"
            )
            
            # Plot drawdown
            logger.info("Generating drawdown visualization")
            plotter.plot_drawdown(
                nav_history=results,
                title=f"Tech Portfolio Drawdown: {start_date} to {end_date}",
                filename="e2e_test_drawdown.png"
            )
        
        # Save results
        logger.info("Saving backtest results")
        results.to_csv('data/backtesting/e2e_test_results.csv', index=False)
        
        # Save metrics
        pd.DataFrame([metrics]).to_csv('data/backtesting/e2e_test_metrics.csv', index=False)
        
        logger.info("End-to-end test completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error during backtest: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == '__main__':
    success = run_end_to_end_test()
    sys.exit(0 if success else 1) 