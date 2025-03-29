def calculate_performance_metrics(results: pd.DataFrame) -> Dict[str, float]:
    """Calculate performance metrics from backtest results.
    
    Args:
        results: DataFrame with backtest results
        
    Returns:
        Dictionary of performance metrics
    """
    metrics = {}
    
    # Get portfolio value column name
    portfolio_value_col = 'portfolio_value' if 'portfolio_value' in results.columns else 'Portfolio Value'
    
    # Calculate total return
    initial_value = results[portfolio_value_col].iloc[0]
    final_value = results[portfolio_value_col].iloc[-1]
    metrics['total_return'] = (final_value - initial_value) / initial_value
    
    # Calculate daily returns
    daily_returns = results[portfolio_value_col].pct_change().dropna()
    
    # Calculate annualized return
    days = len(daily_returns)
    metrics['annualized_return'] = (1 + metrics['total_return']) ** (252/days) - 1
    
    # Calculate volatility
    metrics['volatility'] = daily_returns.std() * np.sqrt(252)
    
    # Calculate Sharpe ratio (assuming risk-free rate of 2%)
    risk_free_rate = 0.02
    excess_returns = daily_returns - risk_free_rate/252
    metrics['sharpe_ratio'] = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
    
    # Calculate maximum drawdown
    cummax = results[portfolio_value_col].cummax()
    drawdown = (results[portfolio_value_col] - cummax) / cummax
    metrics['max_drawdown'] = drawdown.min()
    
    return metrics 