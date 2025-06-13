import csv
import os
import pandas as pd
from pathlib import Path
import re
import argparse
from datetime import datetime

def read_work_portfolio(filename):
    """Read the work portfolio CSV file"""
    try:
        # Read the file contents as a single string
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Use a simpler approach to parse the file
        lines = content.strip().split('\n')
        if len(lines) >= 2:  # Ensure we have at least a header and data line
            # Assume the first line is the header and the second is GitLab data
            # Parse manually to avoid regex issues
            data_line = lines[1]
            # Extract values by splitting on ',' and cleaning up quotes
            parts = data_line.split(',')
            if len(parts) >= 5:
                security = parts[0].strip('"')
                shares = parts[1].strip('"').strip()
                einstandskurs = parts[2].strip('"').strip()
                current_price = parts[3].strip('"').strip()
                market_value = parts[4].strip('"').strip()
                
                # Convert to standard numeric formats
                try:
                    shares_num = int(shares)
                    einstandskurs_num = float(einstandskurs)
                    current_price_num = float(current_price)
                    # Recalculate market value to ensure consistency
                    market_value_num = shares_num * current_price_num
                except ValueError:
                    print(f"Error converting values for {security}")
                    shares_num = 0
                    einstandskurs_num = 0
                    current_price_num = 0
                    market_value_num = 0
                
                # Create DataFrame directly with data
                data = {
                    'Security': [security],
                    'ISIN': [''],
                    'Shares': [shares_num],
                    'Einstandskurs': [einstandskurs_num],
                    'Current Price (EUR)': [current_price_num],
                    'Market Value (EUR)': [market_value_num],
                    'Weight': [''],  # Will calculate later
                    'Change': [''],
                    'Portfolio': ['Work']
                }
                df = pd.DataFrame(data)
                print(f"Work portfolio data: {df}")
                return df
        
        print("No positions found in Work portfolio")
        return pd.DataFrame({
            'Security': [], 'ISIN': [], 'Shares': [], 'Einstandskurs': [],
            'Current Price (EUR)': [], 'Market Value (EUR)': [], 'Weight': [], 'Change': [], 'Portfolio': []
        })
    except Exception as e:
        print(f"Error reading work portfolio: {e}")
        return pd.DataFrame({
            'Security': [], 'ISIN': [], 'Shares': [], 'Einstandskurs': [],
            'Current Price (EUR)': [], 'Market Value (EUR)': [], 'Weight': [], 'Change': [], 'Portfolio': []
        })

def read_bank_portfolio(filename, portfolio_name):
    """Read bank portfolio CSV files (Family and Brett)"""
    try:
        # Read the file as regular text to handle the specific format
        with open(filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Extract header information
        depot_info = {}
        for i in range(10):  # First few lines contain general portfolio info
            if i < len(lines) and ';' in lines[i]:
                parts = lines[i].strip().split(';', 1)
                if len(parts) >= 2:
                    key = parts[0].strip('"')
                    value = parts[1].strip('"')
                    depot_info[key] = value
        
        # Find the line with position headers
        header_idx = None
        for i, line in enumerate(lines):
            if '"Position";' in line or 'Position;' in line:
                header_idx = i
                break
        
        if header_idx is None:
            print(f"Could not find position headers in {filename}")
            return pd.DataFrame()
        
        # Read positions into dataframe
        positions = []
        for i in range(header_idx + 1, len(lines)):
            line = lines[i].strip()
            if not line or 'Diese Aufstellung' in line:
                break
            
            # Split by semicolon and remove quotes
            fields = [f.strip('"') for f in line.split(';')]
            
            if len(fields) > 18:  # Ensure we have enough fields
                try:
                    # Convert numeric values, handling European number format
                    shares = parse_number(fields[6])
                    einstandskurs = parse_number(fields[7]) if fields[7] else None
                    current_price = parse_number(fields[12])
                    market_value = parse_number(fields[18])
                    
                    # Fix market value calculation if it seems wrong
                    calculated_value = shares * current_price
                    if abs(market_value - calculated_value) > 1:  # Allow small rounding differences
                        print(f"Warning: Market value mismatch for {fields[1]} - reported: {market_value}, calculated: {calculated_value}")
                        market_value = calculated_value
                    
                    # Extract only numeric part from change values
                    change_value = fields[20]
                    change_percent = fields[21]
                    change_str = f"{change_value} ({change_percent})"
                    
                    position = {
                        'Security': fields[1],  # Bezeichnung
                        'ISIN': fields[3],
                        'Shares': shares,
                        'Einstandskurs': einstandskurs,
                        'Current Price (EUR)': current_price,
                        'Market Value (EUR)': market_value,
                        'Weight': '',  # Will calculate later
                        'Change': change_str,
                        'Portfolio': portfolio_name
                    }
                    positions.append(position)
                    print(f"Added position from {portfolio_name}: {fields[1]}")
                except IndexError:
                    print(f"Skipping line due to unexpected format: {line[:50]}...")
            else:
                print(f"Skipping line with insufficient fields: {line[:50]}...")
        
        df = pd.DataFrame(positions)
        print(f"Read {len(positions)} positions from {portfolio_name}")
        return df
    
    except Exception as e:
        print(f"Error reading bank portfolio {filename}: {e}")
        return pd.DataFrame()

def parse_number(value):
    """Parse a number string, handling both US and European formats."""
    if not value or value.strip() == '':
        return 0
    
    # Remove any currency symbols, spaces, and other non-numeric characters except . and ,
    cleaned = ''.join(c for c in value if c.isdigit() or c in '.,+-')
    
    # Check if it's European format (1.234,56)
    if '.' in cleaned and ',' in cleaned and cleaned.rindex('.') < cleaned.rindex(','):
        # European format: remove dots and replace comma with dot
        cleaned = cleaned.replace('.', '').replace(',', '.')
    else:
        # US format or European without thousands separator: just replace comma with dot
        cleaned = cleaned.replace(',', '.')
    
    try:
        return float(cleaned)
    except ValueError:
        print(f"Could not parse number: {value}")
        return 0

def calculate_weights(df):
    """Calculate portfolio weights for each security"""
    try:
        # Ensure market value is numeric
        df['Market Value (EUR)'] = pd.to_numeric(df['Market Value (EUR)'], errors='coerce')
        
        # Fill any NaN values with 0
        df['Market Value (EUR)'] = df['Market Value (EUR)'].fillna(0)
        
        # Calculate total portfolio value
        total_value = df['Market Value (EUR)'].sum()
        
        # Calculate weight as a percentage
        df['Weight'] = (df['Market Value (EUR)'] / total_value * 100).round(2)
        
        return df
    except Exception as e:
        print(f"Error calculating weights: {e}")
        return df

def format_output(df):
    """Format the dataframe for output to CSV"""
    # Make a copy to avoid modifying the original
    formatted_df = df.copy()
    
    # Format numbers for display
    formatted_df['Shares'] = formatted_df['Shares'].fillna(0).astype(int)
    
    # Format currencies with 2 decimal places
    for col in ['Einstandskurs', 'Current Price (EUR)', 'Market Value (EUR)']:
        formatted_df[col] = formatted_df[col].fillna(0).round(2)
    
    # Format weights as percentages
    formatted_df['Weight'] = formatted_df['Weight'].map('{:.2f}%'.format)
    
    return formatted_df

def consolidate_holdings(df):
    """Consolidate duplicate holdings across portfolios"""
    # Group by security/ISIN to find duplicates
    grouped = df.groupby(['Security', 'ISIN'], as_index=False).agg({
        'Shares': 'sum',
        'Einstandskurs': lambda x: 0 if x.isna().all() else x.fillna(0).mean(),  # Simple average for now
        'Current Price (EUR)': 'first',  # Should be same across portfolios
        'Market Value (EUR)': 'sum',
        'Portfolio': lambda x: ', '.join(sorted(set(x)))  # Show which portfolios contain this holding
    })
    
    # Recalculate market value to ensure consistency
    grouped['Market Value (EUR)'] = grouped['Shares'] * grouped['Current Price (EUR)']
    
    # Calculate weighted average cost basis
    # First, create a temporary column for total cost
    df['Total Cost'] = df['Shares'] * df['Einstandskurs']
    
    # Group again to calculate weighted average
    cost_grouped = df.groupby(['Security', 'ISIN'], as_index=False).agg({
        'Total Cost': 'sum',
        'Shares': 'sum'
    })
    
    # Calculate weighted average Einstandskurs
    cost_grouped['Weighted Einstandskurs'] = cost_grouped['Total Cost'] / cost_grouped['Shares']
    
    # Merge back the weighted average cost
    grouped = grouped.drop('Einstandskurs', axis=1)
    grouped = grouped.merge(
        cost_grouped[['Security', 'ISIN', 'Weighted Einstandskurs']], 
        on=['Security', 'ISIN'], 
        how='left'
    )
    grouped = grouped.rename(columns={'Weighted Einstandskurs': 'Einstandskurs'})
    
    # Calculate gain/loss
    grouped['Change'] = ((grouped['Current Price (EUR)'] - grouped['Einstandskurs']) * grouped['Shares']).round(2)
    grouped['Change %'] = ((grouped['Current Price (EUR)'] / grouped['Einstandskurs'] - 1) * 100).round(2)
    grouped['Change'] = grouped.apply(lambda row: f"€{row['Change']:,.2f} ({row['Change %']:.2f}%)", axis=1)
    grouped = grouped.drop('Change %', axis=1)
    
    print(f"Consolidated {len(df)} positions into {len(grouped)} unique holdings")
    
    return grouped

def detect_portfolio_type(filename):
    """Detect the type of portfolio file based on its name and content"""
    name_lower = filename.name.lower()
    
    # Check filename patterns
    if 'work' in name_lower and 'portfolio' in name_lower:
        return 'work'
    elif 'family' in name_lower and 'report' in name_lower:
        return 'family'
    elif 'brett' in name_lower and 'report' in name_lower:
        return 'brett'
    else:
        # Try to detect by reading first few lines
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                first_line = f.readline().lower()
                if 'gitlab' in first_line or 'einstandskurs' in first_line:
                    return 'work'
                elif 'depotübersicht' in first_line or 'position;' in first_line:
                    # Check for depot name in the file
                    for _ in range(10):
                        line = f.readline()
                        if 'Depot;' in line:
                            if 'Family' in line:
                                return 'family'
                            elif 'Brett' in line:
                                return 'brett'
        except:
            pass
    
    return None

def main():
    parser = argparse.ArgumentParser(description='Combine and consolidate portfolio CSV files')
    parser.add_argument('--source', '-s', type=str, 
                        default='/Users/brettgray/Coding/Cursor/Investment Master R4/Source',
                        help='Source directory containing portfolio CSV files')
    parser.add_argument('--output', '-o', type=str,
                        default='/Users/brettgray/Coding/Cursor/Investment Master R4/combined_portfolio.csv',
                        help='Output file path for combined portfolio')
    parser.add_argument('--timestamp', '-t', action='store_true',
                        help='Add timestamp to output filename')
    parser.add_argument('--date-format', action='store_true',
                        help='Use date format (YYYY-MM-DD) instead of timestamp')
    parser.add_argument('--no-archive', action='store_true',
                        help='Skip archiving to Archive folder')
    parser.add_argument('--no-current', action='store_true',
                        help='Skip creating/updating current combined_portfolio.csv')
    parser.add_argument('--no-details', action='store_true',
                        help='Skip creating detailed (unconsolidated) portfolio file')
    
    args = parser.parse_args()
    
    source_dir = Path(args.source)
    base_dir = source_dir.parent
    output_file = Path(args.output)
    
    # Create Archive folder if it doesn't exist
    archive_dir = base_dir / 'Archive'
    if not args.no_archive:
        archive_dir.mkdir(exist_ok=True)
    
    # Determine the timestamp/date format
    if args.timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_stem = f"{output_file.stem}_{timestamp}"
    elif args.date_format:
        date_str = datetime.now().strftime('%Y-%m-%d')
        archive_stem = f"{output_file.stem}_{date_str}"
    else:
        # Default to date format for archives
        date_str = datetime.now().strftime('%Y-%m-%d')
        archive_stem = f"{output_file.stem}_{date_str}"
    
    # Find all CSV files in the source directory
    csv_files = list(source_dir.glob('*.csv'))
    
    if not csv_files:
        print(f"No CSV files found in {source_dir}")
        return
    
    print(f"Found {len(csv_files)} CSV files in {source_dir}")
    
    # Categorize portfolio files
    portfolios = {'work': None, 'family': None, 'brett': None}
    unidentified = []
    
    # Group files by portfolio type
    portfolio_candidates = {'work': [], 'family': [], 'brett': []}
    
    for csv_file in csv_files:
        portfolio_type = detect_portfolio_type(csv_file)
        if portfolio_type and portfolio_type in portfolio_candidates:
            portfolio_candidates[portfolio_type].append(csv_file)
            print(f"  - {csv_file.name} identified as {portfolio_type.capitalize()} portfolio")
        else:
            unidentified.append(csv_file)
            print(f"  - {csv_file.name} could not be identified")
    
    # Select the most recent file for each portfolio type
    for ptype, candidates in portfolio_candidates.items():
        if candidates:
            # Sort by modification time and pick the most recent
            most_recent = max(candidates, key=lambda f: f.stat().st_mtime)
            portfolios[ptype] = most_recent
            if len(candidates) > 1:
                print(f"  Note: Using most recent {ptype.capitalize()} portfolio: {most_recent.name}")
    
    # Check if we have all required portfolios
    missing = [k for k, v in portfolios.items() if v is None]
    if missing:
        print(f"\nWarning: Missing portfolio types: {', '.join(missing)}")
        print("The script will continue with available portfolios.")
    
    if unidentified:
        print(f"\nUnidentified files: {', '.join(f.name for f in unidentified)}")
    
    # Read all available portfolios
    all_dfs = []
    
    if portfolios['work']:
        print(f"\nProcessing Work portfolio: {portfolios['work'].name}")
        work_df = read_work_portfolio(portfolios['work'])
        if not work_df.empty:
            all_dfs.append(work_df)
    
    if portfolios['family']:
        print(f"Processing Family portfolio: {portfolios['family'].name}")
        family_df = read_bank_portfolio(portfolios['family'], 'Family')
        if not family_df.empty:
            all_dfs.append(family_df)
    
    if portfolios['brett']:
        print(f"Processing Brett portfolio: {portfolios['brett'].name}")
        brett_df = read_bank_portfolio(portfolios['brett'], 'Brett')
        if not brett_df.empty:
            all_dfs.append(brett_df)
    
    if not all_dfs:
        print("No portfolio data could be read. Exiting.")
        return
    
    # Combine all portfolios
    combined_df = pd.concat(all_dfs, ignore_index=True)
    
    print(f"\nTotal positions before consolidation: {len(combined_df)}")
    
    # Consolidate duplicate holdings
    consolidated_df = consolidate_holdings(combined_df)
    
    # Calculate weights for the combined portfolio
    consolidated_df = calculate_weights(consolidated_df)
    
    # Format for output
    formatted_df = format_output(consolidated_df)
    
    # Save files based on configuration
    files_saved = []
    
    # 1. Always save to archive (unless disabled)
    if not args.no_archive:
        archive_file = archive_dir / f"{archive_stem}.csv"
        formatted_df.to_csv(archive_file, index=False)
        files_saved.append(f"Archive: {archive_file}")
        
        # Also save detailed version to archive
        if not args.no_details:
            detailed_archive = archive_dir / f"{archive_stem}_detailed.csv"
            combined_df = calculate_weights(combined_df)
            format_output(combined_df).to_csv(detailed_archive, index=False)
            files_saved.append(f"Archive (detailed): {detailed_archive}")
    
    # 2. Update current portfolio file (unless disabled)
    if not args.no_current:
        current_file = base_dir / 'combined_portfolio.csv'
        formatted_df.to_csv(current_file, index=False)
        files_saved.append(f"Current: {current_file}")
        
        # Also update current detailed version
        if not args.no_details:
            current_detailed = base_dir / 'combined_portfolio_detailed.csv'
            if 'combined_df' not in locals():
                combined_df = calculate_weights(combined_df)
            format_output(combined_df).to_csv(current_detailed, index=False)
            files_saved.append(f"Current (detailed): {current_detailed}")
    
    # 3. Save to custom output path if specified and different from default
    if args.output != parser.get_default('output') and args.output != str(base_dir / 'combined_portfolio.csv'):
        formatted_df.to_csv(output_file, index=False)
        files_saved.append(f"Custom: {output_file}")
    
    # Print summary of saved files
    print("\nFiles saved:")
    for file_info in files_saved:
        print(f"  - {file_info}")

if __name__ == "__main__":
    main() 