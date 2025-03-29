"""
Performance metrics calculation for backtest results.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any


def calculate_performance_metrics(results: pd.DataFrame, benchmark_data: pd.DataFrame = None) -> Dict[str, Any]:
    """
    Calculate performance metrics from backtest results.
    
    Args:
        results: DataFrame with portfolio values over time
        benchmark_data: Optional benchmark data for comparison
        
    Returns:
        Dictionary of performance metrics
    """
    if results is None or results.empty:
        raise ValueError("Results data is empty")
    
    # Extract portfolio values
    portfolio_values = results['portfolio_value']
    initial_value = portfolio_values.iloc[0]
    final_value = portfolio_values.iloc[-1]
    
    # Calculate daily returns
    daily_returns = portfolio_values.pct_change().dropna()
    
    # Calculate benchmark returns if available
    benchmark_returns = None
    if benchmark_data is not None and not benchmark_data.empty:
        if isinstance(benchmark_data, pd.Series):
            benchmark_values = benchmark_data
        else:
            # Assume 'Close' column if DataFrame
            benchmark_values = benchmark_data['Close'] if 'Close' in benchmark_data.columns else benchmark_data.iloc[:, 0]
        
        # Align benchmark with portfolio dates
        benchmark_values = benchmark_values.reindex(portfolio_values.index, method='ffill')
        benchmark_returns = benchmark_values.pct_change().dropna()
    
    # Calculate metrics
    total_return = final_value / initial_value - 1
    
    # Annualized return (assuming 252 trading days in a year)
    n_days = len(results)
    n_years = n_days / 252
    annualized_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
    
    # Volatility (annualized standard deviation of returns)
    volatility = daily_returns.std() * np.sqrt(252)
    
    # Sharpe ratio (assuming risk-free rate of 0 for simplicity)
    sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
    
    # Maximum drawdown
    cumulative_returns = (1 + daily_returns).cumprod()
    running_max = cumulative_returns.cummax()
    drawdown = (cumulative_returns / running_max) - 1
    max_drawdown = drawdown.min()
    
    # Beta (if benchmark available)
    beta = None
    alpha = None
    information_ratio = None
    
    if benchmark_returns is not None:
        # Filter to matching dates
        common_dates = daily_returns.index.intersection(benchmark_returns.index)
        if len(common_dates) > 0:
            aligned_returns = daily_returns.loc[common_dates]
            aligned_benchmark = benchmark_returns.loc[common_dates]
            
            # Calculate beta
            covariance = aligned_returns.cov(aligned_benchmark)
            benchmark_variance = aligned_benchmark.var()
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
            
            # Calculate alpha (annualized)
            benchmark_annualized_return = (1 + aligned_benchmark.mean() * n_days) ** (252 / n_days) - 1
            alpha = annualized_return - (beta * benchmark_annualized_return)
            
            # Calculate information ratio
            tracking_error = (aligned_returns - aligned_benchmark).std() * np.sqrt(252)
            information_ratio = (annualized_return - benchmark_annualized_return) / tracking_error if tracking_error > 0 else 0
    
    # Compile results
    metrics = {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'final_value': final_value
    }
    
    # Add benchmark-related metrics if available
    if beta is not None:
        metrics['beta'] = beta
    if alpha is not None:
        metrics['alpha'] = alpha
    if information_ratio is not None:
        metrics['information_ratio'] = information_ratio
    
    return metrics 