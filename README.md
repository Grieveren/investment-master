# Investment Master - Portfolio Analyzer

A comprehensive tool for analyzing and optimizing investment portfolios using AI-powered financial analysis.

## Features

- Portfolio data parsing from CSV files
- Financial data retrieval from SimplyWall.st API
- AI-powered financial analysis using OpenAI's o3-mini and Anthropic's Claude models
- Advanced portfolio optimization algorithms
- Enhanced analysis with extended thinking capabilities (32,000 tokens)
- Real-time feedback through streaming analysis
- Comprehensive value investing analysis
- Detailed individual stock reports
- Portfolio-level optimization recommendations
- German investor-specific considerations

## Project Structure

```
investment-master/
├── src/                         # All source code
│   ├── core/                    # Core functionality
│   │   ├── config.py            # Configuration management
│   │   ├── file_operations.py   # File handling utilities
│   │   ├── logger.py            # Logging configuration
│   │   ├── portfolio.py         # Portfolio data handling
│   │   └── portfolio_optimizer.py # Rule-based optimization
│   ├── models/                  # Model-specific code
│   │   ├── claude/              # Claude-specific implementations
│   │   ├── openai/              # OpenAI-specific implementations
│   │   └── analysis.py          # General analysis functionality
│   ├── scripts/                 # Standalone scripts
│   │   ├── portfolio_analyzer.py # Main analysis script
│   │   ├── claude_portfolio_optimizer.py # Claude-based optimizer
│   │   ├── analyze_company.py   # Single company analysis script
│   │   ├── analyze_companies.py # All companies analysis script
│   │   └── fetch_portfolio_data.py # Data fetching script
│   └── tools/                   # Utility tools
│       ├── api.py               # API interaction utilities
│       ├── changelog.py         # Changelog utilities
│       ├── examine_api_data.py  # API data inspection tool
│       ├── search_company.py    # Company search tool
│       └── update_changelog.py  # Changelog update script
├── scripts/                     # Shell scripts for modular testing
│   ├── fetch_data_only.sh       # Script to fetch data only
│   ├── run_company_analyses.sh  # Script to run company analyses
│   └── run_portfolio_analysis_only.sh # Script for portfolio analysis
├── tests/                       # All test files
│   └── diagnostic/              # Diagnostic tests
│       ├── run_tsm_test.py      # Test for TSM data fetching
│       └── test_rheinmetall.py  # Test for Rheinmetall data fetching
├── data/                        # Data files
│   ├── processed/               # Processed analysis results
│   ├── raw/                     # Raw API data
│   ├── results/                 # Analysis result files
│   └── source/                  # Source portfolio files
├── docs/                        # Documentation
├── examples/                    # Example use cases
└── logs/                        # Log files
```

## Requirements

- Python 3.7 or higher
- SimplyWall.st API access (free or paid)
- Anthropic API key (for Claude model)
- OpenAI API key (for o3-mini model)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/investment-master.git
   cd investment-master
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -e .          # Installs the package in development mode with all dependencies
   ```

3. Set up your API keys in a `.env` file:
   ```
   SWS_API_TOKEN=your_simplywall_st_api_token
   ANTHROPIC_API_KEY=your_anthropic_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

### Running the complete analysis pipeline:

```bash
./run_portfolio_analysis.sh
```

This script performs:
1. Portfolio analysis with Claude (individual stock analysis)
2. Rule-based portfolio optimization
3. Claude holistic portfolio optimization

### Running only the optimization:

```bash
./run_portfolio_analysis.sh --skip-analysis
```

### Modular Testing Scripts

The project includes modular scripts for testing individual components:

1. **Fetch data only**:
   ```bash
   ./scripts/fetch_data_only.sh
   ```
   Fetches fresh data for all companies in your portfolio without running analysis.

2. **Run company-level analyses**:
   ```bash
   # Analyze all companies
   ./scripts/run_company_analyses.sh

   # Analyze a specific company
   ./scripts/run_company_analyses.sh --company "Microsoft"

   # Specify a different model
   ./scripts/run_company_analyses.sh --model "gpt-4"
   ```
   Runs AI analysis on individual companies using existing API data.

3. **Run portfolio-level analysis only**:
   ```bash
   ./scripts/run_portfolio_analysis_only.sh
   ```
   Performs portfolio-level optimization using previously generated company analyses.

### Running a single stock analysis test:

```bash
python tests/test_single_stock_analysis.py --model claude-3-7 --ticker MSFT --company "Microsoft Corporation"
```

## Output

- Individual company analyses: `data/processed/companies/claude/` or `data/processed/companies/openai/`
- Portfolio analysis summary: `data/processed/portfolio_analysis_claude.md` or `data/processed/portfolio_analysis_openai.md`
- Rule-based optimization: `data/processed/portfolio_optimization.md`
- Claude holistic optimization: `data/processed/claude_portfolio_optimization.md`

## How It Works

The tool follows this process:
1. **Data Collection**: Parses portfolio data from CSV files and retrieves financial data from SimplyWall.st
2. **Individual Analysis**: Analyzes each stock using value investing principles with AI models
3. **Rule-Based Optimization**: Applies predefined rules to suggest portfolio adjustments
4. **Holistic Optimization**: Uses Claude with extended thinking to optimize the entire portfolio

## Portfolio Optimization Approaches

1. **Rule-Based Optimization**
   - Uses predefined rules based on analysis recommendations
   - Calculates target weights based on performance and recommendations
   - Generates buy/sell/hold recommendations for each position

2. **Claude Holistic Optimization**
   - Considers all individual analyses together
   - Analyzes diversification, sector allocation, and risk profile
   - Provides comprehensive portfolio-level recommendations
   - Includes German investor-specific considerations

## AI Models Supported

1. **Anthropic Claude**
   - Model: claude-3-7-sonnet-20250219
   - Enhanced analysis with 32,000 token thinking budget
   - Streaming enabled for real-time feedback
   - Comprehensive analysis capabilities
   - Holistic portfolio optimization

2. **OpenAI o3-mini**
   - Basic analysis capabilities
   - Faster processing
   - Lower cost but less detailed analysis

## Value Investing Criteria

The analysis evaluates stocks based on these value investing principles:
- Financial strength and stability
- Competitive advantages (economic moat)
- Management quality and capital allocation
- Growth prospects and profitability
- Valuation (intrinsic value vs. current price)
- Margin of safety

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT License](LICENSE) 