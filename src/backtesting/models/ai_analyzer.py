"""
AI analyzer for running analysis on historical data snapshots.

This module provides a class for running AI analysis on historical
financial data snapshots, simulating what recommendations would have
been made at specific points in time.
"""

import datetime
import logging
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, List, Optional, Union, Tuple

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """Runs AI analysis on historical data snapshots."""
    
    def __init__(self, model_name: str = 'claude-3-7', strategy: str = 'momentum', lookback: int = 20):
        """Initialize the AI analyzer.
        
        Args:
            model_name: The AI model to use ('claude-3-7', 'o3-mini')
            strategy: Strategy to use for backtesting ('momentum', 'value', 'mean_reversion', 'trend_following')
            lookback: Number of days to look back for strategy calculations
        """
        self.model_name = model_name
        self.strategy = strategy
        self.lookback = lookback
        self.fundamental_data = {}  # Cache for fundamental data
        logger.info(f"Initialized AIAnalyzer with model {model_name}, strategy: {strategy}, lookback: {lookback} days")
    
    def analyze(self, date: datetime.date, prices: Dict[str, pd.DataFrame]) -> Dict[str, Tuple[str, float]]:
        """
        Analyze prices using the selected strategy and generate buy/sell recommendations.
        
        Args:
            date: The date of analysis
            prices: Dictionary of price dataframes for each ticker
            
        Returns:
            Dictionary of recommendations with ticker as key and (action, allocation) as value
        """
        if self.strategy == 'momentum':
            return self._momentum_strategy(date, prices)
        elif self.strategy == 'value':
            return self._value_strategy(date, prices)
        elif self.strategy == 'mean_reversion':
            return self._mean_reversion_strategy(date, prices)
        elif self.strategy == 'trend_following':
            return self._trend_following_strategy(date, prices)
        else:
            logger.warning(f"Unknown strategy: {self.strategy}, defaulting to 'hold' for all tickers")
            return {ticker: ('hold', 0.0) for ticker in prices.keys()}
    
    def _momentum_strategy(self, date: datetime.date, prices: Dict[str, pd.DataFrame]) -> Dict[str, Tuple[str, float]]:
        """
        Simple momentum strategy based on past returns.
        
        Buy stocks with positive returns over the lookback period, sell those with negative.
        """
        recommendations = {}
        
        # Convert date to pd.Timestamp for comparison
        date_ts = pd.Timestamp(date)
        
        for ticker, data in prices.items():
            # Filter data up to the given date
            data_until_date = data[data.index <= date_ts]
            
            if len(data_until_date) < self.lookback + 1:
                recommendations[ticker] = ('hold', 0.0)
                continue
                
            # Calculate momentum (return over lookback period)
            current_price = data_until_date['Close'].iloc[-1]
            previous_price = data_until_date['Close'].iloc[-self.lookback-1]
            momentum = (current_price / previous_price) - 1
            
            # Decide action based on momentum
            if momentum > 0.05:  # 5% threshold for strong momentum
                action = 'buy'
                allocation = 0.1  # 10% allocation
            elif momentum < -0.05:  # 5% threshold for weak momentum
                action = 'sell'
                allocation = 0.0  # Sell all
            else:
                action = 'hold'
                allocation = 0.05  # 5% allocation
                
            recommendations[ticker] = (action, allocation)
            logger.debug(f"Momentum for {ticker}: {momentum:.2%}, Action: {action}")
            
        return recommendations
    
    def _value_strategy(self, date: datetime.date, prices: Dict[str, pd.DataFrame]) -> Dict[str, Tuple[str, float]]:
        """
        Value investing strategy based on fundamental metrics.
        
        Buy undervalued stocks (high value score) and sell overvalued stocks (low value score).
        """
        recommendations = {}
        value_scores = {}
        
        # Convert date to pd.Timestamp for comparison
        date_ts = pd.Timestamp(date)
        
        # First, load all fundamental data
        for ticker in prices.keys():
            if ticker not in self.fundamental_data:
                self._load_fundamental_data(ticker)
        
        # Calculate value scores for each ticker
        for ticker, data in prices.items():
            # Filter data up to the given date
            data_until_date = data[data.index <= date_ts]
            
            if len(data_until_date) < 5:  # Need at least some price history
                recommendations[ticker] = ('hold', 0.0)
                continue
            
            # Get fundamental data
            fund_data = self.fundamental_data.get(ticker, {})
            if not fund_data:
                recommendations[ticker] = ('hold', 0.0)
                continue
            
            # Calculate value score based on fundamental metrics
            value_score = 0
            
            # 1. PE Ratio: Lower is better for value
            pe_ratio = fund_data.get('trailingPE', 0)
            if pe_ratio > 0:  # Valid PE ratio
                if pe_ratio < 10:
                    value_score += 2  # Very low PE
                elif pe_ratio < 15:
                    value_score += 1  # Low PE
                elif pe_ratio > 30:
                    value_score -= 1  # High PE
            
            # 2. Price to Book: Lower is better for value
            pb_ratio = fund_data.get('priceToBook', 0)
            if pb_ratio > 0:  # Valid P/B ratio
                if pb_ratio < 1:
                    value_score += 2  # Below book value
                elif pb_ratio < 2:
                    value_score += 1  # Low P/B
                elif pb_ratio > 5:
                    value_score -= 1  # High P/B
            
            # 3. Debt to Equity: Lower is better for value
            debt_to_equity = fund_data.get('debtToEquity', 0)
            if debt_to_equity >= 0:  # Valid D/E ratio
                if debt_to_equity < 0.5:
                    value_score += 1  # Low debt
                elif debt_to_equity > 2:
                    value_score -= 1  # High debt
            
            # 4. Profit Margins: Higher is better
            profit_margin = fund_data.get('profitMargins', 0)
            if profit_margin > 0.2:  # 20%+
                value_score += 2  # High profit margins
            elif profit_margin > 0.1:  # 10%+
                value_score += 1  # Good profit margins
            elif profit_margin < 0:
                value_score -= 2  # Negative margins
            
            # 5. Return on Equity: Higher is better
            roe = fund_data.get('returnOnEquity', 0)
            if roe > 0.2:  # 20%+
                value_score += 2  # High ROE
            elif roe > 0.15:  # 15%+
                value_score += 1  # Good ROE
            elif roe < 0:
                value_score -= 1  # Negative ROE
            
            # 6. Dividend Yield: Higher can be better for value
            dividend_yield = fund_data.get('dividendYield', 0)
            if dividend_yield > 0.04:  # 4%+
                value_score += 1  # Good dividend yield
            
            # Store value score
            value_scores[ticker] = value_score
        
        # Sort tickers by value score
        sorted_tickers = sorted(value_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Generate recommendations
        if sorted_tickers:
            # Sell low value score stocks (bottom 30%)
            bottom_threshold = len(sorted_tickers) * 0.7
            for i, (ticker, score) in enumerate(sorted_tickers):
                if i >= bottom_threshold and score < 3:
                    recommendations[ticker] = ('sell', 0.5)  # Sell half of position
            
            # Buy high value score stocks (top 30%)
            for i, (ticker, score) in enumerate(sorted_tickers):
                if i < len(sorted_tickers) * 0.3 and score > 6:  # Only buy stocks with good value scores
                    recommendations[ticker] = ('buy', 0.2)  # Buy with 20% allocation
        
        return recommendations
    
    def _load_fundamental_data(self, ticker: str) -> None:
        """Load fundamental data for a ticker."""
        try:
            logger.info(f"Loading fundamental data for {ticker}")
            stock = yf.Ticker(ticker)
            info = stock.info
            self.fundamental_data[ticker] = info
            logger.info(f"Successfully loaded fundamental data for {ticker}")
        except Exception as e:
            logger.warning(f"Failed to load fundamental data for {ticker}: {e}")
            self.fundamental_data[ticker] = {}
    
    def _mean_reversion_strategy(self, date: datetime.date, prices: Dict[str, pd.DataFrame]) -> Dict[str, Tuple[str, float]]:
        """
        Mean reversion strategy based on recent price movements.
        
        Buy stocks that have fallen significantly below their moving average,
        sell stocks that have risen significantly above their moving average.
        """
        recommendations = {}
        
        for ticker, data in prices.items():
            # Filter data up to the given date
            data_until_date = data[data.index <= pd.Timestamp(date)]
            
            if len(data_until_date) < self.lookback + 10:  # Need enough data for moving average
                recommendations[ticker] = ('hold', 0.0)
                continue
                
            # Calculate moving average
            ma = data_until_date['Close'].rolling(window=self.lookback).mean()
            
            # Calculate how far current price is from moving average
            current_price = data_until_date['Close'].iloc[-1]
            current_ma = ma.iloc[-1]
            
            if pd.isna(current_ma):
                recommendations[ticker] = ('hold', 0.0)
                continue
                
            deviation = (current_price / current_ma) - 1
            
            # Decide action based on deviation from mean
            if deviation < -0.1:  # 10% below MA - likely to revert upward
                action = 'buy'
                # More extreme deviations get higher allocations
                allocation = min(0.15, 0.1 - deviation)  # Cap at 15%
            elif deviation > 0.1:  # 10% above MA - likely to revert downward
                action = 'sell'
                allocation = 0.0  # Sell all
            else:
                action = 'hold'
                allocation = 0.05  # 5% allocation
                
            recommendations[ticker] = (action, allocation)
            logger.debug(f"Mean reversion for {ticker}: deviation = {deviation:.2%}, Action: {action}")
            
        return recommendations
    
    def _trend_following_strategy(self, date: datetime.date, prices: Dict[str, pd.DataFrame]) -> Dict[str, Tuple[str, float]]:
        """
        Trend following strategy based on moving averages.
        
        Buy when price is above moving average (uptrend), sell when below (downtrend).
        """
        recommendations = {}
        
        # Convert date to pd.Timestamp for comparison
        date_ts = pd.Timestamp(date)
        
        for ticker, data in prices.items():
            # Filter data up to the given date
            data_until_date = data[data.index <= date_ts]
            
            if len(data_until_date) < self.lookback + 1:
                recommendations[ticker] = ('hold', 0.0)
                continue
                
            # Calculate moving averages
            short_ma = data_until_date['Close'].rolling(window=20).mean()
            long_ma = data_until_date['Close'].rolling(window=50).mean()
            
            # Get current values
            current_price = data_until_date['Close'].iloc[-1]
            current_short_ma = short_ma.iloc[-1]
            current_long_ma = long_ma.iloc[-1]
            
            # Calculate trend strength
            trend_strength = (current_price / current_long_ma - 1) * 100  # Percentage from long MA
            
            # Determine action based on moving average crossovers and trend strength
            if current_price > current_short_ma > current_long_ma:
                # Strong uptrend
                if trend_strength > 10:  # More than 10% above long MA
                    action = 'hold'  # Don't chase too far
                    allocation = 0.1
                else:
                    action = 'buy'
                    allocation = 0.2
            elif current_price < current_short_ma < current_long_ma:
                # Strong downtrend
                if trend_strength < -10:  # More than 10% below long MA
                    action = 'hold'  # Don't sell into panic
                    allocation = 0.05
                else:
                    action = 'sell'
                    allocation = 0.0
            else:
                # Mixed signals or sideways trend
                action = 'hold'
                allocation = 0.1
                
            recommendations[ticker] = (action, allocation)
            logger.debug(f"Trend strength for {ticker}: {trend_strength:.2f}%, Action: {action}")
            
        return recommendations

    def analyze_snapshot(
        self,
        date: datetime.date,
        ticker: str,
        price_data: pd.DataFrame,
        fundamental_data: Dict,
        context: Optional[Dict] = None
    ) -> Dict:
        """Analyze a historical data snapshot for a single stock.
        
        This simulates what the AI would have recommended at a specific
        point in time based on the data available then.
        
        Args:
            date: The date of the snapshot
            ticker: The ticker symbol
            price_data: Historical price data up to the snapshot date
            fundamental_data: Fundamental data available at the snapshot date
            context: Additional context information
            
        Returns:
            Dictionary with analysis results and recommendations
        """
        # This is a placeholder for the actual implementation
        # In a real implementation, you would:
        # 1. Filter the data to include only what was available at the snapshot date
        # 2. Format the data for the AI model
        # 3. Run the actual AI analysis using the same prompts/tools as the main system
        # 4. Parse the results
        
        logger.info(f"Analyzing historical snapshot for {ticker} on {date}")
        
        # Get the company_name from the context or use a fallback
        company_name = context.get('company_name', f"Company {ticker}")
        
        # This could be integrated with your existing Claude or OpenAI analysis
        # For now, just return a placeholder result
        
        # In a real implementation, you would run something like:
        # from src.models.claude.analyzer import ClaudeAnalyzer
        # analyzer = ClaudeAnalyzer()
        # result = analyzer.analyze_stock(ticker, company_name, price_data, fundamental_data)
        
        # Placeholder result
        result = {
            'date': date,
            'ticker': ticker,
            'company_name': company_name,
            'recommendation': 'hold',  # Could be 'buy', 'sell', or 'hold'
            'target_allocation': 0.05,  # Example allocation as percentage
            'reasoning': "Placeholder reasoning for historical analysis",
            'valuation': {
                'intrinsic_value': price_data['Close'].iloc[-1] * 1.1,  # Example 10% above current price
                'margin_of_safety': 0.1
            },
            'strengths': ['Placeholder strength 1', 'Placeholder strength 2'],
            'weaknesses': ['Placeholder weakness 1', 'Placeholder weakness 2'],
            'metrics': {
                'pe_ratio': 15.0,
                'price_to_book': 2.5,
                'debt_to_equity': 0.8
            }
        }
        
        logger.info(f"Completed historical analysis for {ticker} on {date} with recommendation: {result['recommendation']}")
        return result
    
    def analyze_portfolio(
        self,
        date: datetime.date,
        portfolio: Dict[str, float],
        stock_analyses: Dict[str, Dict],
        market_context: Optional[Dict] = None
    ) -> Dict:
        """Analyze a portfolio at a historical point in time.
        
        Args:
            date: The date of the analysis
            portfolio: Dictionary mapping ticker symbols to portfolio weights
            stock_analyses: Dictionary mapping ticker symbols to individual stock analyses
            market_context: Additional market context available at the time
            
        Returns:
            Dictionary with portfolio analysis results and recommendations
        """
        # This is a placeholder for the actual implementation
        logger.info(f"Analyzing historical portfolio on {date} with {len(portfolio)} positions")
        
        # In a real implementation, this would integrate with your existing
        # portfolio analysis and optimization logic
        
        # Placeholder result
        result = {
            'date': date,
            'recommendations': {
                ticker: {
                    'action': 'hold',  # Could be 'buy', 'sell', or 'hold'
                    'target_allocation': weight,
                    'reasoning': f"Placeholder reasoning for {ticker}"
                }
                for ticker, weight in portfolio.items()
            },
            'portfolio_assessment': "Placeholder portfolio assessment",
            'diversification': {
                'sector_allocation': {
                    'Technology': 0.25,
                    'Healthcare': 0.20,
                    'Financials': 0.15,
                    'Consumer Discretionary': 0.15,
                    'Industrials': 0.10,
                    'Other': 0.15
                }
            },
            'risk_assessment': {
                'portfolio_beta': 1.05,
                'concentration_risk': 'moderate'
            }
        }
        
        logger.info(f"Completed historical portfolio analysis for {date}")
        return result 