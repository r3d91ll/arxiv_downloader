# Migration Guide: ArXiv Downloader v2

This guide helps you migrate from the original `arxiv_downloader.py` to the new modular version with configuration support.

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

2. The new script is `arxiv_downloader_v2.py` (the original remains unchanged)

## Command Mapping

### Old Commands → New Commands

| Old Command | New Command |
|-------------|-------------|
| `python arxiv_downloader.py recent` | `python arxiv_downloader_v2.py recent` |
| `python arxiv_downloader.py recent --days 7` | `python arxiv_downloader_v2.py recent --days 7` |
| `python arxiv_downloader.py category cs.AI` | `python arxiv_downloader_v2.py category cs.AI` |
| `python arxiv_downloader.py range 2024-01-01 2024-01-31` | `python arxiv_downloader_v2.py range 2024-01-01 2024-01-31` |
| `python arxiv_downloader.py bulk --start-year 2020` | `python arxiv_downloader_v2.py bulk --start-year 2020` |
| `python arxiv_downloader.py stats` | `python arxiv_downloader_v2.py stats` |

### Using Configuration Files

Instead of command-line arguments, you can now use configuration files:

```bash
# Use daily configuration
python arxiv_downloader_v2.py --config config_daily.yaml job daily_recent

# Use backfill configuration
python arxiv_downloader_v2.py --config config_backfill.yaml job historical_backfill

# Use custom configuration
python arxiv_downloader_v2.py --config config_custom.yaml job nlp_transformers
```

## Setting Up Automated Jobs

### Daily Downloads (cron job example)

1. Create a cron job that runs at midnight GMT:
   ```bash
   0 0 * * * /usr/bin/python3 /path/to/arxiv_downloader_v2.py --config /path/to/config_daily.yaml job daily_recent
   ```

### Background Backfill

1. Use the backfill configuration to download historical papers:
   ```bash
   nohup python arxiv_downloader_v2.py --config config_backfill.yaml job historical_backfill &
   ```

## Configuration File Structure

Create your own configuration by copying one of the examples:

```yaml
download:
  rate_limit: 3.0  # Seconds between requests
  timeout: 30      # Request timeout
  max_retries: 3   # Retry attempts

directories:
  base_dir: "arxiv_papers"  # Same as before
  pdf_subdir: "pdf"
  metadata_subdir: "metadata"

logging:
  level: "INFO"
  file: "logs/downloader.log"  # Optional log file

jobs:
  my_job:
    enabled: true
    categories: ["cs.AI", "cs.LG"]
    date_range_days: 7  # Last 7 days
    max_papers_per_run: 1000
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
5. **Cleanup Command**: `python arxiv_downloader_v2.py cleanup` removes incomplete downloads

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

- The original script (`arxiv_downloader.py`) remains unchanged
- Both versions can coexist in the same directory
- Use `python arxiv_downloader_v2.py --help` for command help

## Example Workflows

### Daily Research Updates
```bash
# Download yesterday's AI papers
python arxiv_downloader_v2.py --config config_daily.yaml job daily_recent
```

### Building a Dataset
```bash
# Download all 2023 machine learning papers
python arxiv_downloader_v2.py range 2023-01-01 2023-12-31 --categories cs.LG stat.ML --max 50000
```

### Custom Search
```yaml
# In your config file
jobs:
  transformer_papers:
    enabled: true
    custom_query: 'all:transformer AND (cat:cs.CL OR cat:cs.LG)'
    max_papers_per_run: 5000
```

Then run:
```bash
python arxiv_downloader_v2.py --config my_config.yaml job transformer_papers
```