"""
AI Analyzer for generating portfolio recommendations.
"""

import logging
import pandas as pd
import numpy as np
import datetime
import pytz
from typing import Dict, List, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """Analyzer that generates portfolio recommendations based on historical data."""
    
    def __init__(
        self,
        strategy: str = 'momentum',
        lookback_period: int = 20,
        rebalance_threshold: float = 0.05
    ):
        """Initialize the AI analyzer.
        
        Args:
            strategy: The trading strategy to use ('momentum', 'mean_reversion', 'trend_following', 'value')
            lookback_period: Number of days to look back for analysis
            rebalance_threshold: Minimum threshold for portfolio changes to trigger rebalancing
        """
        self.strategy = strategy
        self.lookback_period = lookback_period
        self.rebalance_threshold = rebalance_threshold
        self.last_rebalance_date = None
        self.fundamental_data = {}
        
        logger.info(f"Initialized AIAnalyzer with strategy: {strategy}, lookback: {lookback_period} days")
    
    def analyze(
        self,
        current_date: Union[datetime.date, pd.Timestamp],
        price_data: Dict[str, pd.DataFrame],
        portfolio: Dict[str, Union[float, int]],
        cash: float
    ) -> Dict[str, Dict[str, float]]:
        """Analyze market data and generate portfolio recommendations.
        
        Args:
            current_date: The current date to analyze
            price_data: Dictionary mapping tickers to price DataFrames
            portfolio: Current portfolio positions with tickers as keys and shares as values
            cash: Available cash in the portfolio
            
        Returns:
            Dictionary with buy and sell recommendations
        """
        # Convert current_date to timezone-aware timestamp if needed
        if isinstance(current_date, datetime.date):
            current_date = pd.Timestamp(current_date)
            if current_date.tz is None:
                current_date = current_date.tz_localize('UTC')
        elif isinstance(current_date, pd.Timestamp):
            if current_date.tz is None:
                current_date = current_date.tz_localize('UTC')
            elif current_date.tz != pytz.UTC:
                current_date = current_date.tz_convert('UTC')
        
        # Skip if not enough data
        if not price_data or len(price_data) == 0:
            logger.warning(f"No price data available for analysis on {current_date}")
            return {"buy": {}, "sell": {}}
        
        # Calculate portfolio value
        portfolio_value = cash
        for ticker, shares in portfolio.items():
            if ticker in price_data and not price_data[ticker].empty:
                # Get the most recent price data for this ticker up to current_date
                ticker_data = price_data[ticker]
                ticker_data = ticker_data[ticker_data.index <= current_date]
                
                if not ticker_data.empty:
                    latest_price = ticker_data['Close'].iloc[-1]
                    portfolio_value += shares * latest_price
        
        recommendations = {"buy": {}, "sell": {}}
        
        # Apply strategy
        if self.strategy == 'momentum':
            recommendations = self._momentum_strategy(current_date, price_data, portfolio, cash, portfolio_value)
        elif self.strategy == 'mean_reversion':
            recommendations = self._mean_reversion_strategy(current_date, price_data, portfolio, cash, portfolio_value)
        elif self.strategy == 'trend_following':
            recommendations = self._trend_following_strategy(current_date, price_data, portfolio, cash, portfolio_value)
        elif self.strategy == 'value':
            recommendations = self._value_strategy(current_date, price_data, portfolio, cash, portfolio_value)
        else:
            logger.warning(f"Unknown strategy: {self.strategy}, using momentum instead")
            recommendations = self._momentum_strategy(current_date, price_data, portfolio, cash, portfolio_value)
        
        # Log recommendations
        buy_recs = ', '.join([f"{t}: ${v:.2f}" for t, v in recommendations['buy'].items()])
        sell_recs = ', '.join([f"{t}: ${v:.2f}" for t, v in recommendations['sell'].items()])
        logger.info(f"Date: {current_date} | Buy: {buy_recs or 'None'} | Sell: {sell_recs or 'None'}")
        
        return recommendations
    
    def _momentum_strategy(
        self,
        current_date: pd.Timestamp,
        price_data: Dict[str, pd.DataFrame],
        portfolio: Dict[str, Union[float, int]],
        cash: float,
        portfolio_value: float
    ) -> Dict[str, Dict[str, float]]:
        """Implement momentum strategy.
        
        Args:
            current_date: Current date
            price_data: Dictionary of price DataFrames
            portfolio: Current portfolio positions
            cash: Available cash
            portfolio_value: Total portfolio value
            
        Returns:
            Dictionary with buy and sell recommendations
        """
        # Calculate momentum for each ticker
        momentum_scores = {}
        
        for ticker, data in price_data.items():
            # Get data up to current date
            data = data[data.index <= current_date]
            
            if len(data) >= self.lookback_period:
                # Calculate momentum (percentage change over lookback period)
                recent_price = data['Close'].iloc[-1]
                past_price = data['Close'].iloc[-self.lookback_period]
                momentum = (recent_price - past_price) / past_price
                
                # Optionally weight more recent performance higher
                recent_momentum = (recent_price - data['Close'].iloc[-5]) / data['Close'].iloc[-5]
                momentum_scores[ticker] = momentum * 0.7 + recent_momentum * 0.3
        
        # Sort tickers by momentum
        sorted_tickers = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Generate recommendations
        recommendations = {"buy": {}, "sell": {}}
        
        # Sell low momentum stocks (bottom 30%)
        bottom_threshold = len(sorted_tickers) * 0.7
        for i, (ticker, score) in enumerate(sorted_tickers):
            if i >= bottom_threshold and ticker in portfolio and portfolio[ticker] > 0:
                # Get latest price
                latest_data = price_data[ticker][price_data[ticker].index <= current_date]
                if not latest_data.empty:
                    latest_price = latest_data['Close'].iloc[-1]
                    position_value = portfolio[ticker] * latest_price
                    
                    # Sell if position is significant and momentum is negative
                    if position_value > portfolio_value * 0.05 and score < 0:
                        # Sell half the position
                        recommendations["sell"][ticker] = 0.5 * position_value
        
        # Buy high momentum stocks (top 30%)
        cash_to_invest = cash * 0.8  # Keep some cash reserve
        target_allocation = cash_to_invest / (len(sorted_tickers) * 0.3 or 1)
        
        for i, (ticker, score) in enumerate(sorted_tickers):
            if i < len(sorted_tickers) * 0.3 and score > 0:
                # Calculate current allocation
                ticker_data = price_data[ticker][price_data[ticker].index <= current_date]
                if not ticker_data.empty:
                    latest_price = ticker_data['Close'].iloc[-1]
                    current_allocation = portfolio.get(ticker, 0) * latest_price
                    
                    # Buy if under-allocated
                    if current_allocation < target_allocation:
                        buy_amount = min(cash_to_invest * 0.3, target_allocation - current_allocation)
                        if buy_amount >= 100:  # Minimum buy amount
                            recommendations["buy"][ticker] = buy_amount
                            cash_to_invest -= buy_amount
        
        return recommendations
    
    def _mean_reversion_strategy(
        self,
        current_date: pd.Timestamp,
        price_data: Dict[str, pd.DataFrame],
        portfolio: Dict[str, Union[float, int]],
        cash: float,
        portfolio_value: float
    ) -> Dict[str, Dict[str, float]]:
        """Implement mean reversion strategy.
        
        Args:
            current_date: Current date
            price_data: Dictionary of price DataFrames
            portfolio: Current portfolio positions
            cash: Available cash
            portfolio_value: Total portfolio value
            
        Returns:
            Dictionary with buy and sell recommendations
        """
        reversion_scores = {}
        
        for ticker, data in price_data.items():
            # Get data up to current date
            data = data[data.index <= current_date]
            
            if len(data) >= self.lookback_period:
                # Calculate z-score of current price relative to recent moving average
                ma = data['Close'].rolling(window=self.lookback_period).mean()
                std = data['Close'].rolling(window=self.lookback_period).std()
                
                if not ma.empty and not std.empty and std.iloc[-1] > 0:
                    z_score = (data['Close'].iloc[-1] - ma.iloc[-1]) / std.iloc[-1]
                    reversion_scores[ticker] = -z_score  # Negative because we want to buy low, sell high
        
        # Sort tickers by reversion potential
        sorted_tickers = sorted(reversion_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Generate recommendations
        recommendations = {"buy": {}, "sell": {}}
        
        # Sell overbought stocks (negative reversion scores)
        for ticker, score in sorted_tickers:
            if score < -1.5 and ticker in portfolio and portfolio[ticker] > 0:  # Z-score > 1.5 above mean
                # Get latest price
                latest_data = price_data[ticker][price_data[ticker].index <= current_date]
                if not latest_data.empty:
                    latest_price = latest_data['Close'].iloc[-1]
                    position_value = portfolio[ticker] * latest_price
                    
                    # Sell if position is significant
                    if position_value > portfolio_value * 0.03:
                        # Sell half the position or more depending on how overbought
                        sell_pct = min(0.9, 0.5 + abs(score) * 0.1)  # More extreme z-scores lead to larger sells
                        recommendations["sell"][ticker] = sell_pct * position_value
        
        # Buy oversold stocks (positive reversion scores)
        cash_to_invest = cash * 0.8  # Keep some cash reserve
        
        for ticker, score in sorted_tickers:
            if score > 1.5:  # Z-score > 1.5 below mean
                # Calculate buy amount based on score and available cash
                buy_weight = min(0.3, 0.1 + score * 0.05)  # More oversold = higher allocation
                buy_amount = cash_to_invest * buy_weight
                
                if buy_amount >= 100:  # Minimum buy amount
                    recommendations["buy"][ticker] = buy_amount
                    cash_to_invest -= buy_amount
                    
                    if cash_to_invest <= 0:
                        break
        
        return recommendations
    
    def _trend_following_strategy(
        self,
        current_date: pd.Timestamp,
        price_data: Dict[str, pd.DataFrame],
        portfolio: Dict[str, Union[float, int]],
        cash: float,
        portfolio_value: float
    ) -> Dict[str, Dict[str, float]]:
        """Implement trend following strategy based on moving averages.
        
        Args:
            current_date: Current date
            price_data: Dictionary of price DataFrames
            portfolio: Current portfolio positions
            cash: Available cash
            portfolio_value: Total portfolio value
            
        Returns:
            Dictionary with buy and sell recommendations
        """
        trend_scores = {}
        short_period = 10
        long_period = self.lookback_period  # e.g., 50
        
        for ticker, data in price_data.items():
            # Get data up to current date
            data = data[data.index <= current_date]
            
            if len(data) >= long_period:
                # Calculate short and long moving averages
                short_ma = data['Close'].rolling(window=short_period).mean()
                long_ma = data['Close'].rolling(window=long_period).mean()
                
                if not short_ma.empty and not long_ma.empty:
                    # Calculate trend strength
                    trend_direction = 1 if short_ma.iloc[-1] > long_ma.iloc[-1] else -1
                    trend_strength = abs(short_ma.iloc[-1] - long_ma.iloc[-1]) / long_ma.iloc[-1]
                    
                    # Check if recent cross happened
                    recent_cross = False
                    if len(short_ma) > 5 and len(long_ma) > 5:
                        was_above = short_ma.iloc[-5] > long_ma.iloc[-5]
                        is_above = short_ma.iloc[-1] > long_ma.iloc[-1]
                        if was_above != is_above:
                            recent_cross = True
                    
                    # Stronger score for recent crosses
                    trend_scores[ticker] = trend_direction * trend_strength * (3 if recent_cross else 1)
        
        # Sort tickers by trend score
        sorted_tickers = sorted(trend_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Generate recommendations
        recommendations = {"buy": {}, "sell": {}}
        
        # Sell tickers with negative trends
        for ticker, score in sorted_tickers:
            if score < -0.01 and ticker in portfolio and portfolio[ticker] > 0:
                # Get latest price
                latest_data = price_data[ticker][price_data[ticker].index <= current_date]
                if not latest_data.empty:
                    latest_price = latest_data['Close'].iloc[-1]
                    position_value = portfolio[ticker] * latest_price
                    
                    # Sell based on trend strength
                    sell_pct = min(1.0, 0.5 + abs(score) * 5)  # More negative trend = larger sell
                    recommendations["sell"][ticker] = sell_pct * position_value
        
        # Buy tickers with positive trends
        cash_to_invest = cash * 0.9  # Keep some cash reserve
        
        for ticker, score in sorted_tickers:
            if score > 0.01:
                # Calculate buy amount based on trend strength
                buy_weight = min(0.3, 0.1 + score * 5)  # Stronger trend = higher allocation
                buy_amount = cash_to_invest * buy_weight
                
                if buy_amount >= 100:  # Minimum buy amount
                    recommendations["buy"][ticker] = buy_amount
                    cash_to_invest -= buy_amount
                    
                    if cash_to_invest <= 0:
                        break
        
        return recommendations
    
    def _value_strategy(
        self,
        current_date: pd.Timestamp,
        price_data: Dict[str, pd.DataFrame],
        portfolio: Dict[str, Union[float, int]],
        cash: float,
        portfolio_value: float
    ) -> Dict[str, Dict[str, float]]:
        """Implement value investing strategy based on fundamental metrics.
        
        Args:
            current_date: Current date
            price_data: Dictionary of price DataFrames
            portfolio: Current portfolio positions
            cash: Available cash
            portfolio_value: Total portfolio value
            
        Returns:
            Dictionary with buy and sell recommendations
        """
        # If we don't have fundamental data, try to load it
        if not self.fundamental_data:
            self._load_fundamental_data(list(price_data.keys()))
        
        # Calculate value score for each ticker
        value_scores = {}
        
        for ticker in price_data.keys():
            # Skip if we don't have fundamental data for this ticker
            if ticker not in self.fundamental_data:
                continue
            
            # Get fundamental metrics
            metrics = self.fundamental_data[ticker]
            score = 0
            
            # PE ratio - lower is better
            pe_ratio = metrics.get('trailingPE')
            if pe_ratio and pe_ratio > 0:
                # 0-10 = 2 points, 10-15 = 1.5 points, 15-20 = 1 point, 20-25 = 0.5 points, >25 = 0
                if pe_ratio < 10:
                    score += 2
                elif pe_ratio < 15:
                    score += 1.5
                elif pe_ratio < 20:
                    score += 1
                elif pe_ratio < 25:
                    score += 0.5
            
            # Price to Book - lower is better
            pb_ratio = metrics.get('priceToBook')
            if pb_ratio and pb_ratio > 0:
                # 0-1 = 2 points, 1-2 = 1.5 points, 2-3 = 1 point, 3-4 = 0.5 points, >4 = 0
                if pb_ratio < 1:
                    score += 2
                elif pb_ratio < 2:
                    score += 1.5
                elif pb_ratio < 3:
                    score += 1
                elif pb_ratio < 4:
                    score += 0.5
            
            # Debt to Equity - lower is better
            debt_to_equity = metrics.get('debtToEquity')
            if debt_to_equity is not None:
                # 0-0.3 = 2 points, 0.3-0.6 = 1.5 points, 0.6-1 = 1 point, 1-1.5 = 0.5 points, >1.5 = 0
                if debt_to_equity < 0.3:
                    score += 2
                elif debt_to_equity < 0.6:
                    score += 1.5
                elif debt_to_equity < 1:
                    score += 1
                elif debt_to_equity < 1.5:
                    score += 0.5
            
            # Profit Margins - higher is better
            profit_margins = metrics.get('profitMargins')
            if profit_margins is not None:
                # >0.2 = 2 points, 0.15-0.2 = 1.5 points, 0.1-0.15 = 1 point, 0.05-0.1 = 0.5 points, <0.05 = 0
                if profit_margins > 0.2:
                    score += 2
                elif profit_margins > 0.15:
                    score += 1.5
                elif profit_margins > 0.1:
                    score += 1
                elif profit_margins > 0.05:
                    score += 0.5
            
            # Return on Equity - higher is better
            roe = metrics.get('returnOnEquity')
            if roe is not None:
                # >0.2 = 2 points, 0.15-0.2 = 1.5 points, 0.1-0.15 = 1 point, 0.05-0.1 = 0.5 points, <0.05 = 0
                if roe > 0.2:
                    score += 2
                elif roe > 0.15:
                    score += 1.5
                elif roe > 0.1:
                    score += 1
                elif roe > 0.05:
                    score += 0.5
            
            # Dividend Yield - higher is better (but not too high)
            dividend_yield = metrics.get('dividendYield')
            if dividend_yield is not None:
                # 0.03-0.06 = 2 points, 0.02-0.03 or 0.06-0.08 = 1.5 points, 0.01-0.02 or 0.08-0.1 = 1 point, 0-0.01 or >0.1 = 0.5 points
                if 0.03 < dividend_yield < 0.06:
                    score += 2
                elif 0.02 < dividend_yield < 0.03 or 0.06 < dividend_yield < 0.08:
                    score += 1.5
                elif 0.01 < dividend_yield < 0.02 or 0.08 < dividend_yield < 0.10:
                    score += 1
                else:
                    score += 0.5
            
            # Store the value score
            value_scores[ticker] = score
        
        # Sort tickers by value score
        sorted_tickers = sorted(value_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Generate recommendations
        recommendations = {"buy": {}, "sell": {}}
        
        # Sell low value score stocks (bottom 30%)
        if sorted_tickers:
            bottom_threshold = len(sorted_tickers) * 0.7
            for i, (ticker, score) in enumerate(sorted_tickers):
                if i >= bottom_threshold and ticker in portfolio and portfolio[ticker] > 0:
                    # Get latest price
                    latest_data = price_data[ticker][price_data[ticker].index <= current_date]
                    if not latest_data.empty:
                        latest_price = latest_data['Close'].iloc[-1]
                        position_value = portfolio[ticker] * latest_price
                        
                        # Sell if position is significant and value score is low
                        if position_value > portfolio_value * 0.05 and score < 3:
                            # Sell half the position
                            recommendations["sell"][ticker] = 0.5 * position_value
            
            # Buy high value score stocks (top 30%)
            cash_to_invest = cash * 0.8  # Keep some cash reserve
            target_allocation = cash_to_invest / (len(sorted_tickers) * 0.3 or 1)
            
            for i, (ticker, score) in enumerate(sorted_tickers):
                if i < len(sorted_tickers) * 0.3 and score > 6:  # Only buy stocks with good value scores
                    # Calculate current allocation
                    ticker_data = price_data[ticker][price_data[ticker].index <= current_date]
                    if not ticker_data.empty:
                        latest_price = ticker_data['Close'].iloc[-1]
                        current_allocation = portfolio.get(ticker, 0) * latest_price
                        
                        # Buy if under-allocated
                        if current_allocation < target_allocation:
                            buy_amount = min(cash_to_invest * 0.3, target_allocation - current_allocation)
                            if buy_amount >= 100:  # Minimum buy amount
                                recommendations["buy"][ticker] = buy_amount
                                cash_to_invest -= buy_amount
        
        return recommendations
    
    def _load_fundamental_data(self, tickers: List[str]) -> None:
        """Load fundamental data for a list of tickers.
        
        This uses the YFinance library to get fundamental metrics for each ticker.
        
        Args:
            tickers: List of ticker symbols
        """
        import yfinance as yf
        
        for ticker in tickers:
            try:
                logger.info(f"Loading fundamental data for {ticker}")
                ticker_obj = yf.Ticker(ticker)
                self.fundamental_data[ticker] = ticker_obj.info
            except Exception as e:
                logger.warning(f"Error loading fundamental data for {ticker}: {e}") 