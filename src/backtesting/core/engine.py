"""
Backtesting engine for Investment Master.

This module provides the main BacktestEngine class that orchestrates the backtesting process.
"""

import datetime
import logging
import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
from typing import Dict, List, Optional, Tuple, Union, Any
from src.backtesting.data.yfinance_connector import YFinanceConnector
from src.backtesting.core.portfolio import Portfolio, Position
from src.backtesting.core.simulator import PortfolioSimulator
from src.backtesting.visualization.plotter import BacktestPlotter

logger = logging.getLogger(__name__)

class BacktestEngine:
    """Main backtesting engine class for Investment Master.
    
    This class coordinates the backtesting process, including:
    - Loading historical data
    - Running AI analysis on historical snapshots
    - Simulating portfolio changes based on recommendations
    - Calculating performance metrics
    - Comparing results against benchmarks
    """
    
    def __init__(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        initial_capital: float = 100000.0,
        benchmark: str = 'SPY',
        data_connector=None,
        ai_analyzer=None
    ):
        """Initialize the backtesting engine.
        
        Args:
            start_date: The start date for the backtest
            end_date: The end date for the backtest
            initial_capital: The initial capital to start with
            benchmark: The benchmark ticker symbol
            data_connector: Optional custom data connector
            ai_analyzer: Optional AI analyzer for generating signals
        """
        self.start_date = start_date
        self.end_date = end_date
        self.initial_capital = initial_capital
        self.benchmark = benchmark
        
        # Initialize connector for retrieving historical data
        if data_connector is None:
            self.data_connector = YFinanceConnector(
                use_cache=True,
                cache_dir='data/cache',
                cache_expire_days=30,  # Cache data for a month to reduce API calls
                rate_limit=0.5,  # 1 request every 2 seconds
                batch_size=1     # Process one ticker at a time for reliability
            )
        else:
            self.data_connector = data_connector
        
        # Initialize the portfolio
        self.portfolio = Portfolio(initial_capital=initial_capital)
        
        # Store price data
        self.price_data = {}
        self.benchmark_data = None
        
        # Store backtest results
        self.results = None
        
        # AI analyzer for generating signals
        self.ai_analyzer = ai_analyzer
        
        # The portfolio simulator
        self.simulator = None
        
        logger.info(f"Initialized BacktestEngine from {start_date} to {end_date}")
    
    def load_price_data(self, tickers: List[str]) -> bool:
        """Load historical price data for the tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Whether the data was successfully loaded
        """
        logger.info(f"Loading historical price data for {len(tickers)} tickers")
        
        try:
            # Load historical prices
            self.price_data = self.data_connector.get_historical_prices(
                tickers=tickers,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # Load benchmark data
            self.benchmark_data = self.data_connector.get_benchmark_data(
                benchmark=self.benchmark,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            if not self.price_data:
                logger.error("Failed to load any price data")
                return False
                
            if self.benchmark_data is None or self.benchmark_data.empty:
                logger.error(f"Failed to load benchmark data for {self.benchmark}")
                return False
                
            loaded_tickers = list(self.price_data.keys())
            missing_tickers = [t for t in tickers if t not in loaded_tickers]
            
            if missing_tickers:
                logger.warning(f"Missing price data for {len(missing_tickers)}/{len(tickers)} tickers: {missing_tickers}")
            
            logger.info(f"Successfully loaded price data for {len(loaded_tickers)}/{len(tickers)} tickers")
            return len(loaded_tickers) > 0
            
        except Exception as e:
            logger.error(f"Error loading price data: {e}")
            return False
    
    def load_fundamental_data(self, data_source: str = 'sws') -> None:
        """Load historical fundamental data for the portfolio.
        
        Args:
            data_source: The source to load fundamental data from ('sws', 'csv')
        """
        logger.info(f"Loading fundamental data from {data_source}")
        # Implementation will connect to the chosen data source
        # and populate self.fundamental_data
    
    def set_initial_portfolio(self, positions: Dict[str, float]) -> None:
        """Set the initial portfolio allocation.
        
        Args:
            positions: Dictionary mapping ticker symbols to allocation weights
        """
        # Reset the portfolio to initial capital
        self.portfolio = Portfolio(initial_capital=self.initial_capital)
        
        # Check if we have price data for all positions
        for ticker in positions:
            if ticker not in self.price_data:
                logger.warning(f"No price data for {ticker}, removing from initial portfolio")
                continue
                
            # Get the first available price
            price_history = self.price_data[ticker]
            if price_history.empty:
                logger.warning(f"Empty price history for {ticker}, removing from initial portfolio")
                continue
                
            first_price = price_history.iloc[0]['Close']
            
            # Calculate the number of shares based on the allocation weight
            allocation_amount = self.initial_capital * positions[ticker]
            shares = allocation_amount / first_price
            
            # Add the position to the portfolio
            self.portfolio.add_position(Position(
                ticker=ticker,
                shares=shares,
                entry_price=first_price,
                entry_date=self.start_date
            ))
            
        logger.info(f"Set initial portfolio with {len(self.portfolio.positions)} positions")
    
    def run_backtest(self) -> pd.DataFrame:
        """Run the backtest simulation and return results.
        
        Returns:
            DataFrame with backtest results
        """
        logger.info("Starting backtest simulation")
        
        # Create a simulator
        self.simulator = PortfolioSimulator(
            portfolio=self.portfolio,
            price_data=self.price_data,
            start_date=self.start_date,
            end_date=self.end_date,
            ai_analyzer=self.ai_analyzer
        )
        
        # Run the simulation
        self.results = self.simulator.run_simulation()
        
        # For now, we'll just return an empty DataFrame placeholder
        # In a real implementation, this would contain portfolio values over time
        if self.results is None:
            logger.error("Backtest simulation failed to produce results")
            return pd.DataFrame()
            
        logger.info("Backtest simulation completed successfully")
        return self.results
    
    def calculate_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics for the backtest.
        
        Returns:
            Dictionary of performance metrics
        """
        if self.results is None or self.results.empty:
            logger.error("No backtest results available for calculating metrics")
            return {}
            
        logger.info("Calculating performance metrics")
        
        # Extract portfolio values over time
        portfolio_values = self.results['Portfolio Value']
        
        # Calculate basic metrics
        start_value = portfolio_values.iloc[0]
        end_value = portfolio_values.iloc[-1]
        total_return = (end_value / start_value) - 1
        
        # Calculate annualized return
        days = (self.end_date - self.start_date).days
        years = days / 365
        annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        
        # Calculate volatility (annualized standard deviation of daily returns)
        daily_returns = portfolio_values.pct_change().dropna()
        volatility = daily_returns.std() * (252 ** 0.5)  # Annualized
        
        # Calculate Sharpe ratio (assuming risk-free rate of 0 for simplicity)
        sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
        
        # Calculate drawdown
        cumulative_max = portfolio_values.cummax()
        drawdown = (portfolio_values / cumulative_max) - 1
        max_drawdown = drawdown.min()
        
        # Store the metrics
        metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'final_portfolio_value': end_value
        }
        
        logger.info(f"Performance metrics: {metrics}")
        return metrics
    
    def compare_to_benchmark(self) -> Dict[str, Any]:
        """Compare backtest performance to the benchmark.
        
        Returns:
            Dictionary of comparative metrics
        """
        if self.results is None or self.results.empty or self.benchmark_data is None or self.benchmark_data.empty:
            logger.error("Missing data for benchmark comparison")
            return {}
            
        logger.info(f"Comparing performance to benchmark ({self.benchmark})")
        
        # Extract portfolio values and benchmark prices
        portfolio_values = self.results['Portfolio Value']
        benchmark_prices = self.benchmark_data['Close']
        
        # Align dates
        common_dates = portfolio_values.index.intersection(benchmark_prices.index)
        if len(common_dates) == 0:
            logger.error("No overlapping dates between portfolio and benchmark")
            return {}
            
        portfolio_values = portfolio_values.loc[common_dates]
        benchmark_prices = benchmark_prices.loc[common_dates]
        
        # Normalize to starting value of 1.0
        portfolio_norm = portfolio_values / portfolio_values.iloc[0]
        benchmark_norm = benchmark_prices / benchmark_prices.iloc[0]
        
        # Calculate relative performance
        outperformance = portfolio_norm.iloc[-1] / benchmark_norm.iloc[-1] - 1
        
        # Calculate tracking error
        tracking_diff = (portfolio_norm.pct_change().dropna() - benchmark_norm.pct_change().dropna())
        tracking_error = tracking_diff.std() * (252 ** 0.5)  # Annualized
        
        # Calculate information ratio
        information_ratio = outperformance / tracking_error if tracking_error > 0 else 0
        
        # Calculate beta
        portfolio_returns = portfolio_norm.pct_change().dropna()
        benchmark_returns = benchmark_norm.pct_change().dropna()
        covariance = portfolio_returns.cov(benchmark_returns)
        variance = benchmark_returns.var()
        beta = covariance / variance if variance > 0 else 1.0
        
        # Store the comparative metrics
        comparative_metrics = {
            'outperformance': outperformance,
            'tracking_error': tracking_error,
            'information_ratio': information_ratio,
            'beta': beta,
            'portfolio_norm': portfolio_norm,
            'benchmark_norm': benchmark_norm
        }
        
        logger.info(f"Benchmark comparison metrics: {comparative_metrics}")
        return comparative_metrics
    
    def save_results(self, output_dir: str = 'data/backtesting') -> bool:
        """Save backtest results to CSV files.
        
        Args:
            output_dir: Directory to save results
            
        Returns:
            Whether the results were successfully saved
        """
        if self.results is None or self.results.empty:
            logger.error("No backtest results available to save")
            return False
            
        logger.info(f"Saving backtest results to {output_dir}")
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Save the main results
            results_path = os.path.join(output_dir, 'backtest_results.csv')
            self.results.to_csv(results_path)
            logger.info(f"Saved backtest results to {results_path}")
            
            # Save performance metrics
            metrics = self.calculate_metrics()
            metrics_df = pd.DataFrame([metrics])
            metrics_path = os.path.join(output_dir, 'performance_metrics.csv')
            metrics_df.to_csv(metrics_path, index=False)
            logger.info(f"Saved performance metrics to {metrics_path}")
            
            # Save comparative metrics if benchmark data is available
            if self.benchmark_data is not None and not self.benchmark_data.empty:
                comparative = self.compare_to_benchmark()
                
                # Only save the numeric metrics, not the time series
                comparative_numerics = {k: v for k, v in comparative.items() 
                                       if not isinstance(v, pd.Series) and not isinstance(v, pd.DataFrame)}
                
                comparative_df = pd.DataFrame([comparative_numerics])
                comparative_path = os.path.join(output_dir, 'benchmark_comparison.csv')
                comparative_df.to_csv(comparative_path, index=False)
                logger.info(f"Saved benchmark comparison to {comparative_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            return False
        
    def visualize_performance(self, output_dir: str = 'data/backtesting') -> bool:
        """Visualize the backtest performance.
        
        Args:
            output_dir: Directory to save visualizations
            
        Returns:
            Whether the visualizations were successfully created
        """
        if self.results is None or self.results.empty:
            logger.error("No backtest results available for visualization")
            return False
            
        logger.info("Creating performance visualizations")
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Create a plotter
            plotter = BacktestPlotter(
                results=self.results,
                benchmark_data=self.benchmark_data,
                start_date=self.start_date,
                end_date=self.end_date
            )
            
            # Generate plots
            success = plotter.plot_portfolio_performance(
                output_path=os.path.join(output_dir, 'performance.png')
            )
            
            if not success:
                logger.error("Failed to create performance visualization")
                return False
                
            logger.info("Successfully created performance visualization")
            return True
            
        except Exception as e:
            logger.error(f"Error creating visualizations: {e}")
            return False 