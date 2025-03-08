# Investment Master - Portfolio Analyzer

A Python tool for analyzing stock portfolios using financial data from SimplyWall.st and AI-powered analysis by OpenAI's o3-mini model or Anthropic's Claude model with extended thinking.

## Features

- **Portfolio Data Parsing**: Automatically parses your portfolio data from a Markdown file
- **Financial Data Retrieval**: Fetches comprehensive financial statements from SimplyWall.st
- **Deep Financial Analysis**: Processes all 166 financial statements per company
- **AI-Powered Recommendations**: Uses either OpenAI's o3-mini model (200K token context) or Anthropic's Claude model with extended thinking to generate value investing signals
- **In-depth Reporting**: Provides buy/sell/hold recommendations with detailed rationales
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

2. Run the analyzer with your preferred AI model:
   ```
   # Using OpenAI (default)
   python portfolio_analyzer.py
   
   # Using Claude
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
│       ├── portfolio_analysis.md # Portfolio summary table
│       └── companies/          # Individual company analysis files
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
3. All financial statements (166 per company) are processed and sent to either OpenAI's o3-mini model or Anthropic's Claude model
4. The AI analyzes the data using value investing principles (P/E ratio, P/B ratio, debt levels, etc.)
5. A comprehensive analysis is generated with buy/sell/hold signals, rationales, and risk factors
6. Results are saved in both a summary table (`portfolio_analysis_[model].md`) and detailed individual company files in the `companies/[model]` directory
7. A changelog entry is automatically added to track the analysis run

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

## Testing

The project includes unit tests for key functionality:
```
python -m unittest discover tests
```

## License

MIT 