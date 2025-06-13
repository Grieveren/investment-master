#!/usr/bin/env python3
"""
Generate HTML reports from stock analysis results.
This script takes a stock ticker, performs analysis, and generates a beautiful HTML report.
"""

import os
import argparse
import jinja2
from datetime import datetime
from stock_analyzer import StockAnalyzer

def generate_html_report(ticker, output_dir='reports'):
    """
    Generate an HTML report for a stock analysis.
    
    Parameters:
    - ticker: Stock ticker symbol
    - output_dir: Directory to save the report (default: 'reports')
    
    Returns:
    - Path to the generated HTML report
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create a stock analyzer instance and run analysis
    analyzer = StockAnalyzer(ticker)
    analysis = analyzer.analyze_stock()
    
    # Load the HTML template
    template_loader = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("report_template.html")
    
    # Prepare data for the template
    template_data = {
        'ticker': ticker,
        'company_name': analysis['company_name'],
        'analysis_date': analysis['analysis_date'],
        
        # Current price and metrics
        'current_price': f"{analysis['metrics'].get('current_price', 'N/A'):.2f}" if analysis['metrics'].get('current_price') else 'N/A',
        'pe_ratio': f"{analysis['metrics'].get('pe_ratio', 'N/A'):.2f}" if analysis['metrics'].get('pe_ratio') else 'N/A',
        'pb_ratio': f"{analysis['metrics'].get('pb_ratio', 'N/A'):.2f}" if analysis['metrics'].get('pb_ratio') else 'N/A',
        'dividend_yield': f"{analysis['metrics'].get('dividend_yield', 0) * 100:.2f}" if analysis['metrics'].get('dividend_yield') else '0.00',
        'debt_to_equity': f"{analysis['metrics'].get('debt_to_equity', 'N/A'):.2f}" if analysis['metrics'].get('debt_to_equity') else 'N/A',
        'current_ratio': f"{analysis['metrics'].get('current_ratio', 'N/A'):.2f}" if analysis['metrics'].get('current_ratio') else 'N/A',
        'roe': f"{analysis['metrics'].get('roe', 0) * 100:.2f}" if analysis['metrics'].get('roe') else 'N/A',
        'profit_margin': f"{analysis['metrics'].get('profit_margin', 0) * 100:.2f}" if analysis['metrics'].get('profit_margin') else 'N/A',
        
        # Recommendation
        'recommendation': analysis['summary'].get('recommendation', 'INSUFFICIENT DATA'),
        'recommendation_class': get_recommendation_class(analysis['summary'].get('recommendation', '')),
        
        # Strengths and concerns
        'strengths': analysis['summary'].get('strengths', []),
        'concerns': analysis['summary'].get('concerns', []),
    }
    
    # DCF Valuation
    if 'error' not in analysis['dcf_valuation']:
        template_data['dcf_intrinsic_value'] = f"{analysis['dcf_valuation'].get('intrinsic_value_per_share', 'N/A'):.2f}"
        upside = analysis['dcf_valuation'].get('upside_potential', 0)
        template_data['dcf_upside_value'] = f"{abs(upside):.2f}"
        template_data['dcf_upside_direction'] = "Upside" if upside > 0 else "Downside"
        template_data['dcf_upside_class'] = "positive" if upside > 0 else "negative"
    else:
        template_data['dcf_intrinsic_value'] = 'N/A'
        template_data['dcf_upside_value'] = 'N/A'
        template_data['dcf_upside_direction'] = 'N/A'
        template_data['dcf_upside_class'] = 'insufficient'
    
    # Graham Number
    if 'error' not in analysis['graham_valuation']:
        template_data['graham_number'] = f"{analysis['graham_valuation'].get('graham_number', 'N/A'):.2f}"
        upside = analysis['graham_valuation'].get('upside_potential', 0)
        template_data['graham_upside_value'] = f"{abs(upside):.2f}"
        template_data['graham_upside_direction'] = "Upside" if upside > 0 else "Downside"
        template_data['graham_upside_class'] = "positive" if upside > 0 else "negative"
    else:
        template_data['graham_number'] = 'N/A'
        template_data['graham_upside_value'] = 'N/A'
        template_data['graham_upside_direction'] = 'N/A'
        template_data['graham_upside_class'] = 'insufficient'
    
    # Buffett Approach
    if 'error' not in analysis['buffett_valuation']:
        template_data['buffett_intrinsic_value'] = f"{analysis['buffett_valuation'].get('intrinsic_value', 'N/A'):.2f}"
        upside = analysis['buffett_valuation'].get('upside_potential', 0)
        template_data['buffett_upside_value'] = f"{abs(upside):.2f}"
        template_data['buffett_upside_direction'] = "Upside" if upside > 0 else "Downside"
        template_data['buffett_upside_class'] = "positive" if upside > 0 else "negative"
    else:
        template_data['buffett_intrinsic_value'] = 'N/A'
        template_data['buffett_upside_value'] = 'N/A'
        template_data['buffett_upside_direction'] = 'N/A'
        template_data['buffett_upside_class'] = 'insufficient'
    
    # Chart path
    if 'error' not in analysis.get('historical_pe', {'error': 'No data'}):
        template_data['pe_chart_path'] = analysis['historical_pe'].get('plot_saved', '')
    else:
        template_data['pe_chart_path'] = ''
    
    # Render the template
    output = template.render(**template_data)
    
    # Write to file
    output_path = os.path.join(output_dir, f"{ticker}_report.html")
    with open(output_path, 'w') as f:
        f.write(output)
    
    return output_path

def get_recommendation_class(recommendation):
    """
    Get the CSS class for the recommendation.
    """
    if "STRONG BUY" in recommendation or "BUY" in recommendation:
        return "buy"
    elif "HOLD" in recommendation:
        return "hold"
    elif "AVOID" in recommendation:
        return "avoid"
    else:
        return "insufficient"

def main():
    parser = argparse.ArgumentParser(description='Generate HTML report for stock analysis')
    parser.add_argument('ticker', type=str, help='Stock ticker symbol')
    parser.add_argument('--output-dir', type=str, default='reports', help='Directory to save the report')
    
    args = parser.parse_args()
    
    print(f"Analyzing {args.ticker} and generating HTML report...")
    output_path = generate_html_report(args.ticker, args.output_dir)
    print(f"Report saved to {output_path}")

if __name__ == "__main__":
    main() 