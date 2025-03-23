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

logger = logging.getLogger(__name__)

class PortfolioSimulator:
    """Simulates portfolio changes based on AI recommendations."""
    
    def __init__(
        self,
        initial_capital: float,
        initial_positions: Dict[str, float],
        transaction_cost: float = 0.001
    ):
        """Initialize the portfolio simulator.
        
        Args:
            initial_capital: Initial portfolio value
            initial_positions: Dictionary mapping ticker symbols to share counts
            transaction_cost: Cost of each transaction as a percentage
        """
        self.initial_capital = initial_capital
        self.initial_positions = initial_positions
        self.transaction_cost = transaction_cost
        
        # Portfolio state
        self.current_positions = initial_positions.copy()
        self.cash = 0.0  # Set during reset
        self.transactions = []
        
        # Performance tracking
        self.nav_history = []  # Net Asset Value history
        
        logger.info(f"Initialized PortfolioSimulator with {len(initial_positions)} positions")
    
    def reset(self):
        """Reset the simulator to initial state."""
        self.current_positions = self.initial_positions.copy()
        self.cash = self.initial_capital
        self.transactions = []
        self.nav_history = []
        
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
    
    def get_nav_history(self) -> pd.DataFrame:
        """Get the NAV history as a DataFrame.
        
        Returns:
            DataFrame of NAV history
        """
        return pd.DataFrame(self.nav_history)
    
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