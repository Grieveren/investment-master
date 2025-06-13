"""
File operations module for saving and loading data.
"""

import os
import json
from src.core.logger import logger

def save_json_data(data, filepath):
    """Save data to a JSON file.

    Args:
        data (dict): Data to save.
        filepath (str): Path to the file.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Data saved to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving data to {filepath}: {e}")
        return False

def load_json_data(filepath):
    """Load data from a JSON file.

    Args:
        filepath (str): Path to the file.

    Returns:
        dict: Loaded data, or None if loading failed.
    """
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
        logger.info(f"Data loaded from {filepath}")
        return data
    except FileNotFoundError:
        logger.error(f"File {filepath} not found.")
        return None
    except json.JSONDecodeError:
        logger.error(f"Error parsing JSON in {filepath}.")
        return None
    except Exception as e:
        logger.error(f"Error loading data from {filepath}: {e}")
        return None

def save_markdown(markdown_content, filepath):
    """Save markdown content to a file.

    Args:
        markdown_content (str): Markdown content to save.
        filepath (str): Path to the file.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "w") as f:
            f.write(markdown_content)
        logger.info(f"Markdown saved to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Error saving markdown to {filepath}: {e}")
        return False 