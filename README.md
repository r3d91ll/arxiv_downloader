# ArXiv PDF Downloader

A comprehensive utility for downloading research papers from arXiv with metadata harvesting and intelligent PDF retrieval. The system uses a two-phase approach: first collecting all metadata, then selectively downloading PDFs based on your requirements.

## New: Metadata-First Architecture

The project now implements a metadata-first strategy that separates lightweight metadata collection from bandwidth-intensive PDF downloads. This allows you to:

- 📊 Harvest complete paper metadata without downloading PDFs
- 🎯 Selectively download PDFs based on categories, dates, or priorities
- 📈 Maintain a searchable database of all arXiv papers
- 🚀 Respect daily download limits while maximizing data collection

## Features

- 📄 **Two-Phase System**: Separate metadata harvesting and PDF downloading
- 📊 **Complete Metadata**: Titles, authors, abstracts, categories, dates
- 🗂️ **Smart Organization**: Files use arXiv ID format (YYMM.NNNNN)
- ⏰ **Chronological Order**: Natural timeline organization
- 🛡️ **Rate Limiting**: Respects arXiv's API guidelines
- 📈 **Progress Tracking**: Resume interrupted operations
- 🎯 **Daily Limits**: Configurable PDF download limits (e.g., 1,800/day)

## Directory Structure

```
/mnt/data/arxiv_data/        # Or your configured directory
├── metadata/
│   ├── 2401.00001.json     # Paper metadata
│   ├── 2401.00002.json
│   └── ...
├── pdf/
│   ├── 2401.00001.pdf      # PDF files (when downloaded)
│   ├── 2401.00002.pdf
│   └── ...
├── harvest_progress.json    # Metadata collection progress
└── pdf_daily_count.json     # Daily PDF download tracking
```

## Installation

```bash
# Clone the repository
git clone https://github.com/r3d91ll/arxiv_downloader.git
cd arxiv_downloader

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

### Step 1: Harvest Metadata

```bash
# Harvest metadata from the last 7 days
python metadata_harvester.py --config config_master.yaml --days-back 7

# Harvest specific date range
python metadata_harvester.py --config config_master.yaml \
    --start-date 2024-01-01 --end-date 2024-12-31

# Harvest specific categories
python metadata_harvester.py --config config_master.yaml \
    --categories cs.AI cs.LG --days-back 30

# Continuous harvesting (checks for new papers hourly)
python metadata_harvester.py --config config_master.yaml --continuous
```

### Step 2: Download PDFs

```bash
# Download up to 1,800 PDFs (newest first)
python pdf_downloader.py --config config_master.yaml --limit 1800

# Download oldest papers first
python pdf_downloader.py --config config_master.yaml \
    --limit 1800 --priority oldest

# Download only AI/ML papers
python pdf_downloader.py --config config_master.yaml \
    --limit 1800 --categories cs.AI cs.LG

# Test with small batch
python pdf_downloader.py --config config_master.yaml --limit 10
```

## Configuration

The master configuration file (`config_master.yaml`) controls all settings:

```yaml
directories:
  base_dir: "/mnt/data/arxiv_data"  # Change to your preferred location
  pdf_subdir: "pdf"
  metadata_subdir: "metadata"

download:
  rate_limit: 3.0          # Seconds between PDF downloads
  timeout: 300             # Download timeout in seconds
  batch_size: 100          # Pause after this many downloads
  batch_pause: 30          # Pause duration in seconds
  daily_limit: null        # Set to 1800 or other limit

api:
  base_url: "http://export.arxiv.org/api/query"
  max_results_per_query: 1000
```

## Usage Details

### Metadata Harvester

The metadata harvester efficiently collects paper information without downloading PDFs:

```bash
python metadata_harvester.py [options]

Options:
  --config FILE           Configuration file path
  --start-date DATE       Start date (YYYY-MM-DD)
  --end-date DATE         End date (YYYY-MM-DD)
  --days-back N          Number of days to look back
  --continuous           Run continuously, checking for new papers
  --check-interval SEC   Seconds between checks in continuous mode
  --categories CAT...    Filter by categories (e.g., cs.AI cs.LG)
```

Features:
- Respects 3-second API rate limit
- Saves progress for resuming
- Skips already harvested papers
- Logs detailed statistics

### PDF Downloader

The PDF downloader works with existing metadata to download papers intelligently:

```bash
python pdf_downloader.py [options]

Options:
  --config FILE          Configuration file path
  --limit N             Daily download limit (default: 1800)
  --priority MODE       Download priority: newest, oldest, random
  --categories CAT...   Only download from specific categories
```

Features:
- Tracks daily download count (resets each day)
- Updates metadata when PDF is downloaded
- Configurable rate limiting and pauses
- Progress tracking and statistics

## Original ArXiv Downloader

The original combined downloader is still available for direct PDF+metadata downloads:

```bash
# Download recent papers
python arxiv_downloader.py recent --days 7

# Download by category
python arxiv_downloader.py category cs.AI --max 1000

# Download date range
python arxiv_downloader.py range 2024-01-01 2024-01-31

# Bulk download
python arxiv_downloader.py bulk --start-year 2020
```

## Metadata Format

Each JSON metadata file contains:

```json
{
  "arxiv_id": "2401.00001",
  "title": "Paper Title",
  "authors": ["Author One", "Author Two"],
  "abstract": "Paper abstract...",
  "categories": ["cs.AI", "cs.LG"],
  "published": "2024-01-01T18:00:00Z",
  "updated": "2024-01-02T12:00:00Z",
  "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf",
  "abs_url": "https://arxiv.org/abs/2401.00001",
  "harvested_at": "2024-07-25T10:00:00.000000",
  "pdf_downloaded": true,
  "pdf_downloaded_at": "2024-07-25T14:30:00.000000"
}
```

## Automation Examples

### Daily Cron Job

```bash
# Crontab entry for daily operations
# Harvest new metadata at 2 AM
0 2 * * * cd /path/to/arxiv_downloader && python metadata_harvester.py --config config_master.yaml --days-back 2

# Download PDFs at 3 AM (respecting 1,800 limit)
0 3 * * * cd /path/to/arxiv_downloader && python pdf_downloader.py --config config_master.yaml --limit 1800
```

### Systemd Service for Continuous Harvesting

```ini
[Unit]
Description=ArXiv Metadata Harvester
After=network.target

[Service]
Type=simple
User=yourusername
WorkingDirectory=/path/to/arxiv_downloader
Environment="PATH=/path/to/venv/bin"
ExecStart=/path/to/venv/bin/python metadata_harvester.py --config config_master.yaml --continuous
Restart=always

[Install]
WantedBy=multi-user.target
```

## API Limits and Best Practices

- **API Rate Limit**: 3-second delay between API calls (enforced)
- **Query Limits**: Maximum 1,000 results per API query
- **Daily PDF Limit**: Configurable (e.g., 1,800 papers/day)
- **Storage**: ~2-3 MB per PDF, ~2-5 KB per metadata file

**Storage Estimates:**
- Metadata only: 1M papers ≈ 2-5 GB
- With PDFs: 1,000 papers ≈ 2.5 GB
- With PDFs: 100,000 papers ≈ 250 GB

## Troubleshooting

### Common Issues

1. **"Daily limit reached"**: Wait until tomorrow or increase limit
2. **"Rate limit error"**: The 3-second delay is enforced automatically
3. **"No papers found for date"**: Future dates have no papers yet
4. **"Permission denied"**: Check directory permissions

### Logs

- `metadata_harvest.log`: Metadata collection activity
- `pdf_download.log`: PDF download activity
- Individual script outputs show real-time progress

## Advanced Usage

### Query Specific Papers

```python
import json
from pathlib import Path

# Find papers by category
metadata_dir = Path("/mnt/data/arxiv_data/metadata")
ai_papers = []

for json_file in metadata_dir.glob("*.json"):
    with open(json_file) as f:
        paper = json.load(f)
        if "cs.AI" in paper.get("categories", []):
            ai_papers.append(paper)

# Papers without PDFs
papers_need_pdf = []
for json_file in metadata_dir.glob("*.json"):
    with open(json_file) as f:
        paper = json.load(f)
        if not paper.get("pdf_downloaded", False):
            papers_need_pdf.append(paper)
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Acknowledgments

- **arXiv**: For providing open access to scientific papers
- **Cornell University**: For maintaining the arXiv repository
- Built following [arXiv API Terms of Use](https://arxiv.org/help/api/tou)

---

**Questions?** Open an issue on GitHub or consult the [arXiv API documentation](https://arxiv.org/help/api/user-manual).