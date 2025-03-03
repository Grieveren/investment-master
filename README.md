# Investment Master - Portfolio Analyzer

A Python tool for analyzing stock portfolios using financial data from SimplyWall.st and AI-powered analysis by either OpenAI's o3-mini model or Claude 3.7.

## Features

- **Portfolio Data Parsing**: Automatically parses your portfolio data from a Markdown file
- **Financial Data Retrieval**: Fetches comprehensive financial statements from SimplyWall.st
- **Deep Financial Analysis**: Processes all 166 financial statements per company
- **AI-Powered Recommendations**: Choose between OpenAI's o3-mini model or Claude 3.7 for analysis
- **In-depth Reporting**: Provides buy/sell/hold recommendations with detailed rationales
- **Robust Error Handling**: Includes retry logic for API calls with exponential backoff
- **Modular Design**: Well-organized codebase with separate modules for different functions

## Requirements

- Python 3.6+
- SimplyWall.st API token
- OpenAI API key

## Installation

1. Clone this repository
2. Install required packages:
   ```
   pip install requests python-dotenv openai
   ```
3. Create a `.env` file with your API keys:
   ```
   SWS_API_TOKEN=your_simplywall_st_token
   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

1. Format your portfolio data in `combined_portfolio.md` with the following format:
   ```
   | # | Security | Shares | Price | Market Value | Weight % |
   |---|----------|--------|-------|--------------|----------|
   | 1 | Stock A  | 100    | 50.0  | 5,000        | 10.0%    |
   ```

2. Run the analyzer with your preferred AI model:
   ```
   # Default (o3-mini)
   python portfolio_analyzer.py
   
   # Specify model explicitly
   python portfolio_analyzer.py --model o3-mini
   python portfolio_analyzer.py --model claude-3-7
   
   # Data fetch only (no analysis)
   python portfolio_analyzer.py --data-only
   ```

3. Review the analysis results in `data/processed/portfolio_analysis.md`

## Project Structure

```
.
├── config.json                 # Configuration settings
├── portfolio_analyzer.py       # Main script
├── combined_portfolio.md       # Your portfolio data
├── data/                       # Data directory
│   ├── raw/                    # Raw API data
│   └── processed/              # Processed analysis results
├── logs/                       # Log files
└── utils/                      # Utility modules
    ├── api.py                  # API interaction functions
    ├── analysis.py             # Analysis functions
    ├── config.py               # Configuration loader
    ├── file_operations.py      # File handling functions
    ├── logger.py               # Logging setup
    └── portfolio.py            # Portfolio parsing functions
```

## How It Works

1. The script parses your portfolio data from the markdown file
2. It fetches detailed financial data for each stock from SimplyWall.st
3. All financial statements (166 per company) are processed and sent to the selected AI model
4. The AI analyzes the data using value investing principles (P/E ratio, P/B ratio, debt levels, etc.)
5. A comprehensive analysis is generated with buy/sell/hold signals, rationales, and risk factors

## AI Model Options

You can choose between two AI models for analysis:

- **o3-mini** (default): OpenAI's o3-mini model with high reasoning effort, optimized for financial analysis with a 200K token context window
- **claude-3-7**: Anthropic's Claude 3.7 model with "thinking" reasoning level, providing an alternative analysis approach

Each model has its own strengths and may produce different insights for your portfolio analysis.

## Value Investing Criteria

The analysis considers the following value investing principles:
- Price-to-earnings ratio
- Price-to-book ratio
- Debt levels
- Return on equity
- Competitive advantage
- Current valuation vs. intrinsic value

## Output Example

The analysis provides signals for each stock:
- **BUY**: Undervalued stocks with strong fundamentals
- **HOLD**: Fairly valued stocks or those with mixed signals
- **SELL**: Overvalued stocks or those with concerning fundamentals

Each recommendation includes a detailed rationale, valuation assessment, and risk factors to consider.

## Testing

The project includes unit tests for key functionality:
```
python -m unittest discover tests
```

## License

MIT 