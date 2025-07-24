# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python utility for downloading research papers from arXiv with configuration support and rate limiting.

**Core Files:**

- `arxiv_downloader.py` - Main entry point with CLI
- `config.py` - Configuration management with dataclasses
- `arxiv_api.py` - ArXiv API client with type-safe paper representation
- `download_manager.py` - PDF download and metadata storage
- `requirements.txt` - Dependencies including PyYAML and type stubs

**Configuration Examples:**

- `config_daily_safe.yaml` - For daily cron jobs
- `config_backfill_safe.yaml` - For 24/7 backfill operations (1,800/day limit)
- `config_custom.yaml` - Example custom configurations

**Documentation:**

- `README.md` - Main documentation
- `CONFIGURATION.md` - Configuration guide and advanced usage
- `PACING_CALCULATIONS.md` - Rate limit calculations

## Key Commands

### Running the Script

```bash
# Install dependencies first
pip install -r requirements.txt

# Run with default configuration
python arxiv_downloader.py recent --days 7

# Run with specific configuration file
python arxiv_downloader.py --config config_daily.yaml job daily_recent
python arxiv_downloader.py --config config_backfill.yaml job historical_backfill

# Run specific commands
python arxiv_downloader.py category cs.AI --max 2000
python arxiv_downloader.py range 2024-01-01 2024-01-31 --categories cs.AI cs.LG
```

### Development Notes

- **No test suite**: This project has no tests
- **No linting configuration**: No linting rules are defined  
- **Dependencies**: PyYAML, requests, and type stubs (see requirements.txt)
- **Type hints**: v2 has comprehensive type annotations throughout
- **No build process**: Direct Python script execution

## Architecture

Modular architecture with separation of concerns:

1. **Configuration Module** (`config.py`)
   - Dataclass-based configuration with type safety
   - YAML file loading/saving
   - Supports multiple job definitions
   - Hierarchical configuration: download, directories, API, logging, jobs

2. **ArXiv API Module** (`arxiv_api.py`)
   - `ArxivPaper` dataclass for type-safe paper representation
   - `ArxivAPIClient` for API interactions
   - Rate limiting enforcement
   - XML parsing with error handling
   - Search, date range, and recent paper queries

3. **Download Manager** (`download_manager.py`)
   - `DownloadManager` handles PDF downloads and metadata storage
   - Retry logic with configurable attempts
   - Progress tracking and statistics
   - Atomic operations (metadata saved with PDF)

4. **Main Entry Point** (`arxiv_downloader.py`)
   - CLI with argparse
   - Support for --config parameter
   - Job execution from configuration
   - Backward-compatible commands

5. **File Organization**
   - Uses arXiv IDs directly: `YYMM.NNNNN` format
   - Example: `2401.00001.pdf` and `2401.00001.json`
   - Files naturally sort chronologically by submission order

## Important Implementation Details

- **Rate Limiting**: Always maintain 3-second delays between arXiv API requests (arxiv_downloader.py:27, 202-203)
- **Error Handling**: Failed downloads are logged but don't stop the process
- **Existing Files**: Script automatically skips files that already exist (arxiv_downloader.py:66-69)
- **API Limits**: Maximum 1000 papers per API call (arxiv_downloader.py:93)
- **Bulk Downloads**: Include 30-second pauses between months (arxiv_downloader.py:318)

## Common Development Tasks

When modifying this script:

1. Preserve the single-file architecture unless absolutely necessary
2. Maintain compatibility with the existing CLI interface
3. Respect arXiv's rate limiting requirements
4. Keep the simple directory structure (pdf/ and metadata/)
5. Use the existing logging setup for all output
