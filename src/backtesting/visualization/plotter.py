"""
Plotting utilities for visualizing backtest results.

This module provides a class for generating plots and visualizations
from backtest results, including performance charts, drawdowns,
and comparative benchmarks.
"""

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
import datetime
import pytz
from typing import Dict, List, Tuple, Optional, Union

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
    """Plotter for backtest results visualization."""
    
    def __init__(
        self,
        results: pd.DataFrame,
        benchmark_data: Optional[pd.DataFrame] = None,
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None
    ):
        """Initialize the backtest plotter.
        
        Args:
            results: DataFrame with backtest results
            benchmark_data: Optional DataFrame with benchmark data
            start_date: Start date of the backtest
            end_date: End date of the backtest
        """
        # Convert index to UTC timezone if timezone-aware
        if isinstance(results.index, pd.DatetimeIndex):
            if results.index.tz is not None:
                self.results = results.tz_convert('UTC')
            else:
                self.results = results.tz_localize('UTC')
        else:
            self.results = results
            
        # Convert benchmark data to UTC timezone if timezone-aware
        if benchmark_data is not None and isinstance(benchmark_data.index, pd.DatetimeIndex):
            if benchmark_data.index.tz is not None:
                self.benchmark_data = benchmark_data.tz_convert('UTC')
            else:
                self.benchmark_data = benchmark_data.tz_localize('UTC')
        else:
            self.benchmark_data = benchmark_data
            
        self.start_date = start_date
        self.end_date = end_date
        
        # Ensure output dirs exist
        os.makedirs('data/backtesting', exist_ok=True)
        
        logger.info("Initialized BacktestPlotter")
    
    def plot_portfolio_performance(self, output_path: str = 'data/backtesting/performance.png') -> bool:
        """Plot portfolio performance compared to benchmark.
        
        Args:
            output_path: Path to save the plot
            
        Returns:
            Whether the plot was successfully created
        """
        try:
            if self.results is None or self.results.empty:
                logger.error("No results data available for plotting")
                return False
                
            # Create the figure
            plt.figure(figsize=(12, 8))
            
            # Plot portfolio value
            ax = plt.subplot(2, 1, 1)
            self.results['Portfolio Value'].plot(ax=ax, label='Portfolio Value', color='blue')
            
            # Add cash component if available
            if 'Cash' in self.results.columns:
                self.results['Cash'].plot(ax=ax, label='Cash', color='green', alpha=0.5)
            
            # Format the plot
            plt.title('Portfolio Performance', fontsize=16)
            plt.xlabel('Date')
            plt.ylabel('Value ($)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Format x-axis dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()
            
            # Plot relative performance vs benchmark
            ax2 = plt.subplot(2, 1, 2)
            
            # Normalize portfolio value to start at 100
            norm_portfolio = 100 * self.results['Portfolio Value'] / self.results['Portfolio Value'].iloc[0]
            norm_portfolio.plot(ax=ax2, label='Portfolio', color='blue')
            
            # Add benchmark if available
            if self.benchmark_data is not None and not self.benchmark_data.empty:
                # Ensure both indices are timezone-aware and in UTC
                benchmark_index = self.benchmark_data.index
                results_index = self.results.index
                
                if not isinstance(benchmark_index, pd.DatetimeIndex):
                    benchmark_index = pd.to_datetime(benchmark_index)
                    self.benchmark_data.index = benchmark_index
                
                if not isinstance(results_index, pd.DatetimeIndex):
                    results_index = pd.to_datetime(results_index)
                    self.results.index = results_index
                
                # Convert both to UTC if they have timezones
                if benchmark_index.tz is not None:
                    self.benchmark_data = self.benchmark_data.tz_convert('UTC')
                else:
                    self.benchmark_data = self.benchmark_data.tz_localize('UTC')
                    
                if results_index.tz is not None:
                    self.results = self.results.tz_convert('UTC')
                else:
                    self.results = self.results.tz_localize('UTC')
                
                # Now both indices are in UTC, we can safely align them
                aligned_benchmark = self.benchmark_data.reindex(
                    self.results.index,
                    method='ffill'
                )
                
                if not aligned_benchmark.empty:
                    # Normalize benchmark to start at 100
                    norm_benchmark = 100 * aligned_benchmark['Close'] / aligned_benchmark['Close'].iloc[0]
                    norm_benchmark.plot(ax=ax2, label='Benchmark', color='red')
            
            # Format the plot
            plt.title('Relative Performance (Normalized)', fontsize=16)
            plt.xlabel('Date')
            plt.ylabel('Value (Normalized to 100)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            # Format x-axis dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()
            
            # Tight layout to avoid overlapping
            plt.tight_layout()
            
            # Save the plot
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Portfolio performance plot saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating portfolio performance plot: {e}")
            return False
    
    def plot_drawdown(self, output_path: str = 'data/backtesting/drawdown.png') -> bool:
        """Plot portfolio drawdown over time.
        
        Args:
            output_path: Path to save the plot
            
        Returns:
            Whether the plot was successfully created
        """
        try:
            if self.results is None or self.results.empty:
                logger.error("No results data available for plotting drawdown")
                return False
            
            # Calculate drawdown
            portfolio_value = self.results['Portfolio Value']
            peak = portfolio_value.cummax()
            drawdown = (portfolio_value - peak) / peak * 100  # Convert to percentage
            
            # Create the figure
            plt.figure(figsize=(12, 6))
            
            # Plot drawdown
            drawdown.plot(color='red', alpha=0.7, linewidth=1.5)
            
            # Add horizontal lines at -5%, -10%, -20%
            plt.axhline(y=-5, color='orange', linestyle='--', alpha=0.5)
            plt.axhline(y=-10, color='orange', linestyle='--', alpha=0.5)
            plt.axhline(y=-20, color='red', linestyle='--', alpha=0.5)
            
            # Format the plot
            plt.title('Portfolio Drawdown', fontsize=16)
            plt.xlabel('Date')
            plt.ylabel('Drawdown (%)')
            plt.grid(True, alpha=0.3)
            
            # Y-axis should be inverted for drawdown
            plt.gca().invert_yaxis()
            
            # Format x-axis dates
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.gcf().autofmt_xdate()
            
            # Save the plot
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Drawdown plot saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating drawdown plot: {e}")
            return False
    
    def plot_monthly_returns(self, output_path: str = 'data/backtesting/monthly_returns.png') -> bool:
        """Plot monthly returns as a heatmap.
        
        Args:
            output_path: Path to save the plot
            
        Returns:
            Whether the plot was successfully created
        """
        try:
            if self.results is None or self.results.empty:
                logger.error("No results data available for plotting monthly returns")
                return False
            
            # Calculate daily returns
            portfolio_value = self.results['Portfolio Value']
            daily_returns = portfolio_value.pct_change().fillna(0)
            
            # Ensure the index is a DatetimeIndex
            if not isinstance(daily_returns.index, pd.DatetimeIndex):
                daily_returns.index = pd.to_datetime(daily_returns.index)
            
            # Calculate monthly returns
            monthly_returns = pd.DataFrame()
            monthly_returns['Year'] = daily_returns.index.year
            monthly_returns['Month'] = daily_returns.index.month
            monthly_returns['Return'] = daily_returns.values
            
            # Calculate returns by month/year
            monthly_returns = monthly_returns.groupby(['Year', 'Month']).apply(
                lambda x: (1 + x['Return']).prod() - 1).unstack('Month')
            
            # Create figure
            plt.figure(figsize=(12, 8))
            
            # Plot heatmap
            plt.pcolormesh(monthly_returns.columns, monthly_returns.index, 
                          monthly_returns.values, cmap='RdYlGn', vmin=-0.1, vmax=0.1)
            
            # Add colorbar
            cbar = plt.colorbar()
            cbar.set_label('Monthly Return')
            
            # Format the plot
            plt.title('Monthly Returns', fontsize=16)
            plt.xlabel('Month')
            plt.ylabel('Year')
            
            # Set x ticks to month names
            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            plt.xticks(range(1, 13), month_names)
            
            # Add text annotations with actual values
            for i in range(len(monthly_returns.index)):
                for j in range(len(monthly_returns.columns)):
                    try:
                        value = monthly_returns.iloc[i, j]
                        if not pd.isna(value):  # Skip NaN values
                            color = 'white' if abs(value) > 0.05 else 'black'
                            plt.text(j + 0.5, i + 0.5, f'{value:.1%}', 
                                    ha='center', va='center', color=color)
                    except IndexError:
                        pass
            
            # Save the plot
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Monthly returns plot saved to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating monthly returns plot: {e}")
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