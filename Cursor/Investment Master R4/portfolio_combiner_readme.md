# Portfolio Combiner

## Overview
The `combine_portfolios.py` script automatically detects and combines multiple portfolio CSV files from different sources, consolidating duplicate holdings and calculating weighted average cost basis.

## Features
- **Automatic file detection**: Identifies Work, Family, and Brett portfolios by filename or content
- **Duplicate consolidation**: Merges positions held in multiple portfolios
- **Weighted average cost**: Calculates proper cost basis for consolidated positions
- **Portfolio tracking**: Shows which portfolios contain each holding
- **Gain/loss calculation**: Displays both amount and percentage changes

## Usage

### Basic usage (with defaults):
```bash
python combine_portfolios.py
```

### With custom options:
```bash
# Specify custom source directory
python combine_portfolios.py --source /path/to/csv/files

# Custom output file
python combine_portfolios.py --output my_combined_portfolio.csv

# Add timestamp to output filename
python combine_portfolios.py --timestamp

# Skip detailed output file
python combine_portfolios.py --no-details
```

### Command-line options:
- `--source, -s`: Source directory containing portfolio CSV files (default: ./Source)
- `--output, -o`: Output file path for combined portfolio (default: ./combined_portfolio.csv)
- `--timestamp, -t`: Add timestamp to output filename (e.g., combined_portfolio_20250113_143022.csv)
- `--no-details`: Skip creating the detailed (unconsolidated) portfolio file

## File Detection
The script automatically detects portfolio types by:
1. **Filename patterns**:
   - Work: Contains "work" and "portfolio"
   - Family: Contains "family" and "report"
   - Brett: Contains "brett" and "report"
2. **File content**: If filename doesn't match, it checks the content for identifying markers

## Output Files
1. **combined_portfolio.csv**: Consolidated holdings with duplicates merged
2. **combined_portfolio_detailed.csv**: All positions without consolidation (optional)

## Adding New Portfolio Files
Simply place new CSV files in the Source directory and run the script. The automatic detection will categorize them appropriately.

## Example Output
```
Found 3 CSV files in Source
  - Work portfolio 16.03.2025.csv identified as Work portfolio
  - Family_Report_Depotübersicht_vom_07.05.2025.csv identified as Family portfolio
  - Brett_Report_Depotübersicht_vom_07.05.2025.csv identified as Brett portfolio

Processing Work portfolio: Work portfolio 16.03.2025.csv
Processing Family portfolio: Family_Report_Depotübersicht_vom_07.05.2025.csv
Processing Brett portfolio: Brett_Report_Depotübersicht_vom_07.05.2025.csv

Total positions before consolidation: 20
Consolidated 20 positions into 12 unique holdings
Combined portfolio saved to combined_portfolio.csv
Detailed portfolio saved to combined_portfolio_detailed.csv
```