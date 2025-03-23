"""
Plotting utilities for visualizing backtest results.

This module provides a class for generating plots and visualizations
from backtest results, including performance charts, drawdowns,
and comparative benchmarks.
"""

import logging
import pandas as pd
import datetime
from typing import Dict, List, Optional, Union

# This is a placeholder - you'll need to install matplotlib
# pip install matplotlib
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

logger = logging.getLogger(__name__)

class BacktestPlotter:
    """Generates plots and visualizations from backtest results."""
    
    def __init__(self, output_dir: str = 'data/backtesting/charts'):
        """Initialize the backtest plotter.
        
        Args:
            output_dir: Directory to save plots to
        """
        self.output_dir = output_dir
        
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib package is not installed. Please install with 'pip install matplotlib'")
    
    def plot_portfolio_performance(
        self,
        nav_history: pd.DataFrame,
        benchmark_history: Optional[pd.DataFrame] = None,
        title: str = 'Portfolio Performance',
        filename: str = 'portfolio_performance.png'
    ) -> bool:
        """Plot portfolio performance over time.
        
        Args:
            nav_history: DataFrame with 'date' and 'nav' columns
            benchmark_history: Optional DataFrame with benchmark data
            title: Plot title
            filename: Output filename
            
        Returns:
            True if the plot was generated successfully
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("Cannot generate plot: matplotlib not installed")
            return False
            
        try:
            plt.figure(figsize=(12, 6))
            
            # Plot portfolio NAV
            plt.plot(nav_history['date'], nav_history['nav'], label='Portfolio')
            
            # Plot benchmark if provided
            if benchmark_history is not None and not benchmark_history.empty:
                # Normalize benchmark to same starting value as portfolio
                norm_factor = nav_history['nav'].iloc[0] / benchmark_history['Close'].iloc[0]
                plt.plot(
                    benchmark_history.index, 
                    benchmark_history['Close'] * norm_factor,
                    label='Benchmark',
                    alpha=0.7
                )
            
            plt.title(title)
            plt.xlabel('Date')
            plt.ylabel('Value')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Format x-axis dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.gcf().autofmt_xdate()
            
            # Save the plot
            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/{filename}")
            plt.close()
            
            logger.info(f"Generated portfolio performance plot: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating portfolio performance plot: {e}")
            return False
    
    def plot_drawdown(
        self,
        nav_history: pd.DataFrame,
        title: str = 'Portfolio Drawdown',
        filename: str = 'portfolio_drawdown.png'
    ) -> bool:
        """Plot portfolio drawdown over time.
        
        Args:
            nav_history: DataFrame with 'date' and 'nav' columns
            title: Plot title
            filename: Output filename
            
        Returns:
            True if the plot was generated successfully
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("Cannot generate plot: matplotlib not installed")
            return False
            
        try:
            # Calculate drawdown
            nav_df = nav_history.copy()
            nav_df['peak'] = nav_df['nav'].cummax()
            nav_df['drawdown'] = (nav_df['nav'] - nav_df['peak']) / nav_df['peak'] * 100  # As percentage
            
            plt.figure(figsize=(12, 6))
            
            # Plot drawdown
            plt.fill_between(
                nav_df['date'],
                nav_df['drawdown'],
                0,
                color='red',
                alpha=0.3,
                label='Drawdown'
            )
            plt.plot(nav_df['date'], nav_df['drawdown'], color='red', alpha=0.5)
            
            plt.title(title)
            plt.xlabel('Date')
            plt.ylabel('Drawdown (%)')
            plt.grid(True, alpha=0.3)
            
            # Format x-axis dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.gcf().autofmt_xdate()
            
            # Format y-axis as percentage
            plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f'{x:.1f}%'))
            
            # Save the plot
            plt.tight_layout()
            plt.savefig(f"{self.output_dir}/{filename}")
            plt.close()
            
            logger.info(f"Generated drawdown plot: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating drawdown plot: {e}")
            return False
    
    def plot_transactions(
        self,
        transactions: pd.DataFrame,
        price_data: Dict[str, pd.DataFrame],
        title: str = 'Portfolio Transactions',
        filename: str = 'portfolio_transactions.png'
    ) -> bool:
        """Plot portfolio transactions on price chart.
        
        Args:
            transactions: DataFrame with transaction history
            price_data: Dictionary mapping ticker symbols to price DataFrames
            title: Plot title
            filename: Output filename
            
        Returns:
            True if the plot was generated successfully
        """
        if not MATPLOTLIB_AVAILABLE:
            logger.error("Cannot generate plot: matplotlib not installed")
            return False
            
        if transactions.empty:
            logger.warning("No transactions to plot")
            return False
            
        try:
            # Get unique tickers
            tickers = transactions['ticker'].unique()
            
            # Create a figure with subplots for each ticker
            n_tickers = len(tickers)
            fig, axes = plt.subplots(n_tickers, 1, figsize=(12, 5 * n_tickers), sharex=True)
            
            # Handle case with only one ticker
            if n_tickers == 1:
                axes = [axes]
            
            for i, ticker in enumerate(tickers):
                ax = axes[i]
                
                # Get price data for this ticker
                if ticker not in price_data:
                    logger.warning(f"No price data available for {ticker}")
                    continue
                    
                price_df = price_data[ticker]
                
                # Plot price data
                ax.plot(price_df.index, price_df['Close'], label=f"{ticker} Price", color='blue', alpha=0.7)
                
                # Get transactions for this ticker
                ticker_txns = transactions[transactions['ticker'] == ticker]
                
                # Plot buy transactions
                buys = ticker_txns[ticker_txns['action'] == 'buy']
                if not buys.empty:
                    ax.scatter(
                        buys['date'],
                        buys['price'],
                        marker='^',
                        color='green',
                        s=100,
                        label='Buy',
                        zorder=5
                    )
                
                # Plot sell transactions
                sells = ticker_txns[ticker_txns['action'] == 'sell']
                if not sells.empty:
                    ax.scatter(
                        sells['date'],
                        sells['price'],
                        marker='v',
                        color='red',
                        s=100,
                        label='Sell',
                        zorder=5
                    )
                
                ax.set_title(f"{ticker} Price and Transactions")
                ax.set_ylabel('Price')
                ax.grid(True, alpha=0.3)
                ax.legend()
            
            # Set title and labels for the overall figure
            plt.suptitle(title, fontsize=16)
            plt.xlabel('Date')
            
            # Format x-axis dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
            plt.gcf().autofmt_xdate()
            
            # Save the plot
            plt.tight_layout()
            plt.subplots_adjust(top=0.95)
            plt.savefig(f"{self.output_dir}/{filename}")
            plt.close()
            
            logger.info(f"Generated transactions plot: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating transactions plot: {e}")
            return False 