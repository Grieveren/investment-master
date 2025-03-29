"""
Portfolio simulator for backtesting.

This module provides the PortfolioSimulator class that simulates portfolio changes
based on AI recommendations.
"""

import datetime
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
import pytz

from src.backtesting.core.portfolio import Portfolio, Position

logger = logging.getLogger(__name__)

class PortfolioSimulator:
    """Simulator for backtesting portfolio strategies."""
    
    def __init__(
        self,
        portfolio: Portfolio,
        price_data: Dict[str, pd.DataFrame],
        start_date: datetime.date,
        end_date: datetime.date,
        ai_analyzer = None,
        transaction_cost: float = 0.001  # 0.1% transaction cost
    ):
        """Initialize the portfolio simulator.
        
        Args:
            portfolio: Initial portfolio
            price_data: Historical price data for tickers
            start_date: Start date for the simulation
            end_date: End date for the simulation
            ai_analyzer: Optional AI analyzer for generating signals
            transaction_cost: Cost of transactions as a fraction
        """
        self.portfolio = portfolio
        
        # Convert price data to UTC timezone
        self.price_data = {}
        for ticker, df in price_data.items():
            if isinstance(df.index, pd.DatetimeIndex):
                if df.index.tz is not None:
                    self.price_data[ticker] = df.tz_convert('UTC')
                else:
                    self.price_data[ticker] = df.tz_localize('UTC')
            else:
                self.price_data[ticker] = df
        
        # Ensure start_date and end_date are datetime.date objects
        self.start_date = start_date
        if isinstance(start_date, datetime.datetime):
            self.start_date = start_date.date()
            
        self.end_date = end_date
        if isinstance(end_date, datetime.datetime):
            self.end_date = end_date.date()
            
        self.ai_analyzer = ai_analyzer
        self.transaction_cost = transaction_cost
        
        # Initialize portfolio value history
        self.nav_history = pd.DataFrame(
            columns=['Date', 'Portfolio Value', 'Cash', 'Invested'])
        
        # Initialize trade history
        self.trade_history = []
        
        # Convert dates to timezone-aware timestamps
        self.start_ts = pd.Timestamp(start_date).tz_localize('UTC')
        self.end_ts = pd.Timestamp(end_date).tz_localize('UTC')
        
        logger.info(f"Initialized PortfolioSimulator from {start_date} to {end_date}")
    
    def run_simulation(self) -> pd.DataFrame:
        """Run the portfolio simulation.
        
        Returns:
            DataFrame with simulation results
        """
        logger.info("Starting portfolio simulation")
        
        # Get all unique dates from price data
        all_dates = set()
        for data in self.price_data.values():
            all_dates.update(data.index.date)
        
        # Sort dates and filter to simulation period
        sim_dates = sorted(all_dates)
        sim_dates = [d for d in sim_dates if self.start_date <= d <= self.end_date]
        
        # Initialize results DataFrame
        self.nav_history = pd.DataFrame(columns=['date', 'portfolio_value', 'cash', 'positions'])
        
        # Run simulation for each date
        for date in sim_dates:
            # Get current prices
            prices = self._get_prices_at_date(date)
            
            # Apply AI recommendations
            self._apply_recommendations(date, prices)
            
            # Update portfolio value
            portfolio_value = self.portfolio.cash
            for position in self.portfolio.positions:
                if position.ticker in prices:
                    portfolio_value += position.shares * prices[position.ticker]
            
            # Record results
            self.nav_history = pd.concat([self.nav_history, pd.DataFrame([{
                'date': date,
                'portfolio_value': portfolio_value,
                'cash': self.portfolio.cash,
                'positions': str(self.portfolio.positions)
            }])], ignore_index=True)
        
        logger.info(f"Completed simulation with {len(sim_dates)} data points")
        return self.nav_history
    
    def _get_prices_at_date(self, date: datetime.date) -> Dict[str, float]:
        """Get prices for all tickers at a given date.
        
        Args:
            date: The date to get prices for
            
        Returns:
            Dictionary mapping ticker symbols to prices
        """
        prices = {}
        
        # Convert date to timezone-aware timestamp
        ts = pd.Timestamp(date).tz_localize('UTC')
        
        for ticker, df in self.price_data.items():
            # Find the closest date on or before the target date
            idx = df.index.searchsorted(ts)
            if idx > 0:
                # Use the previous date's closing price
                prices[ticker] = df.iloc[idx-1]['Close']
            elif idx == 0 and df.index[0].tz_convert('UTC').date() == date:
                # If the first date matches, use it
                prices[ticker] = df.iloc[0]['Close']
        
        return prices
    
    def _process_date(self, date: datetime.date) -> None:
        """Process a single date in the simulation.
        
        Args:
            date: The date to process
        """
        # Get current prices
        prices = self._get_prices_at_date(date)
        
        if not prices:
            logger.warning(f"No prices available for {date}, skipping")
            return
        
        # If we have an AI analyzer, get recommendations
        if self.ai_analyzer:
            try:
                self._apply_recommendations(date, prices)
            except Exception as e:
                logger.error(f"Error getting recommendation: {e}")
        
        # Calculate portfolio value
        portfolio_value = self.portfolio.calculate_value(prices)
        
        # Update NAV history
        self.nav_history = pd.concat([self.nav_history, pd.DataFrame([{
            'Date': date,
            'Portfolio Value': portfolio_value,
            'Cash': self.portfolio.cash,
            'Invested': portfolio_value - self.portfolio.cash
        }])], ignore_index=True)
    
    def _apply_recommendations(self, date: datetime.date, prices: Dict[str, float]) -> None:
        """Apply AI recommendations to the portfolio.
        
        Args:
            date: Current date
            prices: Current prices
        """
        if not self.ai_analyzer:
            return
            
        # Get current portfolio positions as a dictionary
        portfolio_dict = {position.ticker: position.shares for position in self.portfolio.positions}
        
        try:
            # Get recommendations from AI analyzer
            recommendations = self.ai_analyzer.analyze(
                date=date,
                prices=self.price_data
            )
            
            # Apply recommendations
            if isinstance(recommendations, dict):
                for ticker, (action, allocation) in recommendations.items():
                    if ticker in prices:
                        if action == 'buy':
                            amount = allocation * self.portfolio.cash
                            if amount > 0:
                                self._apply_buy_recommendation(ticker, amount, prices[ticker])
                        elif action == 'sell':
                            if ticker in portfolio_dict:
                                position_value = portfolio_dict[ticker] * prices[ticker]
                                amount = allocation * position_value
                                if amount > 0:
                                    self._apply_sell_recommendation(ticker, amount, prices[ticker])
        except Exception as e:
            logger.error(f"Error getting recommendation: {str(e)}")
    
    def _get_recent_data(self, ticker: str, current_date: datetime.date, lookback_days: int = 90) -> pd.DataFrame:
        """Get recent price data for a ticker.
        
        Args:
            ticker: Ticker symbol
            current_date: Current date
            lookback_days: Number of days to look back
            
        Returns:
            DataFrame with recent price data
        """
        if ticker not in self.price_data:
            return pd.DataFrame()
            
        df = self.price_data[ticker]
        
        # Convert current_date to timestamp for comparison
        current_timestamp = pd.Timestamp(current_date).tz_localize('UTC')
        
        # Filter data up to current date
        mask = df.index <= current_timestamp
        if not mask.any():
            return pd.DataFrame()
            
        recent_data = df.loc[mask].copy()
        
        # If we have less than lookback_days, return all available data
        if len(recent_data) <= lookback_days:
            return recent_data
            
        # Otherwise, return the most recent lookback_days
        return recent_data.iloc[-lookback_days:]
    
    def _apply_buy_recommendation(self, ticker: str, amount: float, price: float) -> None:
        """Apply a buy recommendation to the portfolio.
        
        Args:
            ticker: The ticker symbol
            amount: Amount to invest in dollars
            price: Current price
        """
        if amount <= 0 or price <= 0:
            return
            
        # Calculate number of shares to buy
        shares = int(amount / price)  # Round down to nearest whole share
        
        if shares > 0:
            # Calculate actual cost including transaction cost
            cost = shares * price * (1 + self.transaction_cost)
            
            if cost <= self.portfolio.cash:
                # Add the position
                self.portfolio.update_position(ticker, shares, price)
                
                # Log the trade
                self.trade_history.append({
                    'date': pd.Timestamp.now(),
                    'ticker': ticker,
                    'action': 'buy',
                    'shares': shares,
                    'price': price,
                    'cost': cost
                })
                
                logger.info(f"Bought {shares} shares of {ticker} at ${price:.2f}")
    
    def _apply_sell_recommendation(self, ticker: str, amount: float, price: float) -> None:
        """Apply a sell recommendation to the portfolio.
        
        Args:
            ticker: The ticker symbol
            amount: Amount to sell in dollars
            price: Current price
        """
        if amount <= 0 or price <= 0:
            return
            
        # Get current position
        position = self.portfolio.get_position(ticker)
        if not position:
            return
            
        # Calculate number of shares to sell
        shares_value = position.shares * price
        sell_ratio = min(1.0, amount / shares_value)  # Don't sell more than we have
        shares_to_sell = int(position.shares * sell_ratio)
        
        if shares_to_sell > 0:
            # Calculate actual proceeds after transaction cost
            proceeds = shares_to_sell * price * (1 - self.transaction_cost)
            
            # Update the position
            self.portfolio.update_position(ticker, -shares_to_sell, price)
            
            # Log the trade
            self.trade_history.append({
                'date': pd.Timestamp.now(),
                'ticker': ticker,
                'action': 'sell',
                'shares': shares_to_sell,
                'price': price,
                'proceeds': proceeds
            })
            
            logger.info(f"Sold {shares_to_sell} shares of {ticker} at ${price:.2f}")
    
    def get_trade_history(self) -> pd.DataFrame:
        """Get the trade history as a DataFrame.
        
        Returns:
            DataFrame of trade history
        """
        return pd.DataFrame(self.trade_history)
    
    def get_performance_summary(self) -> Dict[str, float]:
        """Get a summary of portfolio performance.
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.nav_history:
            logger.warning("No NAV history available for performance summary")
            return {}
            
        # Extract NAV values and dates
        nav_df = self.get_nav_history()
        
        # Calculate performance metrics
        initial_nav = nav_df['Portfolio Value'].iloc[0]
        final_nav = nav_df['Portfolio Value'].iloc[-1]
        
        total_return = (final_nav / initial_nav) - 1
        
        # Calculate annualized return
        start_date = nav_df['Date'].iloc[0]
        end_date = nav_df['Date'].iloc[-1]
        years = (end_date - start_date).days / 365.25
        
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = 0
            
        # Calculate maximum drawdown
        nav_df['peak'] = nav_df['Portfolio Value'].cummax()
        nav_df['drawdown'] = (nav_df['Portfolio Value'] - nav_df['peak']) / nav_df['peak']
        max_drawdown = nav_df['drawdown'].min()
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown
        }
    
    def get_nav_history(self) -> pd.DataFrame:
        """Get the NAV history as a DataFrame.
        
        Returns:
            DataFrame of NAV history
        """
        return self.nav_history
    
    def reset(self):
        """Reset the simulator to initial state."""
        self.nav_history = pd.DataFrame(
            columns=['Date', 'Portfolio Value', 'Cash', 'Invested'])
        self.trade_history = []
        
        logger.info("Reset portfolio simulator to initial state")
    
    def apply_recommendation(
        self,
        date: datetime.date,
        recommendation: str,
        ticker: str,
        price: float,
        target_allocation: Optional[float] = None,
        share_count: Optional[int] = None
    ) -> bool:
        """Apply a recommendation to the portfolio.
        
        Args:
            date: The date of the recommendation
            recommendation: The recommendation type ('buy', 'sell', 'hold')
            ticker: The ticker symbol
            price: The current price of the security
            target_allocation: Target allocation as percentage of portfolio (0-1)
            share_count: Specific number of shares to buy/sell
            
        Returns:
            True if the recommendation was applied successfully
        """
        current_value = self._calculate_portfolio_value(date)
        
        if recommendation.lower() == 'buy':
            return self._execute_buy(date, ticker, price, target_allocation, share_count, current_value)
        elif recommendation.lower() == 'sell':
            return self._execute_sell(date, ticker, price, target_allocation, share_count)
        elif recommendation.lower() == 'hold':
            logger.info(f"Holding position in {ticker}")
            return True
        else:
            logger.warning(f"Unknown recommendation type: {recommendation}")
            return False
    
    def _execute_buy(
        self,
        date: datetime.date,
        ticker: str,
        price: float,
        target_allocation: Optional[float] = None,
        share_count: Optional[int] = None,
        current_value: Optional[float] = None
    ) -> bool:
        """Execute a buy order.
        
        Args:
            date: The date of the transaction
            ticker: The ticker symbol
            price: The current price of the security
            target_allocation: Target allocation as percentage of portfolio (0-1)
            share_count: Specific number of shares to buy
            current_value: Current portfolio value (if already calculated)
            
        Returns:
            True if the buy was executed successfully
        """
        if current_value is None:
            current_value = self._calculate_portfolio_value(date)
            
        # Determine shares to buy
        if share_count is not None:
            shares_to_buy = share_count
        elif target_allocation is not None:
            current_shares = self.current_positions.get(ticker, 0)
            current_position_value = current_shares * price
            target_value = current_value * target_allocation
            value_to_buy = target_value - current_position_value
            
            # Can't buy negative amounts
            if value_to_buy <= 0:
                logger.info(f"Target allocation for {ticker} already met or exceeded")
                return True
                
            shares_to_buy = int(value_to_buy / price)  # Round down to nearest whole share
        else:
            logger.error("Neither target_allocation nor share_count provided for buy order")
            return False
            
        # Check if we have enough cash
        cost = shares_to_buy * price
        transaction_fee = cost * self.transaction_cost
        total_cost = cost + transaction_fee
        
        if total_cost > self.cash:
            logger.warning(f"Insufficient cash for complete buy order: {ticker}")
            # Adjust shares to buy based on available cash
            max_shares = int((self.cash / (1 + self.transaction_cost)) / price)
            
            if max_shares <= 0:
                logger.error(f"Cannot buy any shares of {ticker} with available cash")
                return False
                
            shares_to_buy = max_shares
            cost = shares_to_buy * price
            transaction_fee = cost * self.transaction_cost
            total_cost = cost + transaction_fee
            
        # Execute the transaction
        self.cash -= total_cost
        self.current_positions[ticker] = self.current_positions.get(ticker, 0) + shares_to_buy
        
        # Record the transaction
        transaction = {
            'date': date,
            'ticker': ticker,
            'action': 'buy',
            'shares': shares_to_buy,
            'price': price,
            'cost': cost,
            'fee': transaction_fee
        }
        self.transactions.append(transaction)
        
        logger.info(f"Bought {shares_to_buy} shares of {ticker} at {price}")
        return True
    
    def _execute_sell(
        self,
        date: datetime.date,
        ticker: str,
        price: float,
        target_allocation: Optional[float] = None,
        share_count: Optional[int] = None
    ) -> bool:
        """Execute a sell order.
        
        Args:
            date: The date of the transaction
            ticker: The ticker symbol
            price: The current price of the security
            target_allocation: Target allocation as percentage of portfolio (0-1)
            share_count: Specific number of shares to sell
            
        Returns:
            True if the sell was executed successfully
        """
        current_shares = self.current_positions.get(ticker, 0)
        
        if current_shares == 0:
            logger.warning(f"Cannot sell {ticker}: No shares in portfolio")
            return False
            
        # Determine shares to sell
        if share_count is not None:
            shares_to_sell = min(share_count, current_shares)
        elif target_allocation is not None:
            current_value = self._calculate_portfolio_value(date)
            current_position_value = current_shares * price
            target_value = current_value * target_allocation
            
            # If target value is higher than current, no need to sell
            if target_value >= current_position_value:
                logger.info(f"Target allocation for {ticker} already at or below current")
                return True
                
            value_to_sell = current_position_value - target_value
            shares_to_sell = int(value_to_sell / price)  # Round down to nearest whole share
            shares_to_sell = min(shares_to_sell, current_shares)
        else:
            logger.error("Neither target_allocation nor share_count provided for sell order")
            return False
            
        # Execute the transaction
        proceeds = shares_to_sell * price
        transaction_fee = proceeds * self.transaction_cost
        net_proceeds = proceeds - transaction_fee
        
        self.cash += net_proceeds
        self.current_positions[ticker] = current_shares - shares_to_sell
        
        # Clean up if position is now zero
        if self.current_positions[ticker] == 0:
            del self.current_positions[ticker]
            
        # Record the transaction
        transaction = {
            'date': date,
            'ticker': ticker,
            'action': 'sell',
            'shares': shares_to_sell,
            'price': price,
            'proceeds': proceeds,
            'fee': transaction_fee
        }
        self.transactions.append(transaction)
        
        logger.info(f"Sold {shares_to_sell} shares of {ticker} at {price}")
        return True
    
    def _calculate_portfolio_value(self, date: datetime.date, prices: Optional[Dict[str, float]] = None) -> float:
        """Calculate the current portfolio value.
        
        Args:
            date: The date for the calculation
            prices: Optional dictionary of ticker:price pairs
            
        Returns:
            The total portfolio value including cash
        """
        # This is a placeholder - in a real implementation, you would look up
        # actual prices for the given date if not provided
        
        total_value = self.cash
        
        for ticker, shares in self.current_positions.items():
            if prices and ticker in prices:
                price = prices[ticker]
                position_value = shares * price
                total_value += position_value
            else:
                # In a real implementation, you would look up the historical price
                # for this ticker on this date
                logger.warning(f"No price available for {ticker} on {date}")
                # Using the last known price as a fallback
                # In a real implementation, this would be properly handled
                # This is just a placeholder
                position_value = 0
                total_value += position_value
                
        return total_value
    
    def update_nav_history(self, date: datetime.date, prices: Dict[str, float]) -> float:
        """Update the NAV history with current portfolio value.
        
        Args:
            date: The date for the update
            prices: Dictionary of ticker:price pairs
            
        Returns:
            The current portfolio NAV
        """
        nav = self._calculate_portfolio_value(date, prices)
        
        # Record NAV
        nav_record = {
            'Date': date,
            'Portfolio Value': nav,
            'Cash': self.cash,
            'date': date,
            'nav': nav
        }
        self.nav_history.append(nav_record)
        
        logger.debug(f"Updated NAV history for {date}: {nav}")
        return nav
    
    def get_transaction_history(self) -> pd.DataFrame:
        """Get the transaction history as a DataFrame.
        
        Returns:
            DataFrame of all transactions
        """
        return pd.DataFrame(self.transactions)
    
    def get_performance_summary(self) -> Dict[str, float]:
        """Get a summary of portfolio performance.
        
        Returns:
            Dictionary of performance metrics
        """
        if not self.nav_history:
            logger.warning("No NAV history available for performance summary")
            return {}
            
        # Extract NAV values and dates
        nav_df = self.get_nav_history()
        
        # Calculate performance metrics
        initial_nav = nav_df['nav'].iloc[0]
        final_nav = nav_df['nav'].iloc[-1]
        
        total_return = (final_nav / initial_nav) - 1
        
        # Calculate annualized return
        start_date = nav_df['date'].iloc[0]
        end_date = nav_df['date'].iloc[-1]
        years = (end_date - start_date).days / 365.25
        
        if years > 0:
            annualized_return = (1 + total_return) ** (1 / years) - 1
        else:
            annualized_return = 0
            
        # Calculate maximum drawdown
        nav_df['peak'] = nav_df['nav'].cummax()
        nav_df['drawdown'] = (nav_df['nav'] - nav_df['peak']) / nav_df['peak']
        max_drawdown = nav_df['drawdown'].min()
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'max_drawdown': max_drawdown
        } 