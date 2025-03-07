"""
Changelog utility to track project changes.

This module provides functions to create and update a CHANGELOG.md file
to track modifications made to the project.
"""

import os
import datetime
from utils.logger import logger

def add_changelog_entry(title, description, files_changed=None, tasks_completed=None, next_steps=None):
    """Add a new entry to the changelog.
    
    Args:
        title (str): Title/summary of the changes
        description (str): Detailed description of changes
        files_changed (list, optional): List of files that were modified
        tasks_completed (list, optional): List of tasks that were completed
        next_steps (list, optional): List of next steps or pending tasks
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get current date
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Create entry content
        entry = f"## {current_date}: {title}\n\n"
        
        # Add description
        entry += f"{description}\n\n"
        
        # Add files changed
        if files_changed:
            entry += "### Files Changed\n"
            for file in files_changed:
                entry += f"- `{file}`\n"
            entry += "\n"
        
        # Add tasks completed
        if tasks_completed:
            entry += "### Tasks Completed\n"
            for task in tasks_completed:
                entry += f"- {task}\n"
            entry += "\n"
        
        # Add next steps
        if next_steps:
            entry += "### Next Steps\n"
            for step in next_steps:
                entry += f"- [ ] {step}\n"
            entry += "\n"
        
        # Read existing changelog or create new one
        changelog_path = "CHANGELOG.md"
        
        if os.path.exists(changelog_path):
            with open(changelog_path, "r") as f:
                existing_content = f.read()
            
            # Check if this is the first entry
            if "# Changelog" in existing_content:
                # Add new entry after the title
                index = existing_content.find("# Changelog") + len("# Changelog")
                new_content = existing_content[:index] + "\n\n" + entry + existing_content[index:]
            else:
                # Just prepend the entry
                new_content = "# Changelog\n\n" + entry + existing_content
        else:
            new_content = "# Changelog\n\n" + entry
        
        # Write updated content
        with open(changelog_path, "w") as f:
            f.write(new_content)
        
        logger.info(f"Changelog updated with entry: {title}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating changelog: {e}")
        return False

def add_analysis_run_to_changelog(model, num_stocks, start_time, elapsed_time):
    """Add an analysis run to the changelog.
    
    Args:
        model (str): Model used for analysis
        num_stocks (int): Number of stocks analyzed
        start_time (datetime): When the analysis started
        elapsed_time (float): Total elapsed time in seconds
        
    Returns:
        bool: True if successful, False otherwise
    """
    model_name = "OpenAI o3-mini" if model == "o3-mini" else "Anthropic Claude"
    formatted_date = start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    title = f"Portfolio Analysis Run ({model_name})"
    description = f"""Ran portfolio analysis on {num_stocks} stocks using {model_name} model.
- Date: {formatted_date}
- Duration: {elapsed_time:.1f} seconds
- Output: data/processed/portfolio_analysis_{model.split('-')[0]}.md
- Company analyses: data/processed/companies/{model.split('-')[0]}/"""
    
    files_changed = [
        f"data/processed/portfolio_analysis_{model.split('-')[0]}.md",
        f"data/processed/companies/{model.split('-')[0]}/*.md"
    ]
    
    return add_changelog_entry(
        title=title,
        description=description,
        files_changed=files_changed
    ) 