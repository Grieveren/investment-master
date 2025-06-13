"""
Client creation module for AI model APIs.

This module provides functions to create OpenAI and Anthropic clients
with proper error handling and configuration.
"""

import os as _os
from src.core.logger import logger as _logger

def create_openai_client(api_key):
    """Create an OpenAI client.

    Args:
        api_key (str): OpenAI API key.

    Returns:
        OpenAI: OpenAI client, or None if creation failed.
    """
    try:
        from openai import OpenAI
        
        if not api_key or api_key.startswith("your_"):
            _logger.warning("Invalid OpenAI API key. Analysis will not be available.")
            return None
        
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        _logger.error(f"Error creating OpenAI client: {e}")
        return None

def create_anthropic_client(api_key=None):
    """Create an Anthropic Claude client.
    
    Args:
        api_key (str, optional): Anthropic API key. If None, will use the ANTHROPIC_API_KEY from environment.
    
    Returns:
        Anthropic: Anthropic client, or None if creation failed.
    """
    # Check if Anthropic is available - moved inside function to minimize scope
    try:
        import anthropic
        anthropic_available = True
    except ImportError:
        anthropic_available = False
        
    if not anthropic_available:
        _logger.error("Anthropic package not installed. Please install with 'pip install anthropic'")
        return None
        
    try:
        if not api_key:
            api_key = _os.getenv("ANTHROPIC_API_KEY")
            
        if not api_key or api_key.startswith("your_"):
            _logger.warning("Invalid Anthropic API key. Claude analysis will not be available.")
            return None
        
        client = anthropic.Anthropic(api_key=api_key)
        return client
    except Exception as e:
        _logger.error(f"Error creating Anthropic client: {e}")
        return None 