# ArXiv PDF Downloader

A simple, efficient utility for downloading research papers from arXiv with their metadata. Downloads are organized chronologically by arXiv submission order, making this perfect for research analysis, machine learning datasets, and semantic knowledge mapping.


## Features

- 📄 **PDF Downloads**: Download papers directly from arXiv
- 📊 **Rich Metadata**: Capture titles, authors, abstracts, categories, and publication dates
- 🗂️ **Perfect Pairing**: PDFs and metadata files use identical naming for easy matching
- ⏰ **Chronological Organization**: Files naturally organize by submission order (YYMM.NNNNN format)
- 🚀 **Multiple Download Modes**: Recent papers, categories, date ranges, or bulk downloads
- 🛡️ **Rate Limiting**: Respects arXiv's API guidelines (3-second delays)
- 📈 **Progress Tracking**: Real-time download progress and statistics

## Directory Structure

The downloader creates a clean, organized structure:

```
arxiv_papers/
├── pdf/
│   ├── 2401.00001.pdf    # 1st paper submitted in Jan 2024
│   ├── 2401.00002.pdf    # 2nd paper submitted in Jan 2024
│   ├── 2401.00003.pdf
│   └── ...
└── metadata/
    ├── 2401.00001.json   # Matching metadata for easy pairing
    ├── 2401.00002.json
    ├── 2401.00003.json
    └── ...
```

## Installation

1. **Install Python dependencies:**

   ```bash
   pip install requests
   ```

2. **Clone the repository:**

   ```bash
   git clone git@github.com:r3d91ll/arxiv_downloader.git
   cd arxiv_downloader
   ```

3. **Make it executable (optional):**

   ```bash
   chmod +x arxiv_downloader.py
   ```

## Usage

### Command Line Interface

The downloader supports multiple modes:

#### Download Recent Papers

```bash
# Download papers from the last day
python arxiv_downloader.py recent

# Download papers from the last week
python arxiv_downloader.py recent --days 7
```

#### Download by Category

```bash
# Download AI papers
python arxiv_downloader.py category cs.AI

# Download 2000 machine learning papers
python arxiv_downloader.py category cs.LG --max 2000

# Other popular categories:
python arxiv_downloader.py category cs.CV   # Computer Vision
python arxiv_downloader.py category cs.CL   # Computation and Language
python arxiv_downloader.py category stat.ML # Statistics - Machine Learning
```

#### Download by Date Range

```bash
# Download papers from January 2024
python arxiv_downloader.py range 2024-01-01 2024-01-31

# Download papers from 2023 (limited to 5000)
python arxiv_downloader.py range 2023-01-01 2023-12-31 --max 5000
```

#### Bulk Download

```bash
# Download all papers from 2020 onwards (500 per month limit)
python arxiv_downloader.py bulk --start-year 2020

# Increase monthly limit (use with caution - respects storage)
python arxiv_downloader.py bulk --start-year 2022 --max-per-month 1000
```

#### View Statistics

```bash
python arxiv_downloader.py stats
```

### Programmatic Usage

```python
from arxiv_downloader import SimpleArxivDownloader

# Initialize downloader
downloader = SimpleArxivDownloader(
    download_dir="my_papers",
    rate_limit=3.0  # seconds between requests
)

# Download recent papers
count = downloader.download_recent_papers(days_back=3)
print(f"Downloaded {count} papers")

# Download by category
count = downloader.download_by_category("cs.AI", max_papers=500)

# Get statistics
stats = downloader.get_stats()
print(f"Total papers: {stats['total_papers']}")
print(f"Total size: {stats['total_size_gb']} GB")
```

## Metadata Format

Each JSON metadata file contains:

```json
{
  "arxiv_id": "2401.00001",
  "title": "Attention Is All You Need",
  "authors": [
    "Ashish Vaswani",
    "Noam Shazeer",
    "Niki Parmar"
  ],
  "abstract": "The dominant sequence transduction models are based on complex recurrent or convolutional neural networks...",
  "categories": [
    "cs.CL",
    "cs.AI",
    "cs.LG"
  ],
  "published": "2024-01-01T18:30:00Z",
  "updated": "2024-01-01T18:30:00Z",
  "pdf_url": "https://arxiv.org/pdf/2401.00001.pdf",
  "abs_url": "https://arxiv.org/abs/2401.00001",
  "fetched_at": "2024-07-24T15:30:00.123456"
}
```

## ArXiv ID Format

ArXiv uses a chronological ID system that enables natural timeline analysis:

- **Format**: `YYMM.NNNNN`
- **YYMM**: Year and month (e.g., 2401 = January 2024)
- **NNNNN**: Sequential submission number within that month

**Examples:**

- `2401.00001` = 1st paper submitted in January 2024
- `2401.00002` = 2nd paper submitted in January 2024
- `2312.17543` = 17,543rd paper submitted in December 2023

This creates **perfect chronological ordering** for research analysis!

## Popular ArXiv Categories

| Category | Description |
|----------|-------------|
| `cs.AI` | Artificial Intelligence |
| `cs.LG` | Machine Learning |
| `cs.CL` | Computation and Language (NLP) |
| `cs.CV` | Computer Vision |
| `cs.CR` | Cryptography and Security |
| `cs.IR` | Information Retrieval |
| `stat.ML` | Statistics - Machine Learning |
| `math.OC` | Optimization and Control |
| `q-bio.NC` | Neurons and Cognition |
| `physics.data-an` | Data Analysis, Statistics and Probability |

[Full category list available at arXiv.org](https://arxiv.org/category_taxonomy)

## Rate Limiting & Best Practices

- **Default rate limit**: 3 seconds between requests (respects arXiv guidelines)
- **Bulk downloads**: Include 30-second pauses between months
- **Storage consideration**: ~2-3 MB per paper average
- **API limits**: Maximum 1000 papers per API call

**Estimated storage requirements:**

- 1,000 papers ≈ 2.5 GB
- 10,000 papers ≈ 25 GB  
- 100,000 papers ≈ 250 GB

## Integration Examples

### With Document Processing Systems

```python
import os
from pathlib import Path

pdf_dir = Path("arxiv_papers/pdf")
metadata_dir = Path("arxiv_papers/metadata")

for pdf_file in pdf_dir.glob("*.pdf"):
    # Get matching metadata
    metadata_file = metadata_dir / f"{pdf_file.stem}.json"
    
    if metadata_file.exists():
        # Process paired PDF and metadata
        process_document(pdf_file, metadata_file)
```

### With Machine Learning Pipelines

```python
import json
from pathlib import Path

def load_arxiv_dataset():
    papers = []
    metadata_dir = Path("arxiv_papers/metadata")
    
    for json_file in sorted(metadata_dir.glob("*.json")):
        with open(json_file) as f:
            paper = json.load(f)
            papers.append(paper)
    
    return papers  # Chronologically ordered by submission

# Papers are naturally sorted by submission order!
papers = load_arxiv_dataset()
```

## Command Line Options

```bash
python arxiv_downloader.py [command] [options]

Global Options:
  --dir DIR     Download directory (default: arxiv_papers)
  --rate FLOAT  Rate limit in seconds (default: 3.0)

Commands:
  recent        Download recent papers
    --days INT    Days back to fetch (default: 1)
  
  category      Download by category
    CATEGORY      ArXiv category (e.g., cs.AI)
    --max INT     Maximum papers (default: 1000)
  
  range         Download date range
    START_DATE    Start date (YYYY-MM-DD)
    END_DATE      End date (YYYY-MM-DD)
    --max INT     Maximum papers (default: 10000)
  
  bulk          Bulk download all papers
    --start-year INT        Start year (default: 2020)
    --max-per-month INT     Max per month (default: 500)
  
  stats         Show download statistics
```

## Error Handling

The downloader includes robust error handling:

- **Failed downloads**: Logged but don't stop the process
- **Rate limiting**: Automatic delays between requests
- **Network issues**: Timeout handling and retry logic
- **File conflicts**: Skips existing files automatically
- **Large files**: Streams downloads to handle memory efficiently

## Logging

Logs include:

- Download progress and success rates
- Error messages with paper IDs
- Rate limiting notifications
- Storage statistics

Example log output:

```
2024-07-24 15:30:01 - INFO - Fetching papers from category: cs.AI
2024-07-24 15:30:05 - INFO - Downloaded: 2401.00001.pdf
2024-07-24 15:30:08 - INFO - Downloaded: 2401.00002.pdf
2024-07-24 15:30:15 - INFO - Progress: 50/1000 (48 successful)
2024-07-24 15:45:22 - INFO - Download complete! 987/1000 successful
```

## Contributing

This utility is designed to be simple and focused. For enhancements:

1. **Fork the repository**
2. **Create a feature branch**
3. **Add tests for new functionality**
4. **Submit a pull request**

## License

MIT License - Feel free to use for research, commercial, or personal projects.

## Acknowledgments

- **arXiv**: For providing free access to scientific literature
- **Cornell University**: For maintaining the arXiv repository
- Built with respect for arXiv's [API guidelines](https://arxiv.org/help/api/user-manual)

---

**Need help?** Open an issue or check the [arXiv API documentation](https://arxiv.org/help/api/user-manual).
