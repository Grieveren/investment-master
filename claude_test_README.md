# Claude Analysis Tester

This utility allows you to test the Claude implementation with extended thinking capabilities without having to run the entire portfolio analysis process on all positions.

## Prerequisites

- Python 3.7+
- Anthropic API key set in your `.env` file (or passed as an argument)
- The project's utility modules (utils folder) accessible in your path

## Features

- Tests Claude 3.7 analysis with extended thinking capabilities
- Supports both pre-defined and custom sample data
- Captures and saves detailed thinking process
- Configurable model selection
- Captures and saves prompts and responses

## Usage

```bash
# Basic usage with default sample data
python test_claude_analysis.py

# Using a sample data file
python test_claude_analysis.py --sample-file sample_stock_data.json

# Specify a different Claude model
python test_claude_analysis.py --model claude-3-5-sonnet-20240620

# Save the generated prompt to a file
python test_claude_analysis.py --save-prompt

# Use a specific API key (instead of from .env)
python test_claude_analysis.py --api-key sk-ant-your-key-here
```

## Output Files

The script generates several output files for analysis and debugging:

1. `claude_thinking_{timestamp}.txt` - Contains the extended thinking content from Claude
2. `claude_response_{timestamp}.txt` - Contains the final analysis response
3. `claude_prompt_{timestamp}.txt` - Contains the generated prompt (when using --save-prompt)

## Extended Thinking

This implementation uses Claude's extended thinking feature with a large budget (16,000 tokens) to provide enhanced reasoning capabilities. This allows Claude to:

- Perform more thorough analysis of financial data
- Compare metrics across multiple dimensions
- Reason through complex valuation considerations
- Provide more detailed explanations of recommendations

## Sample Data Structure

The sample data should follow this structure:

```json
{
    "company": {
        "name": "Company Name",
        "ticker": "TICKER",
        "exchange": "EXCHANGE",
        "description": "Company description..."
    },
    "financial_data": {
        "pe_ratio": 15.5,
        "price_to_book": 2.3,
        "debt_to_equity": 0.8,
        "revenue_growth": 12.5,
        "profit_margin": 8.7,
        "dividend_yield": 2.1,
        "free_cash_flow": 500000000,
        "return_on_equity": 15.2,
        "earnings_growth_5yr": 10.5,
        "current_ratio": 2.1
    },
    "valuation": {
        "intrinsic_value": 150,
        "current_price": 120,
        "margin_of_safety": 20
    },
    "industry_comparison": {
        "sector_pe_average": 18.4,
        "sector_growth_average": 8.7,
        "sector_profit_margin_average": 12.3
    },
    "risk_factors": [
        "Risk factor 1",
        "Risk factor 2"
    ],
    "growth_catalysts": [
        "Growth catalyst 1",
        "Growth catalyst 2"
    ]
}
```

## Integration with Main Project

This test script is designed to help debug Claude implementation issues before integrating it into the main portfolio analysis pipeline. Once the test is working correctly, you can apply the same patterns to the main project.

## Troubleshooting

If you encounter authentication errors:
1. Verify your Anthropic API key is correct
2. Check that your API key has access to the requested model
3. Ensure the anthropic library is properly installed and up-to-date

For other issues, check the detailed logs for error messages. 