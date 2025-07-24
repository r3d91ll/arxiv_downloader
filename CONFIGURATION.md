# Configuration Guide: ArXiv Downloader

This guide explains how to use the configuration system and advanced features of the ArXiv downloader.

## What's New

1. **Configuration Files**: Settings are now managed via YAML files instead of command-line arguments
2. **Modular Architecture**: Code is split into focused modules for better maintainability
3. **Full Type Safety**: All code now has comprehensive type hints
4. **Job Support**: Define reusable download jobs in configuration files
5. **Better Error Handling**: Improved retry logic and error reporting

## Installation

1. Install the new dependencies:
   ```bash
   pip install -r requirements.txt
   ```


## Command Mapping


### Basic Commands

| Command | Description |
|---------|-------------|
| `python arxiv_downloader.py recent` | Download recent papers (last day) |
| `python arxiv_downloader.py recent --days 7` | Download papers from last 7 days |
| `python arxiv_downloader.py category cs.AI` | Download papers from a category |
| `python arxiv_downloader.py range 2024-01-01 2024-01-31` | Download date range |
| `python arxiv_downloader.py bulk --start-year 2020` | Bulk download by year |
| `python arxiv_downloader.py stats` | Show download statistics |

### Using Configuration Files

Instead of command-line arguments, you can now use configuration files:

```bash
# Use daily configuration
python arxiv_downloader.py --config config_daily.yaml job daily_recent

# Use backfill configuration
python arxiv_downloader.py --config config_backfill.yaml job historical_backfill

# Use custom configuration
python arxiv_downloader.py --config config_custom.yaml job nlp_transformers
```

## Setting Up Automated Jobs

### Daily Downloads (cron job example)

1. Create a cron job that runs at midnight GMT:
   ```bash
   0 0 * * * /usr/bin/python3 /path/to/arxiv_downloader.py --config /path/to/config_daily.yaml job daily_recent
   ```

### Background Backfill

1. Use the backfill configuration to download historical papers:
   ```bash
   nohup python arxiv_downloader.py --config config_backfill.yaml job historical_backfill &
   ```

## Configuration File Structure

Create your own configuration by copying one of the examples:

```yaml
download:
  rate_limit: 3.0  # REQUIRED - Seconds between requests (minimum 3.0 for arXiv)
  timeout: 30      # OPTIONAL - Request timeout in seconds (default: 30)
  max_retries: 3   # OPTIONAL - Retry attempts for failed downloads (default: 3)
  chunk_size: 8192 # OPTIONAL - Download chunk size in bytes (default: 8192)
  retry_delay: 5.0 # OPTIONAL - Delay between retries in seconds (default: 5.0)
  
  # Pacing controls (all OPTIONAL)
  batch_size: 10   # OPTIONAL - Papers per batch before pause (default: None)
  batch_pause: 10.0 # OPTIONAL - Pause between batches in seconds (default: None)
  daily_limit: 1800 # OPTIONAL - Maximum downloads per day (default: None)

directories:
  base_dir: "arxiv_papers"  # REQUIRED - Base directory for downloads
  pdf_subdir: "pdf"         # OPTIONAL - Subdirectory for PDFs (default: "pdf")
  metadata_subdir: "metadata"  # OPTIONAL - Subdirectory for metadata (default: "metadata")

api:
  base_url: "http://export.arxiv.org/api/query"  # OPTIONAL - ArXiv API URL (default shown)
  max_results_per_query: 500  # OPTIONAL - Max results per API call (default: 1000, max: 1000)
  default_sort_by: "submittedDate"  # OPTIONAL - Default sort field (default: "submittedDate")
  default_sort_order: "descending"  # OPTIONAL - Sort order (default: "descending")

logging:
  level: "INFO"    # OPTIONAL - Log level (default: "INFO")
  format: "%(asctime)s - %(levelname)s - %(message)s"  # OPTIONAL - Log format
  file: "logs/downloader.log"  # OPTIONAL - Log file path (default: None, logs to console only)

jobs:
  my_job:          # Job name (user-defined)
    enabled: true  # OPTIONAL - Whether to run this job (default: true)
    categories: ["cs.AI", "cs.LG"]  # OPTIONAL - ArXiv categories to filter
    
    # Job type (REQUIRED: exactly one of these must be specified)
    date_range_days: 7  # Option 1: Download papers from last N days
    # OR
    # custom_query: 'all:transformer'  # Option 2: Custom arXiv query
    # OR  
    # start_date: "2024-01-01"  # Option 3: Date range (both required)
    # end_date: "2024-01-31"
    # OR
    # bulk_start_year: 2020  # Option 4: Bulk download from year
    
    max_papers_per_run: 1000  # OPTIONAL - Maximum papers per job run
    bulk_max_per_month: 500   # OPTIONAL - For bulk downloads only
```

## Data Compatibility

- The new version uses the same directory structure (`arxiv_papers/pdf/` and `arxiv_papers/metadata/`)
- File naming remains the same (`{arxiv_id}.pdf` and `{arxiv_id}.json`)
- Existing downloads will be recognized and skipped

## Duplicate Prevention

The system has multiple safeguards against downloading duplicates:

1. **File Existence Check**: Before downloading, checks if both PDF and metadata exist
2. **Skip Counting**: Tracks how many files were skipped in statistics
3. **Daily Limit Awareness**: Only counts NEW downloads toward daily limit
4. **Atomic Operations**: Downloads metadata and PDF together; removes orphans if one fails
5. **Cleanup Command**: `python arxiv_downloader.py cleanup` removes incomplete downloads

### How It Works:

- If both `{arxiv_id}.pdf` and `{arxiv_id}.json` exist → Skip download
- If only metadata exists → Download PDF only
- If only PDF exists → Re-download both (rare case, usually indicates corruption)
- If download fails → Remove any partial files

This ensures you can safely restart the script anytime without re-downloading existing papers.

## Advantages of the New Version

1. **Flexibility**: Different configurations for different use cases
2. **Maintainability**: Modular code is easier to extend and debug
3. **Type Safety**: Catch errors before runtime with proper type hints
4. **Logging**: Better logging with configurable output files
5. **Job Management**: Define and run specific download jobs

## Getting Help

- Use `python arxiv_downloader.py --help` for command help

## Example Workflows

### Daily Research Updates
```bash
# Download yesterday's AI papers
python arxiv_downloader.py --config config_daily.yaml job daily_recent
```

### Building a Dataset
```bash
# Download all 2023 machine learning papers
python arxiv_downloader.py range 2023-01-01 2023-12-31 --categories cs.LG stat.ML --max 50000
```

### Custom Search
```yaml
# In your config file
jobs:
  transformer_papers:
    enabled: true  # OPTIONAL - Whether to run this job (default: true)
    custom_query: 'all:transformer AND (cat:cs.CL OR cat:cs.LG)'  # REQUIRED for custom query jobs
    max_papers_per_run: 5000  # OPTIONAL - Maximum papers to download
```

Then run:
```bash
python arxiv_downloader.py --config my_config.yaml job transformer_papers
```