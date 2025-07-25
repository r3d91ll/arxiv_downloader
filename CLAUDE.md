# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ArXiv PDF Downloader - A comprehensive system for harvesting arXiv paper metadata and selectively downloading PDFs with intelligent rate limiting and organization.

**New Metadata-First Architecture:**

The project now implements a two-phase approach:

1. **Metadata Harvesting** - Lightweight collection of all paper information
2. **PDF Downloading** - Selective retrieval based on metadata with daily limits

## Core Architecture

The project follows a modular architecture with clear separation of concerns:

1. **Configuration Layer** (`config.py`) - Dataclass-based configuration with YAML support
2. **API Client** (`arxiv_api.py`) - Handles all arXiv API interactions with rate limiting
3. **Download Manager** (`download_manager.py`) - Manages PDF downloads with retry logic
4. **Metadata Harvester** (`metadata_harvester.py`) - Collects paper metadata without PDFs
5. **PDF Downloader** (`pdf_downloader.py`) - Downloads PDFs based on existing metadata
6. **CLI Interface** (`arxiv_downloader.py`) - Original combined downloader
7. **Utilities** - Helper scripts for gap analysis and other workflows

## Key Commands

### Installation and Setup

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Metadata Harvesting (New Approach)

```bash
# Harvest recent metadata
python metadata_harvester.py --config config_master.yaml --days-back 7

# Harvest date range
python metadata_harvester.py --config config_master.yaml \
    --start-date 2024-01-01 --end-date 2024-12-31

# Filter by categories
python metadata_harvester.py --config config_master.yaml \
    --categories cs.AI cs.LG --days-back 30

# Continuous mode
python metadata_harvester.py --config config_master.yaml --continuous
```

### PDF Downloading (Respects Daily Limits)

```bash
# Download up to 1,800 PDFs daily
python pdf_downloader.py --config config_master.yaml --limit 1800

# Priority modes: newest, oldest, random
python pdf_downloader.py --config config_master.yaml \
    --limit 1800 --priority oldest

# Category filtering
python pdf_downloader.py --config config_master.yaml \
    --limit 1800 --categories cs.AI cs.LG
```

### Original Combined Downloader

```bash
# Still available for direct PDF+metadata downloads
python arxiv_downloader.py recent --days 7
python arxiv_downloader.py category cs.AI --max 1000
python arxiv_downloader.py range 2024-01-01 2024-01-31
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
- Hierarchical structure: download settings, directories, API config, logging
- Master config at `config_master.yaml` with `/mnt/data/arxiv_data` as base
- Old configs archived in `config_archive/` directory

### API Client (`arxiv_api.py`)

- `ArxivPaper` dataclass represents paper metadata
- `ArxivAPIClient` handles all API interactions
- Enforces 3-second rate limiting between requests
- XML parsing with comprehensive error handling
- Supports search queries, date ranges, and category filtering
- Missing optional fields: DOI, journal_ref, comment, primary_category (TODO)

### Metadata Harvester (`metadata_harvester.py`)

- Saves individual JSON files per paper
- Progress tracking with resume capability
- Handles date ranges intelligently (avoids future dates)
- Updates count more frequently for better feedback
- Tracks both new and existing metadata
- Saves to configured metadata directory

### PDF Downloader (`pdf_downloader.py`)

- Works with existing metadata files
- Tracks daily download count (resets each day)
- Updates metadata when PDF downloaded
- Supports priority modes: newest, oldest, random
- Category filtering capability
- Respects all rate limits and pauses

### Download Manager (`download_manager.py`)

- Handles actual PDF downloads with retry logic
- Configurable retry with exponential backoff
- Progress tracking and statistics
- Automatic skip of existing files
- Batch processing with configurable pauses

### File Organization

- Metadata files: `/mnt/data/arxiv_data/metadata/YYMM.NNNNN.json`
- PDF files: `/mnt/data/arxiv_data/pdf/YYMM.NNNNN.pdf`
- Progress tracking: `harvest_progress.json`, `pdf_daily_count.json`
- Natural chronological ordering by submission

## Critical Implementation Details

### Rate Limiting and Pacing

- **API Rate Limit**: 3-second minimum delay between arXiv API requests (hardcoded)
- **Download Rate Limit**: Configurable via `download.rate_limit` (default 3.0 seconds)
- **Batch Processing**: Pause after N downloads (`batch_size` and `batch_pause`)
- **Session Pauses**: Longer pause after many downloads (`session_pause_after`)
- **Daily Limits**: PDF downloader respects configurable daily limits (e.g., 1,800)

### Error Handling

- Failed operations are logged but don't stop the process
- Retry logic with exponential backoff for transient failures
- Comprehensive logging for debugging
- Graceful handling of missing or malformed data
- Date logic prevents attempting to harvest future papers

### Metadata Format

Each JSON file contains:

- Core fields: arxiv_id, title, authors, abstract, categories
- Dates: published, updated, harvested_at
- URLs: pdf_url, abs_url
- Download tracking: pdf_downloaded, pdf_downloaded_at
- Missing: DOI, journal_ref, comment, primary_category (planned enhancement)

### Directory Management

- Archived old scripts in `old_scripts/`
- Archived old configs in `config_archive/`
- Clean project structure with only essential files
- Master config at `config_master.yaml`

## Important Notes

- **No Test Suite**: This project has no automated tests
- **No Linting**: No formal linting configuration (follows PEP 8 informally)
- **Type Annotations**: Comprehensive type hints throughout codebase
- **API Limits**: Maximum 1000 results per API query
- **Daily Limits**: PDF downloader enforces daily download limits
- **File Naming**: Uses direct arXiv IDs - no sanitization needed
- **Storage Path**: Default to `/mnt/data/arxiv_data/` (configurable)

## Future Enhancements

1. Add missing metadata fields (DOI, journal_ref, comment, primary_category)
2. Consider OAI-PMH protocol for more efficient bulk harvesting
3. Add arXiv acknowledgment statement as recommended
4. Implement database backend option for metadata storage
5. Add full-text search capabilities across abstracts
