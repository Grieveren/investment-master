"""
Unit tests for the PortfolioSimulator class.
"""

import unittest
import datetime
import pandas as pd
from src.backtesting.core.simulator import PortfolioSimulator

class TestPortfolioSimulator(unittest.TestCase):
    """Test cases for the PortfolioSimulator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.initial_capital = 100000.0
        self.initial_positions = {
            'AAPL': 100,
            'MSFT': 50,
            'GOOGL': 20
        }
        self.transaction_cost = 0.001  # 0.1%
        
        self.simulator = PortfolioSimulator(
            initial_capital=self.initial_capital,
            initial_positions=self.initial_positions,
            transaction_cost=self.transaction_cost
        )
        
        # Reset before each test
        self.simulator.reset()
        
        # Set up test data
        self.test_date = datetime.date(2023, 1, 1)
        self.prices = {
            'AAPL': 150.0,
            'MSFT': 250.0,
            'GOOGL': 2000.0
        }
    
    def test_initial_state(self):
        """Test that the simulator initializes correctly."""
        self.assertEqual(self.simulator.cash, self.initial_capital)
        self.assertEqual(self.simulator.current_positions, self.initial_positions)
        self.assertEqual(len(self.simulator.transactions), 0)
        self.assertEqual(len(self.simulator.nav_history), 0)
    
    def test_calculate_portfolio_value(self):
        """Test portfolio value calculation."""
        # Calculate the expected value
        expected_value = self.initial_capital
        for ticker, shares in self.initial_positions.items():
            expected_value += shares * self.prices[ticker]
        
        # Calculate the actual value
        actual_value = self.simulator._calculate_portfolio_value(
            self.test_date,
            self.prices
        )
        
        self.assertEqual(actual_value, expected_value)
    
    def test_buy_with_shares(self):
        """Test buying a specific number of shares."""
        ticker = 'AAPL'
        shares_to_buy = 10
        price = self.prices[ticker]
        
        # Initial state
        initial_cash = self.simulator.cash
        initial_shares = self.simulator.current_positions[ticker]
        
        # Execute buy
        result = self.simulator.apply_recommendation(
            date=self.test_date,
            recommendation='buy',
            ticker=ticker,
            price=price,
            share_count=shares_to_buy
        )
        
        # Check result
        self.assertTrue(result)
        
        # Calculate expected values
        cost = shares_to_buy * price
        fee = cost * self.transaction_cost
        total_cost = cost + fee
        
        # Check position and cash
        self.assertEqual(
            self.simulator.current_positions[ticker],
            initial_shares + shares_to_buy
        )
        self.assertAlmostEqual(
            self.simulator.cash,
            initial_cash - total_cost
        )
        
        # Check transaction record
        self.assertEqual(len(self.simulator.transactions), 1)
        transaction = self.simulator.transactions[0]
        self.assertEqual(transaction['ticker'], ticker)
        self.assertEqual(transaction['action'], 'buy')
        self.assertEqual(transaction['shares'], shares_to_buy)
        self.assertEqual(transaction['price'], price)
    
    def test_buy_with_allocation(self):
        """Test buying to reach a target allocation."""
        ticker = 'AAPL'
        target_allocation = 0.5  # 50%
        price = self.prices[ticker]
        
        # Calculate initial portfolio value
        initial_portfolio_value = self.simulator._calculate_portfolio_value(
            self.test_date,
            self.prices
        )
        
        # Current position value
        current_shares = self.simulator.current_positions[ticker]
        current_position_value = current_shares * price
        
        # Target position value
        target_position_value = initial_portfolio_value * target_allocation
        
        # Expected shares to buy (rounded down)
        expected_shares_to_buy = int((target_position_value - current_position_value) / price)
        
        # Execute buy
        result = self.simulator.apply_recommendation(
            date=self.test_date,
            recommendation='buy',
            ticker=ticker,
            price=price,
            target_allocation=target_allocation
        )
        
        # Check result
        self.assertTrue(result)
        
        # Check position
        expected_new_shares = current_shares + expected_shares_to_buy
        self.assertEqual(
            self.simulator.current_positions[ticker],
            expected_new_shares
        )
    
    def test_sell_with_shares(self):
        """Test selling a specific number of shares."""
        ticker = 'MSFT'
        shares_to_sell = 10
        price = self.prices[ticker]
        
        # Initial state
        initial_cash = self.simulator.cash
        initial_shares = self.simulator.current_positions[ticker]
        
        # Execute sell
        result = self.simulator.apply_recommendation(
            date=self.test_date,
            recommendation='sell',
            ticker=ticker,
            price=price,
            share_count=shares_to_sell
        )
        
        # Check result
        self.assertTrue(result)
        
        # Calculate expected values
        proceeds = shares_to_sell * price
        fee = proceeds * self.transaction_cost
        net_proceeds = proceeds - fee
        
        # Check position and cash
        self.assertEqual(
            self.simulator.current_positions[ticker],
            initial_shares - shares_to_sell
        )
        self.assertAlmostEqual(
            self.simulator.cash,
            initial_cash + net_proceeds
        )
        
        # Check transaction record
        self.assertEqual(len(self.simulator.transactions), 1)
        transaction = self.simulator.transactions[0]
        self.assertEqual(transaction['ticker'], ticker)
        self.assertEqual(transaction['action'], 'sell')
        self.assertEqual(transaction['shares'], shares_to_sell)
        self.assertEqual(transaction['price'], price)
    
    def test_sell_all_shares(self):
        """Test selling all shares of a position."""
        ticker = 'GOOGL'
        shares_to_sell = self.simulator.current_positions[ticker]
        price = self.prices[ticker]
        
        # Execute sell
        result = self.simulator.apply_recommendation(
            date=self.test_date,
            recommendation='sell',
            ticker=ticker,
            price=price,
            share_count=shares_to_sell
        )
        
        # Check result
        self.assertTrue(result)
        
        # Position should be removed
        self.assertNotIn(ticker, self.simulator.current_positions)
    
    def test_hold_recommendation(self):
        """Test a hold recommendation."""
        ticker = 'AAPL'
        initial_positions = self.simulator.current_positions.copy()
        initial_cash = self.simulator.cash
        
        # Execute hold
        result = self.simulator.apply_recommendation(
            date=self.test_date,
            recommendation='hold',
            ticker=ticker,
            price=self.prices[ticker]
        )
        
        # Check result
        self.assertTrue(result)
        
        # Positions and cash should not change
        self.assertEqual(self.simulator.current_positions, initial_positions)
        self.assertEqual(self.simulator.cash, initial_cash)
        
        # No transaction should be recorded
        self.assertEqual(len(self.simulator.transactions), 0)
    
    def test_update_nav_history(self):
        """Test updating the NAV history."""
        # Update NAV
        nav = self.simulator.update_nav_history(
            date=self.test_date,
            prices=self.prices
        )
        
        # Calculate expected NAV
        expected_nav = self.simulator._calculate_portfolio_value(
            self.test_date,
            self.prices
        )
        
        # Check NAV value
        self.assertEqual(nav, expected_nav)
        
        # Check NAV history
        self.assertEqual(len(self.simulator.nav_history), 1)
        nav_record = self.simulator.nav_history[0]
        self.assertEqual(nav_record['date'], self.test_date)
        self.assertEqual(nav_record['nav'], expected_nav)
    
    def test_get_transaction_history(self):
        """Test getting transaction history as a DataFrame."""
        # Add some transactions
        self.simulator.apply_recommendation(
            date=self.test_date,
            recommendation='buy',
            ticker='AAPL',
            price=self.prices['AAPL'],
            share_count=10
        )
        
        self.simulator.apply_recommendation(
            date=self.test_date,
            recommendation='sell',
            ticker='MSFT',
            price=self.prices['MSFT'],
            share_count=5
        )
        
        # Get transaction history
        history_df = self.simulator.get_transaction_history()
        
        # Check DataFrame
        self.assertIsInstance(history_df, pd.DataFrame)
        self.assertEqual(len(history_df), 2)
        self.assertIn('date', history_df.columns)
        self.assertIn('ticker', history_df.columns)
        self.assertIn('action', history_df.columns)
        self.assertIn('shares', history_df.columns)
        self.assertIn('price', history_df.columns)
    
    def test_get_performance_summary(self):
        """Test getting performance summary."""
        # Add NAV history
        self.simulator.update_nav_history(
            date=datetime.date(2023, 1, 1),
            prices=self.prices
        )
        
        # Simulate price changes
        new_prices = {
            'AAPL': self.prices['AAPL'] * 1.1,  # 10% increase
            'MSFT': self.prices['MSFT'] * 0.95,  # 5% decrease
            'GOOGL': self.prices['GOOGL'] * 1.2,  # 20% increase
        }
        
        # Update NAV with new prices
        self.simulator.update_nav_history(
            date=datetime.date(2023, 2, 1),
            prices=new_prices
        )
        
        # Get performance summary
        summary = self.simulator.get_performance_summary()
        
        # Check summary
        self.assertIn('total_return', summary)
        self.assertIn('annualized_return', summary)
        self.assertIn('max_drawdown', summary)

if __name__ == '__main__':
    unittest.main() 