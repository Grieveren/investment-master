# AI Agent Instructions

Use these instructions when launching a new AI agent to quickly get them up to speed on the Investment Master project:

## Initial Project Understanding

1. **Read key documentation first**:
   - Review the README.md to understand project purpose, structure, and functionality
   - Read the CHANGELOG.md to understand recent changes, particularly the modular testing scripts

2. **Examine critical code components**:
   - Review src/core/portfolio.py to understand stock mapping and portfolio handling
   - Examine src/tools/api.py to understand SimplyWall.st data fetching
   - Look at the scripts/ directory to understand modular testing workflow

3. **Understand the data flow**:
   - Trace how data moves from CSV import → API fetching → analysis → portfolio optimization
   - Check data/source and data/raw directories to understand input data formats

4. **Run diagnostic tests**:
   - Execute scripts/fetch_data_only.sh to verify API connectivity
   - Run tests/diagnostic/test_rheinmetall.py to understand the ticker mapping system

5. **Review recent issues**:
   - Note the recent fixes for Rheinmetall data fetching
   - Understand the virtual environment setup that resolved import path issues

This will give you a practical understanding of the codebase, recent changes, and how the system fits together before assisting with modifications. 