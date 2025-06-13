#!/usr/bin/env python3
"""
Update Changelog CLI

A simple script to update the project changelog after a coding session.
This helps track progress and makes it easier to pick up where you left off.
"""

import sys
import argparse
from src.tools.changelog import add_changelog_entry

def main():
    """Main function to update the changelog."""
    parser = argparse.ArgumentParser(description="Update the project changelog")
    parser.add_argument("--title", "-t", type=str, required=True, help="Title/summary of the changes")
    parser.add_argument("--description", "-d", type=str, required=True, help="Detailed description of changes")
    parser.add_argument("--files", "-f", type=str, nargs="+", help="List of files that were modified")
    parser.add_argument("--tasks", "-c", type=str, nargs="+", help="List of tasks that were completed")
    parser.add_argument("--next", "-n", type=str, nargs="+", help="List of next steps or pending tasks")
    
    args = parser.parse_args()
    
    success = add_changelog_entry(
        title=args.title,
        description=args.description,
        files_changed=args.files,
        tasks_completed=args.tasks,
        next_steps=args.next
    )
    
    if success:
        print("Successfully updated CHANGELOG.md")
        sys.exit(0)
    else:
        print("Failed to update CHANGELOG.md", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main() 