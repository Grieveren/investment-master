# Investment Master - Portfolio Analyzer

A Python tool for analyzing stock portfolios using financial data from SimplyWall.st and AI-powered analysis by OpenAI's o3-mini model or Anthropic's Claude model with extended thinking. Now includes portfolio optimization based on value investing principles.

## Features

- **Portfolio Data Parsing**: Automatically parses your portfolio data from a Markdown file
- **Financial Data Retrieval**: Fetches comprehensive financial statements from SimplyWall.st
- **Deep Financial Analysis**: Processes all 166 financial statements per company
- **AI-Powered Recommendations**: Uses either OpenAI's o3-mini model (200K token context) or Anthropic's Claude model with extended thinking to generate value investing signals
- **In-depth Reporting**: Provides buy/sell/hold recommendations with detailed rationales
- **Portfolio Optimization**: Analyzes your current holdings and suggests portfolio adjustments based on value investing principles
- **Holistic Portfolio Optimization**: Uses Claude to provide detailed portfolio recommendations with comprehensive rationales
- **Robust Error Handling**: Includes retry logic for API calls with exponential backoff
- **Modular Design**: Well-organized codebase with separate modules for different functions

## Requirements

- Python 3.6+
- SimplyWall.st API token
- OpenAI API key (for OpenAI analysis)
- Anthropic API key (for Claude analysis)

## Installation

1. Clone this repository
2. Install required packages:
   ```
   pip install requests python-dotenv openai anthropic
   ```
3. Create a `.env` file with your API keys:
   ```
   SWS_API_TOKEN=your_simplywall_st_token
   OPENAI_API_KEY=your_openai_api_key
   ANTHROPIC_API_KEY=your_anthropic_api_key
   ```

## Usage

1. Format your portfolio data in `combined_portfolio.md` with the following format:
   ```
   | # | Security | Shares | Price | Market Value | Weight % |
   |---|----------|--------|-------|--------------|----------|
   | 1 | Stock A  | 100    | 50.0  | 5,000        | 10.0%    |
   ```

2. (Optional) Place your portfolio export CSV from your broker in the root directory:
   ```
   Report_Depotübersicht_vom_07.03.2025_Brett.csv
   ```

3. For a complete analysis and optimization, use the provided shell script:
   ```
   ./run_portfolio_analysis.sh
   
   # Skip the initial analysis if you've already run it
   ./run_portfolio_analysis.sh --skip-analysis
   ```

4. Alternatively, run individual components:
   ```
   # Using OpenAI (default)
   python portfolio_analyzer.py
   
   # Using Claude
   python portfolio_analyzer.py --model claude-3-7
   
   # Data fetch only (no analysis)
   python portfolio_analyzer.py --data-only
   
   # Skip portfolio optimization
   python portfolio_analyzer.py --skip-optimization
   
   # Run rule-based portfolio optimization
   python test_portfolio_optimization.py
   
   # Run holistic Claude-powered portfolio optimization
   python claude_portfolio_optimizer.py
   ```

5. Review the results:
   - Analysis: `data/processed/portfolio_analysis_[model].md`
   - Rule-based optimization: `data/processed/portfolio_optimization.md`
   - Claude holistic optimization: `data/processed/claude_portfolio_optimization.md`

## Project Structure

```
.
├── config.json                 # Configuration settings
├── portfolio_analyzer.py       # Main script
├── claude_portfolio_optimizer.py  # Claude holistic portfolio optimizer
├── run_portfolio_analysis.sh   # Combined analysis and optimization script
├── combined_portfolio.md       # Your portfolio data
├── Report_Depotübersicht_vom_07.03.2025_Brett.csv  # Exported portfolio data from broker
├── data/                       # Data directory
│   ├── raw/                    # Raw API data
│   └── processed/              # Processed analysis results
│       ├── portfolio_analysis_[model].md   # Portfolio summary table
│       ├── portfolio_optimization.md  # Rule-based optimization recommendations
│       ├── claude_portfolio_optimization.md  # Claude holistic optimization
│       └── companies/          # Individual company analysis files
│           ├── openai/         # OpenAI analysis files
│           └── claude/         # Claude analysis files
├── logs/                       # Log files
└── utils/                      # Utility modules
    ├── api.py                  # API interaction functions
    ├── analysis.py             # Analysis functions
    ├── config.py               # Configuration loader
    ├── file_operations.py      # File handling functions
    ├── logger.py               # Logging setup
    ├── portfolio.py            # Portfolio parsing functions
    └── portfolio_optimizer.py  # Portfolio optimization functions
```

## How It Works

1. The script parses your portfolio data from the markdown file
2. It fetches detailed financial data for each stock from SimplyWall.st
3. All financial statements (166 per company) are processed and sent to either OpenAI's o3-mini model or Anthropic's Claude model
4. The AI analyzes the data using value investing principles (P/E ratio, P/B ratio, debt levels, etc.)
5. A comprehensive analysis is generated with buy/sell/hold signals, rationales, and risk factors
6. Results are saved in both a summary table (`portfolio_analysis_[model].md`) and detailed individual company files in the `companies/[model]` directory
7. Portfolio optimization can be done in two ways:
   - **Rule-based optimization**: Uses a simple rule-based approach with fixed multipliers (BUY → 1.5x, SELL → 0.5x)
   - **Claude holistic optimization**: Sends all analyses and portfolio data to Claude for holistic recommendations with detailed rationales
8. A changelog entry is automatically added to track the analysis run

## Portfolio Optimization Approaches

### Rule-based Optimization
- Quick optimization using simple rules
- BUY recommendations get a 1.5x multiplier to their current allocation
- SELL recommendations get a 0.5x multiplier to their current allocation
- HOLD recommendations keep their current allocation
- Normalizes all allocations to sum to 100%
- Fast but lacks detailed rationales and doesn't consider overall portfolio context

### Claude Holistic Optimization
- Comprehensive portfolio analysis considering:
  - Concentration risk
  - Sector balance
  - Growth vs. value mix
  - Margin of safety for each position
- Provides specific position recommendations with euro amounts and percentages
- Includes detailed rationales for each recommendation
- Explains the overall optimization strategy
- Takes longer but provides much more detailed insights

## Changelog

The project includes a comprehensive changelog system to help track progress and make it easier to pick up where you left off after coding sessions:

- **Automatic Updates**: Each analysis run automatically adds an entry to the changelog
- **Manual Updates**: You can manually update the changelog using the `update_changelog.py` script:

```
./update_changelog.py --title "Your Change Title" --description "Detailed description" \
                      --files "file1.py" "file2.py" \
                      --tasks "Task 1 completed" "Task 2 completed" \
                      --next "Next step 1" "Next step 2"
```

The changelog maintains a chronological record of all changes, making it easy to see what's been done and what's next.

## AI Models

The analyzer supports two AI models:

### OpenAI o3-mini
- Default model
- 200K token context window
- Fast analysis (15-20 seconds per stock)
- Configured with high reasoning effort

### Anthropic Claude
- Optional model (use `--model claude-3-7`)
- Extended thinking capability (16K tokens of thinking)
- More detailed analysis (30-40 seconds per stock)
- Configured with temperature=1.0 (required for extended thinking)
- Powers the holistic portfolio optimization

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

Each recommendation includes:
1. A summary table with links to detailed analysis
2. Individual company analysis files with complete untruncated information including:
   - Detailed rationale
   - Full valuation assessment 
   - Comprehensive risk factors

The portfolio optimization provides:
1. A summary of your current portfolio allocation
2. Recommended target allocation based on value investing principles
3. Specific buy/sell actions to rebalance your portfolio
4. Rationales for each recommended change

The Claude holistic optimization adds:
1. Overall analysis of portfolio characteristics
2. Specific position recommendations with euro amounts
3. Detailed rationales for each recommendation
4. Explanation of the overall optimization strategy
5. Consideration of portfolio context (concentration, sectors, etc.)

## Testing

The project includes unit tests and debugging tools:

```
# Run unit tests
python -m unittest discover tests

# Test single stock analysis
python test_single_stock_analysis.py --ticker BRK.B

# Test portfolio optimization
python test_portfolio_optimization.py

# Debug price data extraction
python test_price_data.py
python test_price_extraction.py
```

These testing and debugging tools help ensure the system correctly processes financial data and extracts critical information like current stock prices accurately.

## License

MIT 