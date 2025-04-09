# Changelog

## 2025-03-31: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 11 stocks using Anthropic Claude model.
- Date: 2025-03-31 20:29:43
- Duration: 766.4 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`



## 2025-03-23: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 11 stocks using Anthropic Claude model.
- Date: 2025-03-23 17:47:02
- Duration: 746.8 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`



## 2025-03-23: Extended Ticker Mapping and Added Regression Tests

Extended the ticker mapping system:
- Added direct ticker symbol lookups for all supported companies 
- Created regression tests to prevent future mapping issues
- Improved modularity with comprehensive test coverage

## 2025-03-23: Fixed TSM Ticker Mapping

Fixed an issue with Taiwan Semiconductor (TSM) ticker not being properly recognized in the portfolio analyzer.
- Added multiple mapping entries for TSM with different naming variations
- Added test cases to verify the fix works correctly
- Documented the mapping approach in the code

## 2025-03-23: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 11 stocks using Anthropic Claude model.
- Date: 2025-03-23 11:30:27
- Duration: 762.9 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`



## 2025-03-22: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 11 stocks using Anthropic Claude model.
- Date: 2025-03-22 19:56:15
- Duration: 673.1 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`



## 2025-03-22: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 11 stocks using Anthropic Claude model.
- Date: 2025-03-22 19:31:00
- Duration: 691.1 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`



## 2025-03-22: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 11 stocks using Anthropic Claude model.
- Date: 2025-03-22 19:26:35
- Duration: 742.1 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`



## 2025-03-22: Portfolio Analysis Run (OpenAI o3-mini)

Ran portfolio analysis on 3 stocks using OpenAI o3-mini model.
- Date: 2025-03-22 18:28:30
- Duration: 104.0 seconds
- Output: data/processed/portfolio_analysis_o3.md
- Company analyses: data/processed/companies/o3/

### Files Changed
- `data/processed/portfolio_analysis_o3.md`
- `data/processed/companies/o3/*.md`



## 2025-03-22: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 3 stocks using Anthropic Claude model.
- Date: 2025-03-22 18:25:23
- Duration: 186.4 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`



## 2025-03-22: Portfolio Analysis Run (OpenAI o3-mini)

Ran portfolio analysis on 3 stocks using OpenAI o3-mini model.
- Date: 2025-03-22 18:24:45
- Duration: 76.6 seconds
- Output: data/processed/portfolio_analysis_o3.md
- Company analyses: data/processed/companies/o3/

### Files Changed
- `data/processed/portfolio_analysis_o3.md`
- `data/processed/companies/o3/*.md`



## 2025-03-22: Portfolio Analysis Run (OpenAI o3-mini)

Ran portfolio analysis on 3 stocks using OpenAI o3-mini model.
- Date: 2025-03-22 18:18:20
- Duration: 73.0 seconds
- Output: data/processed/portfolio_analysis_o3.md
- Company analyses: data/processed/companies/o3/

### Files Changed
- `data/processed/portfolio_analysis_o3.md`
- `data/processed/companies/o3/*.md`



## 2025-03-22: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 3 stocks using Anthropic Claude model.
- Date: 2025-03-22 17:02:39
- Duration: 210.9 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`



## 2025-03-22: Portfolio Analysis Run (Anthropic Claude)

Ran portfolio analysis on 11 stocks using Anthropic Claude model.
- Date: 2025-03-22 07:50:34
- Duration: 768.1 seconds
- Output: data/processed/portfolio_analysis_claude.md
- Company analyses: data/processed/companies/claude/

### Files Changed
- `data/processed/portfolio_analysis_claude.md`
- `data/processed/companies/claude/*.md`

## 2025-03-22: Project Restructuring

### Description
Reorganized the project structure to follow a more modular and maintainable architecture. Created a clear separation between core components, models, tools, and scripts.

### Files Changed
- Multiple files moved to new directory structure
- All import statements updated to reflect new module paths
- Shell script updated to use new script paths

### Tasks Completed
- Created `src` directory with subdirectories for core, models, tools, and scripts
- Moved all utility modules to appropriate subdirectories
- Updated all import statements to use the new module paths
- Updated the run_portfolio_analysis.sh script to use the new script paths

### Next Steps
- Test the full analysis pipeline with the new structure
- Consider additional improvements to the module organization
- Update documentation to reflect the new structure

