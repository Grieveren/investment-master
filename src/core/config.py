"""
Configuration module for the portfolio analyzer.
"""

import os
import json
from src.core.logger import logger

def load_config(config_file='config.json'):
    """Load configuration from a JSON file.

    Args:
        config_file (str): Path to the configuration file.

    Returns:
        dict: Configuration dictionary.
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logger.info(f"Configuration loaded from {config_file}")
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file {config_file} not found. Using default configuration.")
        return get_default_config()
    except json.JSONDecodeError:
        logger.error(f"Error parsing configuration file {config_file}. Using default configuration.")
        return get_default_config()

def get_default_config():
    """Get default configuration.

    Returns:
        dict: Default configuration dictionary.
    """
    return {
        "api": {
            "sws_api_url": "https://api.simplywall.st/graphql",
            "portfolio_file": "combined_portfolio.md"
        },
        "retry": {
            "max_retries": 3,
            "retry_base_delay": 2,
            "retry_max_delay": 10
        },
        "openai": {
            "model": "o3-mini",
            "reasoning_effort": "high"
        },
        "output": {
            "raw_data_file": "data/raw/api_data.json",
            "analysis_file": "data/processed/portfolio_analysis.md"
        }
    }

# Load configuration
config = load_config() 