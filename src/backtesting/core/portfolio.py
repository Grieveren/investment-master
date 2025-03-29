"""
Portfolio and Position classes for backtesting.
"""

import logging
import pandas as pd
import datetime
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)

class Position:
    """Representation of a single position in a portfolio."""
    
    def __init__(
        self,
        ticker: str,
        shares: float,
        entry_price: float,
        entry_date: Union[datetime.date, str]
    ):
        """Initialize a position.
        
        Args:
            ticker: Ticker symbol
            shares: Number of shares held
            entry_price: Price at which the position was entered
            entry_date: Date the position was entered
        """
        self.ticker = ticker
        self.shares = shares
        self.entry_price = entry_price
        
        # Convert string date to datetime.date if needed
        if isinstance(entry_date, str):
            self.entry_date = datetime.datetime.strptime(entry_date, '%Y-%m-%d').date()
        else:
            self.entry_date = entry_date
            
        logger.debug(f"Created position: {ticker}, {shares} shares at {entry_price}")
    
    def current_value(self, current_price: float) -> float:
        """Calculate the current value of the position.
        
        Args:
            current_price: Current price of the asset
            
        Returns:
            Current value of the position
        """
        return self.shares * current_price
    
    def profit_loss(self, current_price: float) -> float:
        """Calculate the profit or loss of the position.
        
        Args:
            current_price: Current price of the asset
            
        Returns:
            Profit or loss amount
        """
        return self.shares * (current_price - self.entry_price)
    
    def profit_loss_percent(self, current_price: float) -> float:
        """Calculate the profit or loss percentage of the position.
        
        Args:
            current_price: Current price of the asset
            
        Returns:
            Profit or loss percentage
        """
        if self.entry_price == 0:
            return 0
        return (current_price / self.entry_price) - 1

class Portfolio:
    """Representation of a portfolio of positions."""
    
    def __init__(self, initial_capital: float = 100000.0):
        """Initialize a portfolio.
        
        Args:
            initial_capital: Initial cash amount
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: List[Position] = []
        self.history: List[Dict] = []
        logger.debug(f"Created portfolio with initial capital of {initial_capital}")
    
    def add_position(self, position: Position) -> None:
        """Add a position to the portfolio.
        
        Args:
            position: Position to add
        """
        # Deduct the cost from cash
        cost = position.shares * position.entry_price
        if cost > self.cash:
            logger.warning(f"Insufficient cash to add position: {position.ticker}")
            # Adjust shares to available cash
            position.shares = self.cash / position.entry_price
            cost = position.shares * position.entry_price
            logger.warning(f"Adjusted to {position.shares} shares")
        
        self.cash -= cost
        self.positions.append(position)
        
        # Add to history
        self.history.append({
            'date': position.entry_date,
            'action': 'buy',
            'ticker': position.ticker,
            'shares': position.shares,
            'price': position.entry_price,
            'cost': cost,
            'cash_remaining': self.cash
        })
        
        logger.debug(f"Added position: {position.ticker}, {position.shares} shares at {position.entry_price}")
    
    def remove_position(self, ticker: str, exit_price: float, exit_date: Union[datetime.date, str]) -> Optional[float]:
        """Remove a position from the portfolio.
        
        Args:
            ticker: Ticker symbol of the position to remove
            exit_price: Price at which to exit the position
            exit_date: Date of the exit
            
        Returns:
            Proceeds from the sale, or None if the position was not found
        """
        # Convert string date to datetime.date if needed
        if isinstance(exit_date, str):
            exit_date = datetime.datetime.strptime(exit_date, '%Y-%m-%d').date()
        
        for i, position in enumerate(self.positions):
            if position.ticker == ticker:
                # Calculate proceeds
                proceeds = position.shares * exit_price
                profit_loss = position.profit_loss(exit_price)
                
                # Add to cash
                self.cash += proceeds
                
                # Remove the position
                removed_position = self.positions.pop(i)
                
                # Add to history
                self.history.append({
                    'date': exit_date,
                    'action': 'sell',
                    'ticker': ticker,
                    'shares': removed_position.shares,
                    'price': exit_price,
                    'proceeds': proceeds,
                    'profit_loss': profit_loss,
                    'cash_remaining': self.cash
                })
                
                logger.debug(f"Removed position: {ticker}, {removed_position.shares} shares at {exit_price}")
                return proceeds
                
        logger.warning(f"Position not found: {ticker}")
        return None
    
    def get_position(self, ticker: str) -> Optional[Position]:
        """Get a position by ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Position object, or None if not found
        """
        for position in self.positions:
            if position.ticker == ticker:
                return position
        return None
    
    def update_position(self, ticker: str, shares_delta: float, price: float, date: Union[datetime.date, str]) -> bool:
        """Update an existing position or create a new one.
        
        Args:
            ticker: Ticker symbol
            shares_delta: Change in shares (positive for buy, negative for sell)
            price: Current price
            date: Date of the update
            
        Returns:
            Whether the update was successful
        """
        # Convert string date to datetime.date if needed
        if isinstance(date, str):
            date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        
        # Check if we're selling more shares than we have
        if shares_delta < 0:
            position = self.get_position(ticker)
            if position is None:
                logger.warning(f"Cannot sell shares of non-existent position: {ticker}")
                return False
            if abs(shares_delta) > position.shares:
                logger.warning(f"Attempting to sell more shares than owned: {ticker}")
                shares_delta = -position.shares  # Adjust to sell all shares
        
        # Check if we have enough cash to buy
        if shares_delta > 0:
            cost = shares_delta * price
            if cost > self.cash:
                logger.warning(f"Insufficient cash to buy {shares_delta} shares of {ticker} at {price}")
                # Adjust shares to available cash
                shares_delta = self.cash / price
                cost = shares_delta * price
                logger.warning(f"Adjusted to {shares_delta} shares")
            self.cash -= cost
        
        # Update existing position or create new one
        position = self.get_position(ticker)
        if position is None:
            # Create new position if buying
            if shares_delta > 0:
                self.add_position(Position(
                    ticker=ticker,
                    shares=shares_delta,
                    entry_price=price,
                    entry_date=date
                ))
                return True
            else:
                logger.warning(f"Cannot sell shares of non-existent position: {ticker}")
                return False
        else:
            # Update existing position
            action = 'buy' if shares_delta > 0 else 'sell'
            amount = abs(shares_delta) * price
            
            if action == 'sell':
                # Add proceeds to cash
                self.cash += amount
                
                # If selling all shares, remove the position
                if position.shares + shares_delta <= 0:
                    self.remove_position(ticker, price, date)
                    return True
            
            # Update shares
            position.shares += shares_delta
            
            # Add to history
            self.history.append({
                'date': date,
                'action': action,
                'ticker': ticker,
                'shares': abs(shares_delta),
                'price': price,
                'amount': amount,
                'cash_remaining': self.cash
            })
            
            logger.debug(f"Updated position: {ticker}, {shares_delta} shares at {price}")
            return True
    
    def calculate_value(self, prices: Dict[str, float]) -> float:
        """Calculate the total value of the portfolio.
        
        Args:
            prices: Dictionary mapping ticker symbols to current prices
            
        Returns:
            Total portfolio value including cash
        """
        total_value = self.cash
        
        for position in self.positions:
            if position.ticker in prices:
                total_value += position.current_value(prices[position.ticker])
        
        return total_value
    
    def calculate_allocation(self, prices: Dict[str, float]) -> Dict[str, float]:
        """Calculate the current allocation of the portfolio.
        
        Args:
            prices: Dictionary mapping ticker symbols to current prices
            
        Returns:
            Dictionary mapping ticker symbols to allocation percentages
        """
        total_value = self.calculate_value(prices)
        if total_value == 0:
            return {}
            
        allocation = {}
        for position in self.positions:
            if position.ticker in prices:
                position_value = position.current_value(prices[position.ticker])
                allocation[position.ticker] = position_value / total_value
        
        # Add cash allocation
        allocation['CASH'] = self.cash / total_value
        
        return allocation
    
    def get_history_dataframe(self) -> pd.DataFrame:
        """Get the portfolio history as a DataFrame.
        
        Returns:
            DataFrame of portfolio history
        """
        return pd.DataFrame(self.history) 