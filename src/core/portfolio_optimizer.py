"""
Portfolio Optimizer - Module for optimizing investment portfolio based on analysis results

This module leverages the results from the value investing analysis and current portfolio
holdings to provide optimization recommendations. It includes functionality to:
1. Parse portfolio data from a bank CSV export
2. Map the portfolio data to analysis results
3. Generate optimization recommendations based on value investing principles
4. Format the results in markdown for easy readability
"""

import os
import csv
import json
import re
from datetime import datetime
from src.core.logger import logger
from src.core.config import config
from src.core.file_operations import save_markdown
from src.core.portfolio import get_stock_ticker_and_exchange

def read_csv_content(csv_path):
    """Read raw content from a CSV file.
    
    Args:
        csv_path (str): Path to the CSV file containing portfolio data.
        
    Returns:
        str: Raw content of the CSV file or None if error.
    """
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except FileNotFoundError:
        logger.error(f"Portfolio CSV file {csv_path} not found.")
        return None
    except Exception as e:
        logger.error(f"Error reading portfolio CSV file: {e}")
        return None

def determine_delimiter(lines):
    """Determine the delimiter used in the CSV file.
    
    Args:
        lines (list): List of lines from the CSV file.
        
    Returns:
        str: Delimiter character (';' or ',').
    """
    delimiter = ';'
    if lines and ',' in lines[0] and ';' not in lines[0]:
        delimiter = ','
    return delimiter

def extract_portfolio_summary(lines, delimiter):
    """Extract portfolio summary information from CSV header.
    
    Args:
        lines (list): List of lines from the CSV file.
        delimiter (str): Delimiter character.
        
    Returns:
        dict: Portfolio summary information.
        str: Date string in YYYY-MM-DD format.
    """
    portfolio_summary = {}
    date = datetime.now().strftime("%Y-%m-%d")  # Default date
    
    # If using semicolon format, try to extract summary data
    if delimiter == ';':
        for i in range(10):  # First 10 lines usually contain summary data
            if i < len(lines) and delimiter in lines[i]:
                key, value = lines[i].split(delimiter, 1)
                portfolio_summary[key] = process_summary_value(key, value)
                
                # Try to extract date
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', value)
                if date_match:
                    date_str = date_match.group(1)
                    try:
                        date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                        date = date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        pass
    
    # Set the date in the summary
    portfolio_summary['date'] = date
    return portfolio_summary, date

def process_summary_value(key, value):
    """Process and convert summary values to appropriate types.
    
    Args:
        key (str): Key name.
        value (str): Raw value string.
        
    Returns:
        float or str: Processed value.
    """
    value = value.strip()
    
    if 'EUR' in value:
        # Extract numerical value and convert to float
        match = re.search(r'([\d.,]+)', value.replace(' ', ''))
        if match:
            # Replace comma with dot for float conversion
            num_str = match.group(1).replace('.', '').replace(',', '.')
            try:
                return float(num_str)
            except ValueError:
                return value
    elif '%' in value:
        # Extract percentage and convert to float
        match = re.search(r'([+-]?[\d.,]+)', value.replace(',', '.'))
        if match:
            return float(match.group(1))
    
    return value

def find_header_line(lines, delimiter):
    """Find the line containing column headers.
    
    Args:
        lines (list): List of lines from the CSV file.
        delimiter (str): Delimiter character.
        
    Returns:
        int or None: Index of header line or None if not found.
    """
    # Check for traditional semicolon format
    for i, line in enumerate(lines):
        if delimiter == ';' and line.startswith('Position;Bezeichnung;WKN;ISIN'):
            return i
            
    # Check for comma-separated format (combined_portfolio.csv)
    if delimiter == ',':
        for i, line in enumerate(lines):
            if 'Security' in line and 'ISIN' in line and 'Shares' in line:
                return i
    
    # If we can't find a header line but it looks like a CSV, use the first line
    if lines and delimiter in lines[0]:
        return 0
    
    return None

def parse_positions(lines, header_line_idx, headers, delimiter):
    """Parse position data from CSV lines.
    
    Args:
        lines (list): List of lines from the CSV file.
        header_line_idx (int): Index of the header line.
        headers (list): List of column headers.
        delimiter (str): Delimiter character.
        
    Returns:
        list: List of parsed positions.
    """
    positions = []
    for i in range(header_line_idx + 1, len(lines)):
        line = lines[i].strip()
        if not line or line.startswith('Diese Aufstellung'):
            break
        
        # For the comma-separated format, handle quoted values correctly
        if delimiter == ',':
            values = next(csv.reader([line], delimiter=delimiter, quotechar='"'))
        else:
            values = line.split(delimiter)
        
        if len(values) < len(headers):
            continue
        
        position = create_position_entry(headers, values)
        positions.append(position)
    
    return positions

def create_position_entry(headers, values):
    """Create a position entry from header and value lists.
    
    Args:
        headers (list): List of column headers.
        values (list): List of values.
        
    Returns:
        dict: Position entry with processed values.
    """
    position = {}
    for j, header in enumerate(headers):
        if j < len(values):
            value = values[j].strip() if values[j] else ""
            
            # Skip empty values
            if not value:
                position[header] = None
                continue
            
            position[header] = convert_position_value(header, value)
    
    return position

def convert_position_value(header, value):
    """Convert position values to appropriate types.
    
    Args:
        header (str): Column header.
        value (str): Raw value string.
        
    Returns:
        int, float, or str: Converted value.
    """
    # Convert numerical values
    if re.match(r'^[+-]?\d+$', value):
        return int(value)
    elif re.match(r'^[+-]?\d+[.,]\d+$', value):
        return float(value.replace(',', '.'))
    elif header == 'Veränderung in %' and value.startswith('+'):
        return float(value.replace('+', '').replace(',', '.'))
    elif header == 'Veränderung in EUR' and value.startswith('+'):
        return float(value.replace('+', '').replace('.', '').replace(',', '.'))
    elif header == 'Anteil im Depot':
        return float(value.replace(',', '.'))
    elif header in ['Einstandskurs', 'akt. Kurs']:
        return float(value.replace(',', '.'))
    elif header == 'Einstandswert in EUR' or header == 'Wert in EUR':
        return float(value.replace('.', '').replace(',', '.'))
    else:
        return value

def parse_portfolio_csv(csv_path):
    """Parse portfolio data from a bank CSV export.
    
    Args:
        csv_path (str): Path to the CSV file containing portfolio data.
        
    Returns:
        dict: Dictionary containing portfolio summary and positions.
    """
    content = read_csv_content(csv_path)
    if not content:
        return None
    
    # Print first 10 lines of content for debugging
    print("Portfolio CSV - first 10 lines:")
    lines = content.split('\n')
    for i, line in enumerate(lines[:10]):
        print(f"Line {i}: {line}")
    
    delimiter = determine_delimiter(lines)
    portfolio_summary, date = extract_portfolio_summary(lines, delimiter)
    
    # Print the extracted summary values for debugging
    print("\nPortfolio summary extracted values:")
    for key, value in portfolio_summary.items():
        print(f"{key}: {value} (type: {type(value)})")
    
    header_line_idx = find_header_line(lines, delimiter)
    if header_line_idx is None:
        logger.error("Could not find column headers in CSV file.")
        return {"summary": portfolio_summary, "positions": []}
    
    # Get column headers
    headers = [h.strip() for h in lines[header_line_idx].split(delimiter)]
    
    # Parse positions
    positions = parse_positions(lines, header_line_idx, headers, delimiter)
    
    return {
        "summary": portfolio_summary,
        "positions": positions,
        "date": date
    }

def map_portfolio_to_analysis(portfolio_data, analysis_results):
    """Map portfolio positions to analysis results.
    
    Args:
        portfolio_data (dict): Portfolio data from parse_portfolio_csv.
        analysis_results (dict): Analysis results from get_value_investing_signals.
        
    Returns:
        list: List of positions with analysis results.
    """
    # Extract tickers from analysis results for easy lookup
    analysis_by_ticker = {}
    for stock in analysis_results:
        ticker = stock.get('ticker')
        if ticker:
            analysis_by_ticker[ticker] = stock
    
    # Map for converting portfolio designations to tickers
    ticker_map = {
        "ALLIANZ SE NA O.N.": "ALV",
        "ASML HOLDING    EO -,09": "ASML",
        "ADVANCED MIC.DEV.  DL-,01": "AMD",
        "ALPHABET INC.CL C DL-,001": "GOOG",
        "BERKSH. H.B NEW DL-,00333": "BRK.B",
        "CROWDSTRIKE HLD. DL-,0005": "CRWD",
        "MICROSOFT    DL-,00000625": "MSFT",
        "NUTANIX INC. A": "NTNX",
        "NVIDIA CORP.      DL-,001": "NVDA",
        "TAIWAN SEMICON.MANU.ADR/5": "TSM"
    }
    
    # Map positions to analysis
    mapped_positions = []
    for position in portfolio_data['positions']:
        designation = position.get('Bezeichnung')
        if not designation:
            continue
        
        ticker = ticker_map.get(designation)
        if not ticker:
            logger.warning(f"Could not map {designation} to a ticker.")
            position['analysis'] = None
            mapped_positions.append(position)
            continue
        
        analysis = analysis_by_ticker.get(ticker)
        position['analysis'] = analysis
        position['ticker'] = ticker
        mapped_positions.append(position)
    
    return mapped_positions

def validate_total_value(total_value):
    """Validate and convert total value to float if needed.
    
    Args:
        total_value: The total value to validate, can be float or string.
        
    Returns:
        float or None: Validated total value or None if invalid.
    """
    if total_value is None:
        return None
        
    if isinstance(total_value, str):
        # Try to convert string to float - handle European format
        try:
            # Remove any non-numeric characters except for comma and period
            cleaned_value = ''.join(c for c in total_value if c.isdigit() or c in ',.').strip()
            # Replace comma with period for float conversion
            cleaned_value = cleaned_value.replace('.', '').replace(',', '.')
            total_value = float(cleaned_value)
            print(f"Converted string total value to number: €{total_value:,.2f}")
        except (ValueError, TypeError):
            total_value = None
            print(f"Could not convert total value string: {total_value}")
    
    return total_value

def calculate_total_value_from_positions(mapped_positions):
    """Calculate total portfolio value from positions.
    
    Args:
        mapped_positions (list): List of positions with analysis results.
        
    Returns:
        float: Calculated total value or default value if calculation fails.
    """
    calculated_value = 0
    for position in mapped_positions:
        position_value = position.get('Wert in EUR', 0)
        if isinstance(position_value, str):
            # Convert string to float if needed
            try:
                cleaned_value = ''.join(c for c in position_value if c.isdigit() or c in ',.').strip()
                cleaned_value = cleaned_value.replace('.', '').replace(',', '.')
                position_value = float(cleaned_value)
            except (ValueError, TypeError):
                position_value = 0
        calculated_value += position_value
        
    if calculated_value > 0:
        print(f"Using calculated total value from positions: €{calculated_value:,.2f}")
        return calculated_value
    else:
        # Fallback to a default value if can't calculate
        default_value = 220575.80  # Default from the CSV
        print(f"Using default total value: €{default_value:,.2f}")
        return default_value

def categorize_positions(mapped_positions):
    """Categorize positions based on analysis recommendations.
    
    Args:
        mapped_positions (list): List of positions with analysis results.
        
    Returns:
        tuple: Lists of buy, hold, sell positions.
    """
    buys = []
    holds = []
    sells = []
    
    for position in mapped_positions:
        if position['analysis'] is None:
            logger.warning(f"No analysis found for {position.get('ticker', 'unknown')}. Treating as HOLD.")
            position['analysis'] = {'recommendation': 'HOLD'}
            holds.append(position)
            continue
        
        # Get recommendation, defaulting to HOLD if missing
        recommendation = position['analysis'].get('recommendation', 'HOLD')
        if recommendation is None or recommendation.strip() == '':
            recommendation = 'HOLD'
            position['analysis']['recommendation'] = 'HOLD'
        
        # Normalize the recommendation text to handle variations
        rec_upper = recommendation.upper()
        
        # Check for various forms of BUY/SELL/HOLD
        if any(buy_term in rec_upper for buy_term in ['BUY', 'STRONG BUY', 'ACCUMULATE', 'OVERWEIGHT']):
            buys.append(position)
        elif any(sell_term in rec_upper for sell_term in ['SELL', 'STRONG SELL', 'REDUCE', 'UNDERWEIGHT']):
            sells.append(position)
        elif any(hold_term in rec_upper for hold_term in ['HOLD', 'NEUTRAL', 'MARKET PERFORM', 'EQUAL WEIGHT']):
            holds.append(position)
        else:
            # If we can't categorize, default to HOLD
            logger.warning(f"Couldn't categorize recommendation '{recommendation}' for {position.get('ticker', 'unknown')}. Defaulting to HOLD.")
            holds.append(position)
    
    return buys, holds, sells

def calculate_current_allocation(mapped_positions):
    """Calculate current portfolio allocation.
    
    Args:
        mapped_positions (list): List of positions with analysis results.
        
    Returns:
        dict: Current allocation by ticker.
    """
    current_allocation = {}
    for position in mapped_positions:
        ticker = position.get('ticker')
        if ticker:
            # Get recommendation with clear default
            recommendation = 'HOLD'
            if position['analysis'] and isinstance(position['analysis'], dict):
                rec = position['analysis'].get('recommendation')
                if rec and isinstance(rec, str) and rec.strip():
                    recommendation = rec.strip()
                    
            current_allocation[ticker] = {
                'percent': position.get('Anteil im Depot', 0),
                'value': position.get('Wert in EUR', 0),
                'name': position.get('Bezeichnung', ticker),
                'recommendation': recommendation
            }
    
    return current_allocation

def calculate_target_allocation(current_allocation):
    """Calculate target portfolio allocation based on recommendations.
    
    Args:
        current_allocation (dict): Current allocation by ticker.
        
    Returns:
        dict: Target allocation by ticker.
    """
    # Get factors from configuration
    buy_boost = config["portfolio"]["optimization"].get("buy_boost_factor", 1.5)
    sell_reduction = config["portfolio"]["optimization"].get("sell_reduction_factor", 0.5)
    
    target_allocation = {}
    preliminary_allocations = {}
    
    # Calculate preliminary target allocations
    for ticker, data in current_allocation.items():
        recommendation = data['recommendation']
        rec_upper = recommendation.upper()
        
        # Apply different allocation factors based on recommendation type
        if any(buy_term in rec_upper for buy_term in ['BUY', 'STRONG BUY', 'ACCUMULATE', 'OVERWEIGHT']):
            preliminary_allocations[ticker] = data['percent'] * buy_boost
        elif any(sell_term in rec_upper for sell_term in ['SELL', 'STRONG SELL', 'REDUCE', 'UNDERWEIGHT']):
            preliminary_allocations[ticker] = data['percent'] * sell_reduction
        else:  # HOLD or any unrecognized recommendation
            preliminary_allocations[ticker] = data['percent']
    
    # Normalize allocations to sum to 100%
    total_preliminary = sum(preliminary_allocations.values())
    if total_preliminary > 0:  # Avoid division by zero
        for ticker, allocation in preliminary_allocations.items():
            target_allocation[ticker] = (allocation / total_preliminary) * 100
    else:
        # If sum is zero (unlikely), just keep current allocations
        for ticker, data in current_allocation.items():
            target_allocation[ticker] = data['percent']
    
    return target_allocation

def calculate_allocation_changes(current_allocation, target_allocation, total_value):
    """Calculate changes needed to reach target allocation.
    
    Args:
        current_allocation (dict): Current allocation by ticker.
        target_allocation (dict): Target allocation by ticker.
        total_value (float): Total portfolio value.
        
    Returns:
        list: Sorted list of changes by magnitude.
    """
    changes = {}
    for ticker, target in target_allocation.items():
        current = current_allocation[ticker]['percent']
        
        # Ensure values are floats 
        if isinstance(current, str):
            try:
                current = float(current.replace('%', '').strip())
            except ValueError:
                logger.warning(f"Invalid current percent for {ticker}: {current}. Using 0.")
                current = 0.0
                
        if isinstance(target, str):
            try:
                target = float(target.replace('%', '').strip())
            except ValueError:
                logger.warning(f"Invalid target percent for {ticker}: {target}. Using current value.")
                target = current
        
        change_percent = target - current
        
        # Calculate the change value
        try:
            change_value = (change_percent / 100) * total_value
        except (TypeError, ValueError):
            logger.warning(f"Error calculating change value for {ticker}. Using 0.")
            change_value = 0.0
        
        changes[ticker] = {
            'ticker': ticker,
            'name': current_allocation[ticker]['name'],
            'current_percent': current,
            'target_percent': target,
            'change_percent': change_percent,
            'change_value': change_value,
            'recommendation': current_allocation[ticker]['recommendation']
        }
    
    # Sort changes by absolute magnitude (largest changes first)
    sorted_changes = sorted(
        changes.values(), 
        key=lambda x: abs(x['change_percent']), 
        reverse=True
    )
    
    return sorted_changes

def optimize_portfolio(mapped_positions, total_value=None):
    """Generate portfolio optimization recommendations.
    
    Args:
        mapped_positions (list): List of positions with analysis results.
        total_value (float, optional): Total portfolio value. If None, calculated from positions.
        
    Returns:
        dict: Dictionary containing optimization recommendations.
    """
    # Validate and get total value
    total_value = validate_total_value(total_value)
    
    # If total_value isn't provided or is invalid, calculate from positions
    if not total_value:
        total_value = calculate_total_value_from_positions(mapped_positions)
    else:
        print(f"Using provided total value: €{total_value:,.2f}")
    
    # Categorize positions
    buys, holds, sells = categorize_positions(mapped_positions)
    
    # Calculate current allocation
    current_allocation = calculate_current_allocation(mapped_positions)
    
    # Calculate target allocation
    target_allocation = calculate_target_allocation(current_allocation)
    
    # Calculate changes needed
    sorted_changes = calculate_allocation_changes(current_allocation, target_allocation, total_value)
    
    return {
        'total_value': total_value,
        'current_allocation': current_allocation,
        'target_allocation': target_allocation,
        'changes': sorted_changes
    }

def format_portfolio_summary(portfolio_data, total_value):
    """Format portfolio summary section in markdown.
    
    Args:
        portfolio_data (dict): Portfolio data.
        total_value (float): Total portfolio value.
        
    Returns:
        str: Markdown-formatted portfolio summary.
    """
    markdown = "## Portfolio Summary\n\n"
    markdown += f"Date: {portfolio_data['date']}\n\n"
    
    # Format the total value ensuring it's a number
    if isinstance(total_value, str):
        try:
            total_value = float(total_value.replace(',', '').replace('.', '').replace('€', ''))
        except (ValueError, TypeError):
            total_value = 0.0
    
    markdown += f"Total portfolio value: €{total_value:,.2f}\n"
    markdown += f"Total positions: {len(portfolio_data['positions'])}\n\n"
    
    return markdown

def ensure_numeric_value(value, default=0.0):
    """Ensure a value is numeric, converting from string if needed.
    
    Args:
        value: Value to ensure is numeric.
        default (float): Default value if conversion fails.
        
    Returns:
        float: Numeric value.
    """
    if isinstance(value, (int, float)):
        return float(value)
        
    if isinstance(value, str):
        try:
            # Handle various formats including percentage and currency
            clean_value = value.replace('%', '').replace(',', '.').replace('€', '').strip()
            return float(clean_value)
        except (ValueError, TypeError):
            return default
    
    return default

def format_changes_table(changes):
    """Format table of recommended changes in markdown.
    
    Args:
        changes (list): List of portfolio changes.
        
    Returns:
        str: Markdown-formatted table of changes.
    """
    markdown = "## Optimization Recommendations\n\n"
    markdown += "Based on the value investing analysis, the following changes are recommended:\n\n"
    
    # Add table of recommended changes
    markdown += "| Stock | Ticker | Current % | Target % | Change % | Change Value (€) | Recommendation |\n"
    markdown += "|-------|--------|-----------|----------|----------|-----------------|----------------|\n"
    
    for change in changes:
        markdown += f"| {change['name']} | {change['ticker']} | "
        
        # Ensure values are numeric
        current_percent = ensure_numeric_value(change['current_percent'])
        target_percent = ensure_numeric_value(change['target_percent'], current_percent)
        change_percent = ensure_numeric_value(change['change_percent'])
        change_value = ensure_numeric_value(change['change_value'])
        
        markdown += f"{current_percent:.2f}% | {target_percent:.2f}% | "
        
        # Format change with plus/minus sign
        change_percent_str = f"+{change_percent:.2f}%" if change_percent >= 0 else f"{change_percent:.2f}%"
        change_value_str = f"+{change_value:,.2f}" if change_value >= 0 else f"{change_value:,.2f}"
        
        markdown += f"{change_percent_str} | {change_value_str} | {change['recommendation']} |\n"
    
    return markdown

def format_buy_recommendations(changes):
    """Format buy recommendations section in markdown.
    
    Args:
        changes (list): List of portfolio changes.
        
    Returns:
        str: Markdown-formatted buy recommendations.
    """
    # Buy recommendations (positive change values)
    buys = [c for c in changes if ensure_numeric_value(c['change_value']) > 0]
    if not buys:
        return ""
        
    markdown = "### Stocks to Buy/Increase\n\n"
    for buy in buys:
        # Ensure values are numeric
        change_value = ensure_numeric_value(buy['change_value'])
        current_percent = ensure_numeric_value(buy['current_percent'])
        target_percent = ensure_numeric_value(buy['target_percent'], current_percent)
        
        markdown += f"- **{buy['name']} ({buy['ticker']})**: Increase position by €{change_value:,.2f} "
        markdown += f"(from {current_percent:.2f}% to {target_percent:.2f}%)\n"
        markdown += f"  - *Rationale*: {buy['recommendation']}\n\n"
    
    return markdown

def format_sell_recommendations(changes):
    """Format sell recommendations section in markdown.
    
    Args:
        changes (list): List of portfolio changes.
        
    Returns:
        str: Markdown-formatted sell recommendations.
    """
    # Sell recommendations (negative change values)
    sells = [c for c in changes if ensure_numeric_value(c['change_value']) < 0]
    if not sells:
        return ""
        
    markdown = "### Stocks to Sell/Reduce\n\n"
    for sell in sells:
        # Ensure values are numeric
        change_value = ensure_numeric_value(sell['change_value'])
        current_percent = ensure_numeric_value(sell['current_percent'])
        target_percent = ensure_numeric_value(sell['target_percent'], current_percent)
        
        markdown += f"- **{sell['name']} ({sell['ticker']})**: Reduce position by €{abs(change_value):,.2f} "
        markdown += f"(from {current_percent:.2f}% to {target_percent:.2f}%)\n"
        markdown += f"  - *Rationale*: {sell['recommendation']}\n\n"
    
    return markdown

def format_disclaimer():
    """Format disclaimer section in markdown.
    
    Returns:
        str: Markdown-formatted disclaimer.
    """
    markdown = "## Disclaimer\n\n"
    markdown += "These recommendations are based on algorithmic analysis of financial data and should not be "
    markdown += "considered financial advice. All investment decisions should be made based on your own research "
    markdown += "and in consultation with a qualified financial advisor. Past performance is not indicative of future results.\n"
    
    return markdown

def format_optimization_to_markdown(optimization_results, portfolio_data):
    """Format optimization results to markdown.
    
    Args:
        optimization_results (dict): Results from optimize_portfolio.
        portfolio_data (dict): Original portfolio data.
        
    Returns:
        str: Markdown-formatted optimization recommendations.
    """
    markdown = "# Portfolio Optimization Recommendations\n\n"
    
    # Add portfolio summary
    markdown += format_portfolio_summary(portfolio_data, optimization_results['total_value'])
    
    # Add optimization summary
    markdown += format_changes_table(optimization_results['changes'])
    
    # Add specific action items section
    markdown += "\n## Action Items\n\n"
    
    # Add buy and sell recommendations
    markdown += format_buy_recommendations(optimization_results['changes'])
    markdown += format_sell_recommendations(optimization_results['changes'])
    
    # Add disclaimer
    markdown += "\n" + format_disclaimer()
    
    return markdown 