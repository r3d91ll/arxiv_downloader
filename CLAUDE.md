# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ArXiv PDF Downloader - A Python utility for downloading research papers from arXiv with rate limiting, configuration support, and organized storage.

**Core Architecture:**

The project follows a modular architecture with clear separation of concerns:

1. **Configuration Layer** (`config.py`) - Dataclass-based configuration with YAML support
2. **API Client** (`arxiv_api.py`) - Handles all arXiv API interactions with rate limiting
3. **Download Manager** (`download_manager.py`) - Manages PDF downloads and metadata storage
4. **CLI Interface** (`arxiv_downloader.py`) - Main entry point with command support
5. **Utilities** - Helper scripts for specific workflows (gap finding, backfilling, etc.)

## Key Commands

### Installation and Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Downloader

```bash
# Basic usage - download recent papers
python arxiv_downloader.py recent --days 7

# Using configuration files (recommended)
python arxiv_downloader.py --config config_daily.yaml job daily_recent
python arxiv_downloader.py --config config_backfill.yaml job historical_backfill

# Direct commands
python arxiv_downloader.py category cs.AI --max 1000
python arxiv_downloader.py range 2024-01-01 2024-01-31 --categories cs.AI cs.LG
python arxiv_downloader.py bulk --start-year 2020 --categories cs.AI

# Utility scripts
python find_download_gap.py  # Check how many papers behind current submissions
python reverse_backfill.py   # Backfill from recent to old papers
```

### Development Commands

```bash
# No test suite exists - manual testing required
# No linting configuration - code style follows PEP 8 conventions
# Type checking can be done manually with mypy (not configured)
```

## Architecture Details

### Configuration System (`config.py`)

- Uses dataclasses for type-safe configuration
- Hierarchical structure: download settings, directories, API config, logging, jobs
- YAML file support with validation
- Job definitions for automated/scheduled downloads

### API Client (`arxiv_api.py`)

- `ArxivPaper` dataclass represents paper metadata
- `ArxivAPIClient` handles all API interactions
- Enforces 3-second rate limiting between requests
- XML parsing with comprehensive error handling
- Supports search queries, date ranges, and category filtering

### Download Manager (`download_manager.py`)

- Atomic operations (metadata saved only with successful PDF download)
- Configurable retry logic with exponential backoff
- Progress tracking and statistics
- Automatic skip of existing files
- Batch processing with configurable pauses

### File Organization

- Files use arXiv ID format: `YYMM.NNNNN` (e.g., `2401.00001.pdf`)
- Natural chronological ordering by submission
- Parallel structure: `pdf/` and `metadata/` directories
- Matching names for easy correlation

## Critical Implementation Details

### Rate Limiting and Pacing

- **API Rate Limit**: 3-second minimum delay between arXiv API requests (hardcoded)
- **Download Rate Limit**: Configurable via `download.rate_limit` (default 3.0 seconds)
- **Batch Processing**: Pause after N downloads (`batch_size` and `batch_pause`)
- **Session Pauses**: Longer pause after many downloads (`session_pause_after`)
- **Monthly Pause**: 30-second pause between processing different months in bulk downloads

### Error Handling

- Failed downloads are logged but don't stop the process
- Retry logic with exponential backoff for transient failures
- Comprehensive logging for debugging
- Graceful handling of missing or malformed data

### Configuration Files

Multiple pre-configured YAML files for different use cases:
- `config_daily_safe.yaml` - Conservative daily downloads
- `config_backfill_safe.yaml` - 24/7 backfilling within rate limits
- `config_daily_1800.yaml` - Optimized for 1,800 papers/day limit
- Various year-specific backfill configs

### Utility Scripts

- `find_download_gap.py` - Analyzes gap between local papers and current submissions
- `reverse_backfill.py` - Downloads papers from newest to oldest
- `daily_1800_strategy.py` - Implements specific pacing strategy
- Shell scripts for cron job automation

## Important Notes

- **No Test Suite**: This project has no automated tests
- **No Linting**: No formal linting configuration (follows PEP 8 informally)
- **Type Annotations**: Comprehensive type hints throughout v2 codebase
- **API Limits**: Maximum 1000 results per API query
- **Daily Limits**: Some configs enforce daily download limits (e.g., 1,800/day)
- **File Naming**: Uses direct arXiv IDs - no sanitization needed for filenames