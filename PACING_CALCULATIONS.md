# ArXiv Downloader Pacing Calculations

## Download Rhythm

With the configuration:
- 3 seconds between each download
- 10 second pause after every 10 downloads
- 60 second pause after every 100 downloads

### Time per download calculation:

**For every 10 downloads:**
- Download time: 10 × 3s = 30s
- Batch pause: 10s
- Total: 40s for 10 downloads
- Average: 4s per download

**For every 100 downloads:**
- Download time: 100 × 3s = 300s
- Batch pauses: 9 × 10s = 90s (9 batches of 10)
- Session pause: 60s
- Total: 450s for 100 downloads
- Average: 4.5s per download

### Daily capacity:

**In 24 hours (86,400 seconds):**
- At 4.5s average: 86,400 ÷ 4.5 = 19,200 theoretical maximum
- With overhead, errors, retries: ~15,000-18,000 practical maximum
- **Safe daily limit: 1,800 papers** (well under 10% of capacity)

### Monthly progress:

**At 1,800 papers/day:**
- Per month: 1,800 × 30 = 54,000 papers
- Per year: 1,800 × 365 = 657,000 papers

### Time to download entire ArXiv:

**ArXiv statistics (approximate):**
- Total papers: ~2.5 million (as of 2024)
- At 1,800/day: 2,500,000 ÷ 1,800 = 1,389 days (~3.8 years)

### Bandwidth usage:

**At average 2.5 MB per paper:**
- Daily: 1,800 × 2.5 MB = 4.5 GB/day
- Monthly: 135 GB/month
- Yearly: 1.6 TB/year

## Recommended Settings

### For 24/7 backfill operation:
```yaml
download:
  rate_limit: 3.0
  batch_size: 10
  batch_pause: 10.0
  session_pause_after: 100
  session_pause_duration: 60.0
  daily_limit: 1800  # Conservative, respectful rate
```

### For faster but still safe operation:
```yaml
download:
  rate_limit: 3.0
  batch_size: 10
  batch_pause: 10.0
  session_pause_after: 200
  session_pause_duration: 30.0
  daily_limit: 3000  # Still very safe
```

### For maximum safe speed (not recommended for continuous use):
```yaml
download:
  rate_limit: 3.0
  batch_size: 20
  batch_pause: 5.0
  session_pause_after: 500
  session_pause_duration: 30.0
  daily_limit: 5000  # Use sparingly
```

## Why These Limits Are Safe

1. **ArXiv's perspective:**
   - Their API allows up to 1 request per 3 seconds
   - We're strictly following this with additional pauses
   - 1,800 downloads/day is only ~1.25 downloads/minute average
   - This is far below what would be considered abusive

2. **Network perspective:**
   - 4.5 GB/day is minimal bandwidth
   - Spread over 24 hours = ~52 KB/second average
   - Less than watching a low-quality video stream

3. **Server load perspective:**
   - Regular, predictable pattern
   - Built-in breaks reduce sustained load
   - Respects both API and download servers

## Monitoring

The system tracks:
- Daily download counts (persisted in `download_stats.json`)
- Session statistics
- Automatic enforcement of daily limits
- Detailed logging of all activities

Run `python arxiv_downloader.py stats` to see current progress and limits.