# Investment Master: Value Investing Analysis Tool

A Python-based stock analysis tool implementing value investing principles from "Build Wealth with Common Stocks" and other value investing methodologies.

## Features

- **Individual Stock Analysis:** Analyze stocks using multiple valuation methods (DCF, Graham Number, Buffett Approach)
- **Stock Comparison:** Compare and rank multiple stocks by investment potential
- **Portfolio Analysis:** Evaluate your entire portfolio, identify undervalued holdings, and get rebalancing suggestions
- **Stock Screening:** Screen large sets of stocks (including major indices) based on value investing criteria
- **Visualizations:** Generate charts and graphs to visualize analysis results

## Installation

1. Clone this repository or download the source code
2. Install the required dependencies:

```
pip install -r requirements.txt
```

## Usage

The tool provides several main commands for analyzing stocks, comparing multiple stocks, analyzing a portfolio, and screening for investment opportunities.

### Analyzing a Single Stock

To analyze a single stock:

```
python value_investor.py stock TICKER
```

Replace `TICKER` with the stock symbol you want to analyze (e.g., AAPL, MSFT, GOOGL).

To save the analysis report to a file:

```
python value_investor.py stock TICKER --save
```

### Comparing Multiple Stocks

To compare multiple stocks and see which ones offer the best investment potential:

```
python value_investor.py compare TICKER1 TICKER2 TICKER3 ...
```

For example:

```
python value_investor.py compare AAPL MSFT GOOGL META AMZN
```

### Analyzing a Portfolio

To analyze a portfolio of stocks:

1. Create a CSV file with your holdings in the format: `ticker,shares`
2. Run the analysis with:

```
python value_investor.py portfolio portfolio.csv
```

### Stock Screening

The stock screening tool allows you to filter large sets of stocks based on value investing criteria:

```
python stock_screener.py --index sp500 --max-pe 15 --min-roe 15 --max-debt-to-equity 1.5 --visualize
```

This command will screen all S&P 500 stocks for those with P/E ratios under 15, ROE over 15%, and debt-to-equity ratios under 1.5.

Other screening options:
- Screen specific stocks: `--tickers AAPL MSFT GOOGL`
- Screen from a file: `--file my_watchlist.txt`
- Screen different indices: `--index nasdaq100`, `--index dowjones`, or `--index russell2000`

Additional filtering criteria include:
- `--min-market-cap`: Minimum market cap in billions
- `--min-dividend-yield`: Minimum dividend yield in percent
- `--min-current-ratio`: Minimum current ratio
- `--min-profit-margin`: Minimum profit margin in percent
- `--max-pb`: Maximum price-to-book ratio
- `--min-graham-upside`: Minimum upside potential based on Graham Number
- `--min-earnings-growth`: Minimum earnings growth rate in percent

Output options:
- `--limit 10`: Limit the display to the top 10 results
- `--export csv`: Export results to a CSV file
- `--export excel`: Export results to an Excel file
- `--visualize`: Generate charts and visualizations of the results

## Analysis Methodology

The tool applies multiple value investing methodologies to determine a stock's intrinsic value:

1. **Discounted Cash Flow (DCF):** Calculates intrinsic value by projecting future cash flows and discounting them to present value.

2. **Benjamin Graham's Number:** Uses the formula `sqrt(22.5 * EPS * BVPS)` to determine a conservative price ceiling.

3. **Warren Buffett's Approach:** Focuses on book value growth and return on equity to estimate future value.

4. **Margin of Safety:** Measures the difference between intrinsic value and current market price.

## Value Investing Principles

This tool is based on key value investing principles:

- Focus on the intrinsic value of companies rather than market movements
- Seek companies with strong fundamentals and competitive advantages
- Look for stocks trading below their intrinsic value
- Apply a margin of safety to protect against valuation errors
- Make investment decisions based on data and fundamental analysis

## Sample Output

The analysis provides comprehensive data including:

- Key financial metrics (P/E ratio, debt-to-equity, ROE, etc.)
- Intrinsic value calculations using multiple methods
- Margin of safety assessment
- Investment recommendation with confidence level
- Strengths and concerns for each investment
- Visual charts for easier comparison

## Example Scripts

The repository includes example scripts to help you get started:

- `example.py`: Demonstrates how to use the analysis tools programmatically
- `stock_analyzer.py`: Core module for analyzing individual stocks
- `value_investor.py`: Command-line interface for the analysis tools
- `stock_screener.py`: Tool for screening large sets of stocks

## Disclaimer

This tool is provided for educational and research purposes only. Always conduct your own research and consider consulting with a financial advisor before making investment decisions.

Stock analysis is inherently complex, and no predictive model can guarantee investment results. Use this tool as part of a broader investment strategy.

## License

This project is open source and available under the MIT License. 