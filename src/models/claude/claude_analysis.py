"""
Claude-specific analysis module.

This module contains functions for analyzing financial data
using Anthropic's Claude models.
"""

import time as _time
from src.core.logger import logger as _logger
from src.core.config import config as _config

def _get_system_prompt():
    """Get the system prompt for Claude analysis.
    
    This function is private and only used within this module.
    
    Returns:
        str: System prompt for Claude
    """
    return """You are a value investing expert with deep knowledge of financial analysis, following principles of Warren Buffett and Benjamin Graham.

You have been given extended thinking time to perform an exceptionally thorough analysis of a company. Use this time to:

1. Carefully examine all financial statements and metrics provided
2. Calculate intrinsic value using multiple approaches (DCF, multiples, etc.)
3. Assess competitive advantages and durability of the business model
4. Evaluate management quality and capital allocation decisions
5. Consider industry dynamics, competitive threats, and macroeconomic factors
6. Identify potential catalysts and risks not explicitly mentioned in the data
7. Calculate a reasonable margin of safety based on risk factors

You will produce a detailed value investing analysis report with the following structure:

# [Company Name] ([Ticker])

## Recommendation
[Clearly state BUY, SELL, or HOLD here - this must be one of these three words]

## Summary
[One paragraph summary of the company and your analysis]

## Strengths
- [Strength 1]
- [Strength 2]
- [Additional strengths...]

## Weaknesses
- [Weakness 1]
- [Weakness 2]
- [Additional weaknesses...]

## Competitive Analysis
[One paragraph assessment of the company's competitive position and moat]

## Management Assessment
[One paragraph evaluation of management quality and capital allocation]

## Financial Health
[Analysis of balance sheet, cash flow, and financial stability]

## Growth Prospects
[Analysis of growth drivers, market opportunities, and threats]

## Price Analysis
Current Price: $[current price - ALWAYS include this exactly as provided in the data]
Intrinsic Value: $[your estimated fair value]
Margin of Safety: [percentage]%
Valuation Method(s): [Brief description of valuation method(s) used]

## Investment Rationale
[Detailed explanation of your recommendation, focusing on value investing principles]

## Risk Factors
[List and analysis of key risks that could impact the investment thesis]

IMPORTANT: Always include the Current Price in your Price Analysis section, exactly as provided in the data. If no price is available, clearly state "Price data not available". The current price is a critical data point for any investment analysis.

This format will be used to guide investment decisions, so be thorough and objective. This is an enhanced analysis using comprehensive data, so provide detailed insights beyond a typical stock report.
"""

def analyze_with_claude(user_prompt, client, model="claude-3-7-sonnet-20250219"):
    """Use Anthropic's Claude model to analyze financial data.
    
    Args:
        user_prompt (str): The prompt to send to Claude.
        client (Anthropic): Anthropic client instance.
        model (str, optional): Claude model to use. Defaults to "claude-3-7-sonnet-20250219".
        
    Returns:
        str: Text response from Claude.
    """
    try:
        thinking_budget = _config["claude"].get("thinking_budget", 32000)
        
        # Get system prompt from private function
        system_prompt = _get_system_prompt()
        
        _logger.info(f"Requesting detailed company analysis from Claude ({model}) with {thinking_budget} token thinking budget...")
        print(f"Starting analysis with {thinking_budget} token thinking budget...")
        print("This will take some time. Progress will be shown as Claude processes the data...")
        
        start_time = _time.time()
        
        # Variables to track streaming progress - scoped only to this function
        full_response = ""
        current_thinking = ""
        current_text = ""
        thinking_in_progress = False
        text_in_progress = False
        thinking_chunks = 0
        text_chunks = 0
        last_progress_time = _time.time()
        progress_interval = 5  # Show progress every 5 seconds
        
        # Use streaming to get the response
        with client.messages.stream(
            model=model,
            max_tokens=thinking_budget + 10000,  # Increased output tokens for more comprehensive analysis
            thinking={"type": "enabled", "budget_tokens": thinking_budget},
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
            temperature=1.0  # Must be 1.0 when thinking is enabled
        ) as stream:
            # Display initial progress message
            print("Claude's thinking process has started...")
            
            # Process the streaming events
            for event in stream:
                current_time = _time.time()
                
                # Handle message start
                if event.type == "message_start":
                    pass
                
                # Handle content block start
                elif event.type == "content_block_start":
                    if event.content_block.type == "thinking":
                        thinking_in_progress = True
                        text_in_progress = False
                        thinking_chunks = 0
                        if current_time - last_progress_time > progress_interval:
                            print("Claude is analyzing the company data...")
                            last_progress_time = current_time
                    elif event.content_block.type == "text":
                        text_in_progress = True
                        thinking_in_progress = False
                        text_chunks = 0
                        print("\nAnalysis complete! Claude is now generating the report...")
                
                # Handle content block delta (the actual content chunks)
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "thinking") and thinking_in_progress:
                        thinking_chunk = event.delta.thinking
                        current_thinking += thinking_chunk
                        thinking_chunks += 1
                        # Periodically show progress for thinking
                        if current_time - last_progress_time > progress_interval:
                            elapsed = current_time - start_time
                            print(f"Still thinking... ({elapsed:.1f}s elapsed, {thinking_chunks} thinking chunks processed)")
                            last_progress_time = current_time
                    elif hasattr(event.delta, "text") and text_in_progress:
                        text_chunk = event.delta.text
                        current_text += text_chunk
                        text_chunks += 1
                        # Show progress for text generation
                        if text_chunks % 20 == 0:  # Show more frequent updates for text
                            progress_char = "." * (text_chunks // 20 % 4 + 1)
                            print(f"Generating report{progress_char}", end="\r")
                
                # Handle content block stop
                elif event.type == "content_block_stop":
                    if thinking_in_progress:
                        thinking_in_progress = False
                        _logger.info(f"Thinking complete: {len(current_thinking)} characters in {thinking_chunks} chunks")
                    elif text_in_progress:
                        text_in_progress = False
                        _logger.info(f"Text complete: {len(current_text)} characters in {text_chunks} chunks")
                
                # Handle message delta
                elif event.type == "message_delta":
                    if event.delta.stop_reason:
                        _logger.info(f"Message stopped with reason: {event.delta.stop_reason}")
                
                # Handle message stop (end of stream)
                elif event.type == "message_stop":
                    full_response = current_text
                    _logger.info("Streaming complete")
        
        elapsed_time = _time.time() - start_time
        _logger.info(f"Claude company analysis completed in {elapsed_time:.1f}s")
        print(f"\nCompany analysis complete! (took {elapsed_time:.1f} seconds)")
        
        return full_response
        
    except Exception as e:
        _logger.error(f"Error calling Claude API: {e}")
        return f"Error: {e}" 