#!/usr/bin/env python3
"""
ArXiv Metadata Harvester

This script focuses exclusively on harvesting paper metadata without downloading PDFs.
It's designed for efficient, large-scale metadata collection that can run continuously.

Usage:
    python metadata_harvester.py --start-date 2024-01-01 --end-date 2024-12-31
    python metadata_harvester.py --days-back 30
    python metadata_harvester.py --continuous  # Keep harvesting new papers
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import time
import json

from config import Config, load_config
from arxiv_api import ArxivAPIClient, ArxivPaper
from download_manager import DownloadManager


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('metadata_harvest.log')
    ]
)
logger = logging.getLogger(__name__)


class MetadataHarvester:
    """Handles metadata-only harvesting from arXiv."""
    
    def __init__(self, config: Config):
        self.config = config
        self.api_client = ArxivAPIClient(config.api)
        self.metadata_dir = Path(config.directories.metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Track statistics
        self.stats = {
            'total_processed': 0,
            'new_metadata': 0,
            'existing_metadata': 0,
            'failed': 0,
            'start_time': time.time(),
            'metadata_file_count': 0  # Cached count to avoid expensive glob operations
        }
        
        # Progress tracking
        self.progress_file = self.metadata_dir.parent / 'harvest_progress.json'
        self.progress = self._load_progress()
        
        # Initialize metadata file count
        if 'metadata_file_count' in self.progress:
            self.stats['metadata_file_count'] = self.progress['metadata_file_count']
        else:
            # Count once at startup if not in progress file
            self.stats['metadata_file_count'] = len(list(self.metadata_dir.glob('*.json')))
    
    def _load_progress(self) -> Dict:
        """Load harvest progress from file."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load progress: {e}")
        return {'last_harvest_date': None, 'total_papers': 0}
    
    def _save_progress(self):
        """Save harvest progress to file."""
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
    
    def _save_metadata(self, paper: ArxivPaper) -> bool:
        """Save paper metadata to JSON file."""
        try:
            # Use the same filename convention as download_manager
            safe_arxiv_id = paper.arxiv_id.replace('/', '_')
            metadata_file = self.metadata_dir / f"{safe_arxiv_id}.json"
            
            if metadata_file.exists():
                self.stats['existing_metadata'] += 1
                return True
            
            metadata = {
                'arxiv_id': paper.arxiv_id,
                'title': paper.title,
                'authors': paper.authors,
                'abstract': paper.abstract,
                'categories': paper.categories,
                'published': paper.published,
                'updated': paper.updated,
                'pdf_url': paper.pdf_url,
                'abs_url': paper.abs_url,
                'harvested_at': datetime.now().isoformat(),
                'pdf_downloaded': False  # Track download status
            }
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.stats['new_metadata'] += 1
            self.stats['metadata_file_count'] += 1  # Update cached count
            return True
            
        except Exception as e:
            logger.error(f"Failed to save metadata for {paper.arxiv_id}: {e}")
            self.stats['failed'] += 1
            return False
    
    def harvest_date_range(self, start_date: datetime, end_date: datetime, 
                          categories: Optional[List[str]] = None):
        """Harvest metadata for papers in a date range."""
        logger.info(f"Harvesting metadata from {start_date.date()} to {end_date.date()}")
        if categories:
            logger.info(f"Categories: {', '.join(categories)}")
        
        current_date = start_date
        
        while current_date <= end_date:
            # Process one day at a time for better progress tracking
            day_end = min(current_date.replace(hour=23, minute=59, second=59), end_date)
            
            logger.info(f"Processing {current_date.date()}")
            logger.info("Making API request (this may take a few seconds due to rate limiting)...")
            
            papers = self.api_client.get_papers_by_date_range(
                start_date=current_date,
                end_date=day_end,
                categories=categories,
                max_results=10000  # Adjust based on daily volume
            )
            
            if len(papers) == 10000:
                logger.warning(f"Reached max_results limit for {current_date.date()}. Some papers may be missed.")
            
            logger.info(f"Found {len(papers)} papers for {current_date.date()}")
            
            for i, paper in enumerate(papers):
                self.stats['total_processed'] += 1
                self._save_metadata(paper)
                
                # Log progress every 10 papers for better feedback
                if self.stats['total_processed'] % 10 == 0:
                    self._log_progress()
                
                # Also show progress within current batch
                if i > 0 and i % 50 == 0:
                    logger.info(f"  Processed {i}/{len(papers)} papers for {current_date.date()}")
            
            # Update progress
            self.progress['last_harvest_date'] = day_end.isoformat()
            self.progress['total_papers'] = self.stats['total_processed']
            self.progress['metadata_file_count'] = self.stats['metadata_file_count']
            self._save_progress()
            
            # Move to next day
            current_date = day_end + timedelta(seconds=1)
            current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def harvest_recent(self, days_back: int = 7, categories: Optional[List[str]] = None):
        """Harvest recent papers metadata."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        self.harvest_date_range(start_date, end_date, categories)
    
    def harvest_continuous(self, categories: Optional[List[str]] = None, 
                          check_interval: int = 3600):
        """Continuously harvest new papers."""
        logger.info("Starting continuous harvest mode")
        
        retry_delay = 60
        while True:
            try:
                # Harvest papers from last 2 days to catch any delays
                self.harvest_recent(days_back=2, categories=categories)
                
                retry_delay = 60  # Reset delay on success
                logger.info(f"Sleeping for {check_interval} seconds...")
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("Continuous harvest interrupted by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous harvest: {e}")
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 3600)  # Cap at 1 hour
    
    def _log_progress(self):
        """Log current progress statistics."""
        elapsed = time.time() - self.stats['start_time']
        rate = self.stats['total_processed'] / elapsed if elapsed > 0 else 0
        
        logger.info(
            f"Progress: {self.stats['total_processed']} processed "
            f"({self.stats['new_metadata']} new, "
            f"{self.stats['existing_metadata']} existing, "
            f"{self.stats['failed']} failed) "
            f"Rate: {rate:.1f} papers/sec"
        )
    
    def get_statistics(self) -> Dict:
        """Get harvest statistics."""
        elapsed = time.time() - self.stats['start_time']
        
        return {
            **self.stats,
            'elapsed_seconds': elapsed,
            'papers_per_second': self.stats['total_processed'] / elapsed if elapsed > 0 else 0,
            'metadata_files': self.stats['metadata_file_count']  # Use cached count
        }


def main():
    parser = argparse.ArgumentParser(
        description='Harvest arXiv paper metadata without downloading PDFs'
    )
    parser.add_argument('--config', type=str, help='Configuration file path')
    
    # Date range options
    parser.add_argument('--start-date', type=str, 
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, 
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--days-back', type=int, 
                       help='Number of days to look back')
    
    # Continuous mode
    parser.add_argument('--continuous', action='store_true',
                       help='Continuously harvest new papers')
    parser.add_argument('--check-interval', type=int, default=3600,
                       help='Seconds between checks in continuous mode (default: 3600)')
    
    # Filtering
    parser.add_argument('--categories', nargs='+',
                       help='Categories to harvest (e.g., cs.AI cs.LG)')
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config = load_config(Path(args.config))
    else:
        config = Config()
    
    # Create harvester
    harvester = MetadataHarvester(config)
    
    try:
        if args.continuous:
            harvester.harvest_continuous(
                categories=args.categories,
                check_interval=args.check_interval
            )
        elif args.days_back:
            harvester.harvest_recent(
                days_back=args.days_back,
                categories=args.categories
            )
        elif args.start_date and args.end_date:
            start = datetime.strptime(args.start_date, '%Y-%m-%d')
            end = datetime.strptime(args.end_date, '%Y-%m-%d')
            harvester.harvest_date_range(
                start_date=start,
                end_date=end,
                categories=args.categories
            )
        else:
            # Default: harvest last 7 days
            harvester.harvest_recent(days_back=7, categories=args.categories)
    
    except KeyboardInterrupt:
        logger.info("Harvest interrupted by user")
    finally:
        # Print final statistics
        stats = harvester.get_statistics()
        logger.info("\n=== Final Statistics ===")
        logger.info(f"Total processed: {stats['total_processed']}")
        logger.info(f"New metadata: {stats['new_metadata']}")
        logger.info(f"Existing metadata: {stats['existing_metadata']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Elapsed time: {stats['elapsed_seconds']:.1f} seconds")
        logger.info(f"Rate: {stats['papers_per_second']:.2f} papers/sec")
        logger.info(f"Total metadata files: {stats['metadata_files']}")


if __name__ == '__main__':
    main()