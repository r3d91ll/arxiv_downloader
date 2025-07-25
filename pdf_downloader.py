#!/usr/bin/env python3
"""
PDF Downloader for ArXiv Papers

Downloads PDFs based on existing metadata files, respecting daily limits.
Designed to work with metadata collected by metadata_harvester.py

Usage:
    python pdf_downloader.py --limit 1800
    python pdf_downloader.py --limit 1800 --priority newest
    python pdf_downloader.py --limit 1800 --categories cs.AI cs.LG
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Set
import random

from config import Config, load_config
from download_manager import DownloadManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pdf_download.log')
    ]
)
logger = logging.getLogger(__name__)


class PDFDownloader:
    """Downloads PDFs based on existing metadata."""
    
    def __init__(self, config: Config):
        self.config = config
        self.metadata_dir = Path(config.directories.metadata_dir)
        self.pdf_dir = Path(config.directories.pdf_dir)
        self.pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Use existing download manager for actual downloads
        self.download_manager = DownloadManager(config.download, config.directories)
        
        # Track daily downloads
        self.daily_count_file = self.pdf_dir.parent / 'pdf_daily_count.json'
        self.daily_downloads = self._load_daily_count()
        
        # Session statistics
        self.stats = {
            'checked': 0,
            'already_downloaded': 0,
            'downloaded': 0,
            'failed': 0,
            'skipped_limit': 0,
            'start_time': time.time()
        }
    
    def _load_daily_count(self) -> Dict:
        """Load daily download count."""
        if self.daily_count_file.exists():
            try:
                with open(self.daily_count_file, 'r') as f:
                    data = json.load(f)
                    # Reset if it's a new day
                    if data.get('date') != datetime.now().strftime('%Y-%m-%d'):
                        return {'date': datetime.now().strftime('%Y-%m-%d'), 'count': 0}
                    return data
            except Exception as e:
                logger.warning(f"Failed to load daily count: {e}")
        
        return {'date': datetime.now().strftime('%Y-%m-%d'), 'count': 0}
    
    def _save_daily_count(self):
        """Save daily download count."""
        try:
            with open(self.daily_count_file, 'w') as f:
                json.dump(self.daily_downloads, f)
        except Exception as e:
            logger.error(f"Failed to save daily count: {e}")
    
    def _check_daily_limit(self, limit: int) -> bool:
        """Check if we've hit the daily limit."""
        return self.daily_downloads['count'] >= limit
    
    def _get_metadata_files(self, 
                           priority: str = 'newest',
                           categories: Optional[List[str]] = None) -> List[Path]:
        """Get list of metadata files to process.
        
        Args:
            priority: 'newest', 'oldest', or 'random'
            categories: Filter by these categories
        
        Returns:
            List of metadata file paths
        """
        metadata_files = list(self.metadata_dir.glob('*.json'))
        
        # Filter out files that already have PDFs
        candidates = []
        for meta_file in metadata_files:
            pdf_file = self.pdf_dir / meta_file.name.replace('.json', '.pdf')
            if not pdf_file.exists():
                # Check categories if specified
                if categories:
                    try:
                        with open(meta_file, 'r') as f:
                            data = json.load(f)
                            paper_cats = data.get('categories', [])
                            if any(cat in paper_cats for cat in categories):
                                candidates.append(meta_file)
                    except Exception:
                        continue
                else:
                    candidates.append(meta_file)
        
        # Sort based on priority
        if priority == 'newest':
            # Sort by arxiv ID (newer IDs are larger)
            candidates.sort(key=lambda x: x.stem, reverse=True)
        elif priority == 'oldest':
            candidates.sort(key=lambda x: x.stem)
        elif priority == 'random':
            random.shuffle(candidates)
        
        return candidates
    
    def download_pdfs(self, 
                     daily_limit: int = 1800,
                     priority: str = 'newest',
                     categories: Optional[List[str]] = None):
        """Download PDFs up to daily limit.
        
        Args:
            daily_limit: Maximum downloads per day
            priority: Download priority ('newest', 'oldest', 'random')
            categories: Only download papers from these categories
        """
        logger.info(f"Starting PDF downloads (limit: {daily_limit}, priority: {priority})")
        logger.info(f"Already downloaded today: {self.daily_downloads['count']}")
        
        if self._check_daily_limit(daily_limit):
            logger.warning(f"Daily limit of {daily_limit} already reached")
            return
        
        # Get metadata files to process
        metadata_files = self._get_metadata_files(priority, categories)
        logger.info(f"Found {len(metadata_files)} papers without PDFs")
        
        if categories:
            logger.info(f"Filtering by categories: {', '.join(categories)}")
        
        # Process files
        for meta_file in metadata_files:
            if self._check_daily_limit(daily_limit):
                logger.info(f"Daily limit of {daily_limit} reached")
                self.stats['skipped_limit'] = len(metadata_files) - self.stats['checked']
                break
            
            self.stats['checked'] += 1
            
            try:
                # Load metadata
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                
                arxiv_id = metadata['arxiv_id']
                pdf_url = metadata['pdf_url']
                
                # Check if PDF already exists
                safe_arxiv_id = arxiv_id.replace('/', '_')
                pdf_file = self.pdf_dir / f"{safe_arxiv_id}.pdf"
                
                if pdf_file.exists():
                    self.stats['already_downloaded'] += 1
                    continue
                
                # Download PDF
                logger.info(f"Downloading {arxiv_id} ({self.daily_downloads['count'] + 1}/{daily_limit})")
                
                success = self.download_manager._download_with_retry(pdf_url, pdf_file)
                
                if success:
                    self.stats['downloaded'] += 1
                    self.daily_downloads['count'] += 1
                    self._save_daily_count()
                    
                    # Update metadata to mark PDF as downloaded
                    metadata['pdf_downloaded'] = True
                    metadata['pdf_downloaded_at'] = datetime.now().isoformat()
                    with open(meta_file, 'w') as f:
                        json.dump(metadata, f, indent=2, ensure_ascii=False)
                    
                    # Progress update every 10 downloads
                    if self.stats['downloaded'] % 10 == 0:
                        self._log_progress()
                    
                    # Rate limiting
                    time.sleep(self.config.download.rate_limit)
                    
                    # Batch pause
                    if self.stats['downloaded'] % self.config.download.batch_size == 0:
                        logger.info(f"Batch pause: {self.config.download.batch_pause} seconds")
                        time.sleep(self.config.download.batch_pause)
                    
                    # Session pause
                    if self.stats['downloaded'] % self.config.download.session_pause_after == 0:
                        logger.info(f"Session pause: {self.config.download.session_pause_duration} seconds")
                        time.sleep(self.config.download.session_pause_duration)
                else:
                    self.stats['failed'] += 1
                    logger.error(f"Failed to download {arxiv_id}")
                    
            except Exception as e:
                logger.error(f"Error processing {meta_file}: {e}")
                self.stats['failed'] += 1
    
    def _log_progress(self):
        """Log download progress."""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['downloaded'] / elapsed if elapsed > 0 else 0
        
        logger.info(
            f"Progress: {self.stats['checked']} checked, "
            f"{self.stats['downloaded']} downloaded, "
            f"{self.stats['already_downloaded']} existing, "
            f"{self.stats['failed']} failed. "
            f"Rate: {rate:.2f} PDFs/sec"
        )
    
    def get_statistics(self) -> Dict:
        """Get session statistics."""
        elapsed = time.time() - self.stats['start_time']
        
        return {
            **self.stats,
            'elapsed_seconds': elapsed,
            'download_rate': self.stats['downloaded'] / elapsed if elapsed > 0 else 0,
            'daily_count': self.daily_downloads['count'],
            'daily_remaining': max(0, 1800 - self.daily_downloads['count'])
        }


def main():
    parser = argparse.ArgumentParser(
        description='Download PDFs based on existing metadata files'
    )
    parser.add_argument('--config', type=str, help='Configuration file path')
    parser.add_argument('--limit', type=int, default=1800,
                       help='Daily download limit (default: 1800)')
    parser.add_argument('--priority', choices=['newest', 'oldest', 'random'],
                       default='newest',
                       help='Download priority (default: newest)')
    parser.add_argument('--categories', nargs='+',
                       help='Only download papers from these categories (e.g., cs.AI cs.LG)')
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = load_config(Path(args.config))
    else:
        config = Config()
    
    # Create downloader
    downloader = PDFDownloader(config)
    
    try:
        # Start downloading
        downloader.download_pdfs(
            daily_limit=args.limit,
            priority=args.priority,
            categories=args.categories
        )
    
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
    
    finally:
        # Print statistics
        stats = downloader.get_statistics()
        logger.info("\n=== Session Statistics ===")
        logger.info(f"Checked: {stats['checked']} metadata files")
        logger.info(f"Downloaded: {stats['downloaded']} PDFs")
        logger.info(f"Already had: {stats['already_downloaded']} PDFs")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Skipped (limit): {stats['skipped_limit']}")
        logger.info(f"Session time: {stats['elapsed_seconds']:.1f} seconds")
        logger.info(f"Download rate: {stats['download_rate']:.2f} PDFs/sec")
        logger.info(f"\nDaily total: {stats['daily_count']}/1800")
        logger.info(f"Daily remaining: {stats['daily_remaining']}")


if __name__ == '__main__':
    main()