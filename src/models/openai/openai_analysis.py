"""
OpenAI-specific analysis module.

This module contains functions for analyzing financial data
using OpenAI models.
"""

from src.core.logger import logger
from src.core.config import config

def analyze_with_openai(system_prompt, user_prompt, client, model="o3-mini"):
    """Send analysis request to OpenAI.
    
    Args:
        system_prompt (str): System prompt with instructions
        user_prompt (str): User prompt with financial data
        client (OpenAI): OpenAI client
        model (str): OpenAI model to use
        
    Returns:
        str: Response text
    """
    # Add high-reasoning effort if configured
    reasoning_effort = "high" if config["openai"].get("reasoning_effort") == "high" else "auto"
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            reasoning_effort=reasoning_effort
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return f"Error: {e}" 