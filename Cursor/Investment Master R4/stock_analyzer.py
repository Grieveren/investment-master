import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os

class StockAnalyzer:
    """
    A class to analyze stocks using value investing principles based on 
    "Build Wealth with Common Stocks" methodology.
    """
    
    def __init__(self, ticker):
        """
        Initialize with a stock ticker symbol.
        """
        self.ticker = ticker
        self.stock = yf.Ticker(ticker)
        self.info = self.stock.info
        self.company_name = self.info.get('longName', ticker)
        
    def get_financial_data(self):
        """
        Retrieve key financial data for the company.
        """
        # Get income statement
        self.income_stmt = self.stock.income_stmt
        
        # Get balance sheet
        self.balance_sheet = self.stock.balance_sheet
        
        # Get cash flow statement
        self.cash_flow = self.stock.cashflow
        
        # Get historical price data
        self.hist_data = self.stock.history(period="5y")
        
        return {
            'income_statement': self.income_stmt,
            'balance_sheet': self.balance_sheet,
            'cash_flow': self.cash_flow,
            'historical_data': self.hist_data
        }
    
    def calculate_key_metrics(self):
        """
        Calculate key financial metrics used in value investing.
        """
        metrics = {}
        
        # Current price
        metrics['current_price'] = self.info.get('currentPrice', self.hist_data['Close'][-1] if not self.hist_data.empty else None)
        
        # Price-to-Earnings (P/E) Ratio
        metrics['pe_ratio'] = self.info.get('trailingPE')
        
        # Price-to-Book (P/B) Ratio
        metrics['pb_ratio'] = self.info.get('priceToBook')
        
        # Debt-to-Equity Ratio
        metrics['debt_to_equity'] = self.info.get('debtToEquity')
        
        # Return on Equity (ROE)
        metrics['roe'] = self.info.get('returnOnEquity')
        
        # Return on Assets (ROA)
        metrics['roa'] = self.info.get('returnOnAssets')
        
        # Free Cash Flow
        if not self.cash_flow.empty:
            try:
                metrics['free_cash_flow'] = self.cash_flow.loc['Free Cash Flow'].iloc[0]
            except:
                metrics['free_cash_flow'] = None
                
        # Dividend Yield
        metrics['dividend_yield'] = self.info.get('dividendYield')
        
        # Earnings Growth (5-year)
        metrics['earnings_growth_5yr'] = self.info.get('fiveYearAvgDividendYield')
        
        # Current Ratio
        if not self.balance_sheet.empty:
            try:
                current_assets = self.balance_sheet.loc['Total Current Assets'].iloc[0]
                current_liabilities = self.balance_sheet.loc['Total Current Liabilities'].iloc[0]
                metrics['current_ratio'] = current_assets / current_liabilities
            except:
                metrics['current_ratio'] = None
        
        # Profit Margin
        metrics['profit_margin'] = self.info.get('profitMargins')
        
        # Earnings Per Share (EPS)
        metrics['eps'] = self.info.get('trailingEps')
        
        # Book Value Per Share
        metrics['book_value_per_share'] = self.info.get('bookValue')
        
        return metrics
    
    def calculate_dcf(self, growth_rate=0.15, discount_rate=0.1, years=10, terminal_growth=0.03):
        """
        Calculate Discounted Cash Flow (DCF) to estimate intrinsic value.
        
        Parameters:
        - growth_rate: Annual growth rate for cash flows (default: 15%)
        - discount_rate: Required rate of return / WACC (default: 10%)
        - years: Number of years to forecast (default: 10)
        - terminal_growth: Long-term growth rate after forecast period (default: 3%)
        
        Returns:
        - Intrinsic value per share
        """
        try:
            # Get free cash flow
            if not self.cash_flow.empty:
                try:
                    free_cash_flow = self.cash_flow.loc['Free Cash Flow'].iloc[0]
                except:
                    free_cash_flow = self.cash_flow.iloc[-1].iloc[0] * 0.2  # Estimate as 20% of net income if FCF not available
            else:
                raise ValueError("Cash flow data not available")
            
            # Get shares outstanding
            shares_outstanding = self.info.get('sharesOutstanding')
            if not shares_outstanding:
                raise ValueError("Shares outstanding data not available")
            
            # Project future cash flows
            future_cash_flows = []
            for year in range(1, years + 1):
                future_cf = free_cash_flow * (1 + growth_rate) ** year
                future_cash_flows.append(future_cf)
            
            # Calculate present value of future cash flows
            present_values = []
            for i, cf in enumerate(future_cash_flows):
                present_value = cf / (1 + discount_rate) ** (i + 1)
                present_values.append(present_value)
            
            # Calculate terminal value
            terminal_value = future_cash_flows[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
            
            # Discount terminal value to present
            present_terminal_value = terminal_value / (1 + discount_rate) ** years
            
            # Total intrinsic value is sum of all present values
            total_value = sum(present_values) + present_terminal_value
            
            # Intrinsic value per share
            intrinsic_value_per_share = total_value / shares_outstanding
            
            return {
                'intrinsic_value_per_share': intrinsic_value_per_share,
                'total_present_value': sum(present_values),
                'terminal_value': present_terminal_value,
                'upside_potential': (intrinsic_value_per_share / self.info.get('currentPrice', 1) - 1) * 100
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def calculate_graham_number(self):
        """
        Calculate Ben Graham's Number, which is used to determine 
        the maximum price an investor should pay for a stock.
        
        Formula: Graham Number = sqrt(22.5 * EPS * BVPS)
        
        Returns:
        - Graham number value
        """
        try:
            eps = self.info.get('trailingEps')
            bvps = self.info.get('bookValue')
            
            if not eps or not bvps:
                return {'error': 'EPS or BVPS data not available'}
            
            if eps <= 0:
                return {'error': 'EPS must be positive for Graham Number calculation'}
            
            # Traditional Graham Number
            graham_number = np.sqrt(22.5 * eps * bvps)
            
            # Current price
            current_price = self.info.get('currentPrice', self.hist_data['Close'][-1] if not self.hist_data.empty else None)
            
            return {
                'graham_number': graham_number,
                'current_price': current_price,
                'upside_potential': (graham_number / current_price - 1) * 100 if current_price else None
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def calculate_intrinsic_value_buffett(self, growth_rate=None):
        """
        Calculate intrinsic value using Warren Buffett's approach based on book value growth.
        
        Parameters:
        - growth_rate: Override the historical book value growth rate (optional)
        
        Returns:
        - Intrinsic value based on Buffett's approach
        """
        try:
            # Use historical book value growth rate if not provided
            if growth_rate is None:
                # Try to estimate from historical data if available
                growth_rate = self.info.get('fiveYearAverageReturn', 0.1)  # Default to 10% if not available
            
            # Get current book value per share
            book_value = self.info.get('bookValue')
            if not book_value:
                return {'error': 'Book value data not available'}
            
            # Calculate future book value (10 years)
            future_book_value = book_value * (1 + growth_rate) ** 10
            
            # Estimate future EPS based on ROE
            roe = self.info.get('returnOnEquity', 0.15)  # Default to 15% if not available
            future_eps = future_book_value * roe
            
            # Estimate future price with reasonable P/E (use average industry P/E or 15)
            future_pe = self.info.get('forwardPE', 15)  # Default to 15 if not available
            future_price = future_eps * future_pe
            
            # Discount back to present (using 9% required return)
            required_return = 0.09
            intrinsic_value = future_price / (1 + required_return) ** 10
            
            # Current price
            current_price = self.info.get('currentPrice', self.hist_data['Close'][-1] if not self.hist_data.empty else None)
            
            return {
                'intrinsic_value': intrinsic_value,
                'current_price': current_price,
                'future_book_value': future_book_value,
                'future_eps': future_eps,
                'future_price': future_price,
                'upside_potential': (intrinsic_value / current_price - 1) * 100 if current_price else None
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def margin_of_safety(self, intrinsic_value):
        """
        Calculate the margin of safety - the difference between intrinsic value and current price.
        
        Parameters:
        - intrinsic_value: Calculated intrinsic value per share
        
        Returns:
        - Margin of safety as a percentage
        """
        current_price = self.info.get('currentPrice', self.hist_data['Close'][-1] if not self.hist_data.empty else None)
        
        if not current_price:
            return {'error': 'Current price data not available'}
        
        margin = (intrinsic_value - current_price) / intrinsic_value * 100
        
        return {
            'margin_of_safety_percent': margin,
            'is_undervalued': margin > 0,
            'intrinsic_value': intrinsic_value,
            'current_price': current_price
        }
    
    def plot_historical_pe(self):
        """
        Plot historical P/E ratio to identify if the stock is trading at a discount.
        """
        try:
            # Get historical price data
            hist_data = self.stock.history(period="5y")
            
            # Get historical EPS data if available
            quarterly_financials = self.stock.quarterly_financials
            
            # Calculate historical P/E ratio (simplified)
            pe_ratios = []
            dates = []
            
            # Use the current P/E for demonstration
            current_pe = self.info.get('trailingPE')
            
            if current_pe:
                # Create a simple historical P/E plot based on price movement
                prices = hist_data['Close']
                # Normalize prices around current price and multiply by current P/E
                pe_estimate = prices / prices.iloc[-1] * current_pe
                
                plt.figure(figsize=(12, 6))
                plt.plot(pe_estimate.index, pe_estimate, label=f'{self.ticker} P/E Ratio Estimate')
                plt.axhline(y=current_pe, color='r', linestyle='--', label=f'Current P/E: {current_pe:.2f}')
                plt.title(f'{self.company_name} Historical P/E Ratio Estimate')
                plt.xlabel('Date')
                plt.ylabel('P/E Ratio')
                plt.legend()
                plt.grid(True)
                
                # Save the plot
                plot_dir = 'analysis_outputs'
                os.makedirs(plot_dir, exist_ok=True)
                plt.savefig(f'{plot_dir}/{self.ticker}_historical_pe.png')
                plt.close()
                
                return {
                    'current_pe': current_pe,
                    'plot_saved': f'{plot_dir}/{self.ticker}_historical_pe.png'
                }
            else:
                return {'error': 'P/E ratio data not available'}
            
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_stock(self):
        """
        Comprehensive stock analysis based on value investing principles.
        """
        analysis = {
            'ticker': self.ticker,
            'company_name': self.company_name,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        }
        
        # Calculate key metrics
        analysis['metrics'] = self.calculate_key_metrics()
        
        # DCF Valuation
        analysis['dcf_valuation'] = self.calculate_dcf()
        
        # Graham Number
        analysis['graham_valuation'] = self.calculate_graham_number()
        
        # Buffett's Approach
        analysis['buffett_valuation'] = self.calculate_intrinsic_value_buffett()
        
        # Margin of Safety (using DCF valuation)
        if 'error' not in analysis['dcf_valuation']:
            analysis['margin_of_safety'] = self.margin_of_safety(analysis['dcf_valuation']['intrinsic_value_per_share'])
        
        # Historical P/E Analysis
        analysis['historical_pe'] = self.plot_historical_pe()
        
        # Summary and recommendation
        analysis['summary'] = self._generate_summary(analysis)
        
        return analysis
    
    def _generate_summary(self, analysis):
        """
        Generate a summary and recommendation based on the analysis.
        """
        summary = {}
        
        # Determine if the stock is undervalued by different methods
        methods_undervalued = 0
        total_methods = 0
        
        # Check DCF
        if 'error' not in analysis['dcf_valuation']:
            total_methods += 1
            if analysis['dcf_valuation']['upside_potential'] > 0:
                methods_undervalued += 1
                summary['dcf_assessment'] = f"Undervalued by {analysis['dcf_valuation']['upside_potential']:.2f}% according to DCF"
            else:
                summary['dcf_assessment'] = f"Overvalued by {-analysis['dcf_valuation']['upside_potential']:.2f}% according to DCF"
        
        # Check Graham Number
        if 'error' not in analysis['graham_valuation']:
            total_methods += 1
            if analysis['graham_valuation']['upside_potential'] > 0:
                methods_undervalued += 1
                summary['graham_assessment'] = f"Undervalued by {analysis['graham_valuation']['upside_potential']:.2f}% according to Graham Number"
            else:
                summary['graham_assessment'] = f"Overvalued by {-analysis['graham_valuation']['upside_potential']:.2f}% according to Graham Number"
        
        # Check Buffett's approach
        if 'error' not in analysis['buffett_valuation']:
            total_methods += 1
            if analysis['buffett_valuation']['upside_potential'] > 0:
                methods_undervalued += 1
                summary['buffett_assessment'] = f"Undervalued by {analysis['buffett_valuation']['upside_potential']:.2f}% according to Buffett's approach"
            else:
                summary['buffett_assessment'] = f"Overvalued by {-analysis['buffett_valuation']['upside_potential']:.2f}% according to Buffett's approach"
        
        # Overall recommendation
        if total_methods > 0:
            confidence_level = methods_undervalued / total_methods
            
            if confidence_level >= 0.67:
                summary['recommendation'] = "STRONG BUY - The stock appears undervalued by multiple valuation methods"
            elif confidence_level >= 0.5:
                summary['recommendation'] = "BUY - The stock appears moderately undervalued"
            elif confidence_level >= 0.33:
                summary['recommendation'] = "HOLD - The stock appears fairly valued"
            else:
                summary['recommendation'] = "AVOID - The stock appears overvalued by multiple valuation methods"
        else:
            summary['recommendation'] = "INSUFFICIENT DATA - Unable to make a confident assessment"
        
        # Check key value investing criteria
        concerns = []
        strengths = []
        
        # Check debt levels
        debt_to_equity = analysis['metrics'].get('debt_to_equity')
        if debt_to_equity and debt_to_equity > 2:
            concerns.append(f"High debt-to-equity ratio of {debt_to_equity:.2f}")
        elif debt_to_equity and debt_to_equity < 0.5:
            strengths.append(f"Low debt-to-equity ratio of {debt_to_equity:.2f}")
        
        # Check profitability
        roe = analysis['metrics'].get('roe')
        if roe and roe < 0.1:
            concerns.append(f"Low return on equity of {roe*100:.2f}%")
        elif roe and roe > 0.2:
            strengths.append(f"Strong return on equity of {roe*100:.2f}%")
        
        # Check P/E ratio
        pe_ratio = analysis['metrics'].get('pe_ratio')
        if pe_ratio and pe_ratio > 25:
            concerns.append(f"High P/E ratio of {pe_ratio:.2f}")
        elif pe_ratio and pe_ratio < 15:
            strengths.append(f"Attractive P/E ratio of {pe_ratio:.2f}")
        
        # Check P/B ratio
        pb_ratio = analysis['metrics'].get('pb_ratio')
        if pb_ratio and pb_ratio > 3:
            concerns.append(f"High P/B ratio of {pb_ratio:.2f}")
        elif pb_ratio and pb_ratio < 1.5:
            strengths.append(f"Attractive P/B ratio of {pb_ratio:.2f}")
        
        summary['concerns'] = concerns
        summary['strengths'] = strengths
        
        return summary


def analyze_multiple_stocks(tickers):
    """
    Analyze multiple stocks and return a sorted list based on investment potential.
    
    Parameters:
    - tickers: List of stock ticker symbols
    
    Returns:
    - DataFrame with analysis results sorted by investment potential
    """
    results = []
    
    for ticker in tickers:
        try:
            analyzer = StockAnalyzer(ticker)
            analysis = analyzer.analyze_stock()
            
            # Extract key metrics for comparison
            result = {
                'ticker': ticker,
                'company_name': analysis['company_name'],
                'current_price': analysis['metrics'].get('current_price'),
                'pe_ratio': analysis['metrics'].get('pe_ratio'),
                'pb_ratio': analysis['metrics'].get('pb_ratio'),
                'roe': analysis['metrics'].get('roe'),
                'dcf_intrinsic_value': analysis['dcf_valuation'].get('intrinsic_value_per_share'),
                'dcf_upside': analysis['dcf_valuation'].get('upside_potential'),
                'graham_number': analysis['graham_valuation'].get('graham_number'),
                'graham_upside': analysis['graham_valuation'].get('upside_potential'),
                'buffett_intrinsic_value': analysis['buffett_valuation'].get('intrinsic_value'),
                'buffett_upside': analysis['buffett_valuation'].get('upside_potential'),
                'recommendation': analysis['summary'].get('recommendation')
            }
            
            results.append(result)
            
        except Exception as e:
            print(f"Error analyzing {ticker}: {str(e)}")
    
    # Convert to DataFrame
    if results:
        df = pd.DataFrame(results)
        
        # Calculate an overall score based on the three valuation methods
        df['avg_upside'] = df[['dcf_upside', 'graham_upside', 'buffett_upside']].mean(axis=1, skipna=True)
        
        # Sort by average upside potential
        df = df.sort_values('avg_upside', ascending=False)
        
        return df
    
    return pd.DataFrame()


def analyze_portfolio(portfolio_csv):
    """
    Analyze a portfolio of stocks from a CSV file.
    Expected format: ticker,shares
    
    Parameters:
    - portfolio_csv: Path to CSV file with portfolio holdings
    
    Returns:
    - DataFrame with portfolio analysis
    """
    try:
        # Read portfolio
        portfolio = pd.read_csv(portfolio_csv)
        
        # Ensure required columns exist
        if 'ticker' not in portfolio.columns or 'shares' not in portfolio.columns:
            raise ValueError("CSV file must contain 'ticker' and 'shares' columns")
        
        results = []
        total_value = 0
        
        for _, row in portfolio.iterrows():
            ticker = row['ticker']
            shares = row['shares']
            
            try:
                analyzer = StockAnalyzer(ticker)
                analysis = analyzer.analyze_stock()
                
                current_price = analysis['metrics'].get('current_price')
                position_value = current_price * shares if current_price else 0
                total_value += position_value
                
                result = {
                    'ticker': ticker,
                    'company_name': analysis['company_name'],
                    'shares': shares,
                    'current_price': current_price,
                    'position_value': position_value,
                    'dcf_intrinsic_value': analysis['dcf_valuation'].get('intrinsic_value_per_share'),
                    'dcf_upside': analysis['dcf_valuation'].get('upside_potential'),
                    'graham_number': analysis['graham_valuation'].get('graham_number'),
                    'graham_upside': analysis['graham_valuation'].get('upside_potential'),
                    'buffett_intrinsic_value': analysis['buffett_valuation'].get('intrinsic_value'),
                    'buffett_upside': analysis['buffett_valuation'].get('upside_potential'),
                    'recommendation': analysis['summary'].get('recommendation')
                }
                
                results.append(result)
                
            except Exception as e:
                print(f"Error analyzing {ticker}: {str(e)}")
        
        # Convert to DataFrame
        if results:
            df = pd.DataFrame(results)
            
            # Calculate portfolio weights
            df['weight'] = df['position_value'] / total_value
            
            # Calculate an overall score based on the three valuation methods
            df['avg_upside'] = df[['dcf_upside', 'graham_upside', 'buffett_upside']].mean(axis=1, skipna=True)
            
            # Calculate weighted average upside for the portfolio
            portfolio_upside = (df['avg_upside'] * df['weight']).sum()
            
            # Sort by position value
            df = df.sort_values('position_value', ascending=False)
            
            return df, portfolio_upside, total_value
        
        return pd.DataFrame(), 0, 0
        
    except Exception as e:
        print(f"Error analyzing portfolio: {str(e)}")
        return pd.DataFrame(), 0, 0


if __name__ == "__main__":
    # Example usage
    ticker = "AAPL"
    analyzer = StockAnalyzer(ticker)
    analysis = analyzer.analyze_stock()
    
    print(f"Analysis for {analysis['company_name']} ({ticker}):")
    print(f"Current Price: ${analysis['metrics'].get('current_price', 'N/A')}")
    print(f"DCF Intrinsic Value: ${analysis['dcf_valuation'].get('intrinsic_value_per_share', 'N/A')}")
    print(f"Graham Number: ${analysis['graham_valuation'].get('graham_number', 'N/A')}")
    print(f"Buffett Intrinsic Value: ${analysis['buffett_valuation'].get('intrinsic_value', 'N/A')}")
    print(f"Recommendation: {analysis['summary'].get('recommendation', 'N/A')}") 