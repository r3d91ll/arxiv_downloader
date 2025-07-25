#!/usr/bin/env python3
"""
ArXiv PDF Downloader - Refactored with Configuration Support
Downloads arXiv papers as PDFs with metadata, supporting multiple configurations.
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List

from arxiv_api import ArxivAPIClient
from config import Config, load_config, JobConfig
from download_manager import DownloadManager

# Configuration constants
MONTHLY_PAUSE_SECONDS = 30  # Pause duration between processing months



def setup_logging(config: Config) -> None:
    """Setup logging based on configuration."""
    valid_levels = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}
    level_str = config.logging.level.upper()
    
    if level_str not in valid_levels:
        raise ValueError(
            f"Invalid log level '{config.logging.level}'. "
            f"Must be one of: {', '.join(sorted(valid_levels))}"
        )
    
    log_level = getattr(logging, level_str)
    
    handlers: List[logging.Handler] = [logging.StreamHandler()]
    
    if config.logging.file:
        # Create logs directory if needed
        log_file = Path(config.logging.file)
        log_file.parent.mkdir(exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=log_level,
        format=config.logging.format,
        handlers=handlers
    )


def run_recent_papers(
    api_client: ArxivAPIClient,
    download_manager: DownloadManager,
    config: Config,
    days: int = 1,
    categories: Optional[List[str]] = None,
    max_papers: int = 1000
) -> None:
    """Download recent papers from the last N days."""
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching papers from the last {days} day(s)")
    
    papers = api_client.get_recent_papers(
        days_back=days,
        categories=categories,
        max_results=max_papers
    )
    
    if papers:
        download_manager.download_papers(papers, rate_limit=config.download.rate_limit)
    else:
        logger.info("No papers found for the specified criteria")


def run_category_download(
    api_client: ArxivAPIClient,
    download_manager: DownloadManager,
    config: Config,
    category: str,
    max_papers: int = 1000
) -> None:
    """Download papers from a specific category."""
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching papers from category: {category}")
    
    papers, _ = api_client.search(
        query=f"cat:{category}",
        max_results=max_papers
    )
    
    if papers:
        download_manager.download_papers(papers, rate_limit=config.download.rate_limit)
    else:
        logger.info(f"No papers found in category {category}")


def run_date_range_download(
    api_client: ArxivAPIClient,
    download_manager: DownloadManager,
    config: Config,
    start_date: str,
    end_date: str,
    categories: Optional[List[str]] = None,
    max_papers: int = 10000
) -> None:
    """Download papers within a date range."""
    logger = logging.getLogger(__name__)
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD")
        return
    
    logger.info(f"Fetching papers from {start_date} to {end_date}")
    
    papers = api_client.get_papers_by_date_range(
        start_date=start,
        end_date=end,
        categories=categories,
        max_results=max_papers
    )
    
    if papers:
        download_manager.download_papers(papers, rate_limit=config.download.rate_limit)
    else:
        logger.info("No papers found for the specified date range")


def run_bulk_download(
    api_client: ArxivAPIClient,
    download_manager: DownloadManager,
    config: Config,
    start_year: int = 2020,
    max_per_month: int = 500,
    categories: Optional[List[str]] = None
) -> None:
    """Bulk download papers month by month."""
    logger = logging.getLogger(__name__)
    
    current_date = datetime.now()
    start_date = datetime(start_year, 1, 1)
    
    logger.info(f"Starting bulk download from {start_year}")
    
    while start_date < current_date:
        # Calculate end of month
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
        
        logger.info(f"Processing {start_date.strftime('%Y-%m')}")
        
        papers = api_client.get_papers_by_date_range(
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            max_results=max_per_month
        )
        
        if papers:
            download_manager.download_papers(papers, rate_limit=config.download.rate_limit)
        
        # Pause between months
        logger.info(f"Pausing {MONTHLY_PAUSE_SECONDS} seconds before next month...")
        time.sleep(MONTHLY_PAUSE_SECONDS)
        
        # Move to next month
        start_date = end_date + timedelta(days=1)


def run_job(job: JobConfig, api_client: ArxivAPIClient, download_manager: DownloadManager, config: Config) -> None:
    """Run a specific job from configuration."""
    logger = logging.getLogger(__name__)
    logger.info(f"Running job: {job.name}")
    
    if not job.enabled:
        logger.info(f"Job {job.name} is disabled, skipping")
        return
    
    # Validate that only one job type is specified
    job_types = []
    if job.custom_query:
        job_types.append("custom_query")
    if job.date_range_days:
        job_types.append("date_range_days")
    if job.start_date and job.end_date:
        job_types.append("date_range")
    if job.bulk_start_year:
        job_types.append("bulk_download")
    
    if len(job_types) == 0:
        logger.error(f"Job '{job.name}' has no job type specified. Must specify one of: custom_query, date_range_days, start_date/end_date, or bulk_start_year")
        raise ValueError(f"Job '{job.name}' has no job type specified")
    elif len(job_types) > 1:
        logger.error(f"Job '{job.name}' has multiple job types specified: {job_types}. Only one job type is allowed per job.")
        raise ValueError(f"Job '{job.name}' has multiple job types specified: {job_types}")
    
    # Handle different job types
    if job.custom_query:
        papers, _ = api_client.search(
            query=job.custom_query,
            max_results=job.max_papers_per_run or 1000
        )
        if papers:
            download_manager.download_papers(papers, rate_limit=config.download.rate_limit)
    
    elif job.date_range_days:
        run_recent_papers(
            api_client,
            download_manager,
            config,
            days=job.date_range_days,
            categories=job.categories,
            max_papers=job.max_papers_per_run or 1000
        )

    elif job.start_date and job.end_date:
        run_date_range_download(
            api_client,
            download_manager,
            config,
            start_date=job.start_date,
            end_date=job.end_date,
            categories=job.categories,
            max_papers=job.max_papers_per_run or 10000
        )

    elif job.bulk_start_year:
        run_bulk_download(
            api_client,
            download_manager,
            config,
            start_year=job.bulk_start_year,
            max_per_month=job.bulk_max_per_month,
            categories=job.categories
        )


def show_statistics(download_manager: DownloadManager) -> None:
    """Display download statistics."""
    logger = logging.getLogger(__name__)
    stats = download_manager.get_statistics()
    
    logger.info("\n=== ArXiv Download Statistics ===")
    logger.info(f"Storage Path: {stats['storage_path']}")
    logger.info(f"Total Papers: {stats['total_papers']}")
    logger.info(f"Total Metadata Files: {stats['total_metadata']}")
    logger.info(f"Total Size: {stats['total_size_gb']} GB")
    
    # Daily statistics
    daily_stats = stats.get('daily_stats', {})
    if daily_stats:
        logger.info(f"\nToday's Downloads: {daily_stats['downloads_today']}")
        if daily_stats['daily_limit']:
            logger.info(f"Daily Limit: {daily_stats['daily_limit']}")
            remaining = daily_stats['daily_limit'] - daily_stats['downloads_today']
            logger.info(f"Remaining Today: {remaining}")
        
        if daily_stats.get('recent_days'):
            logger.info("\nRecent Daily Downloads:")
            for day, count in sorted(daily_stats['recent_days'].items(), reverse=True)[:7]:
                logger.info(f"  {day}: {count} downloads")
    
    if stats['download_stats']['total_attempted'] > 0:
        logger.info("\nLast Session:")
        logger.info(f"  Attempted: {stats['download_stats']['total_attempted']}")
        logger.info(f"  Successful: {stats['download_stats']['successful_downloads']}")
        logger.info(f"  Failed: {stats['download_stats']['failed_downloads']}")
        logger.info(f"  Skipped (existing): {stats['download_stats']['skipped_existing']}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ArXiv PDF Downloader with Configuration Support",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Global arguments
    parser.add_argument(
        '--config', '-c',
        type=Path,
        help='Path to configuration file (YAML)'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Recent papers
    recent_parser = subparsers.add_parser('recent', help='Download recent papers')
    recent_parser.add_argument('--days', type=int, default=1, help='Days back to fetch')
    recent_parser.add_argument('--categories', nargs='+', help='Categories to filter')
    recent_parser.add_argument('--max', type=int, default=1000, help='Maximum papers')
    
    # Category download
    category_parser = subparsers.add_parser('category', help='Download by category')
    category_parser.add_argument('category', help='ArXiv category (e.g., cs.AI)')
    category_parser.add_argument('--max', type=int, default=1000, help='Maximum papers')
    
    # Date range
    range_parser = subparsers.add_parser('range', help='Download date range')
    range_parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
    range_parser.add_argument('end_date', help='End date (YYYY-MM-DD)')
    range_parser.add_argument('--categories', nargs='+', help='Categories to filter')
    range_parser.add_argument('--max', type=int, default=10000, help='Maximum papers')
    
    # Bulk download
    bulk_parser = subparsers.add_parser('bulk', help='Bulk download by month')
    bulk_parser.add_argument('--start-year', type=int, default=2020, help='Start year')
    bulk_parser.add_argument('--max-per-month', type=int, default=500, help='Max papers per month')
    bulk_parser.add_argument('--categories', nargs='+', help='Categories to filter')
    
    # Run configured job
    job_parser = subparsers.add_parser('job', help='Run a configured job')
    job_parser.add_argument('job_name', help='Name of the job from config file')
    
    # Statistics
    subparsers.add_parser('stats', help='Show download statistics')
    
    # Cleanup
    subparsers.add_parser('cleanup', help='Clean up incomplete downloads')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        # Load configuration
        config = load_config(args.config)
        setup_logging(config)
        
        # Initialize components
        api_client = ArxivAPIClient(config.api, rate_limit=config.download.rate_limit)
        download_manager = DownloadManager(config.download, config.directories)
        
        # Execute command
        if args.command == 'recent':
            run_recent_papers(
                api_client,
                download_manager,
                config,
                days=args.days,
                categories=args.categories,
                max_papers=args.max
            )
        
        elif args.command == 'category':
            run_category_download(
                api_client,
                download_manager,
                config,
                category=args.category,
                max_papers=args.max
            )
        
        elif args.command == 'range':
            run_date_range_download(
                api_client,
                download_manager,
                config,
                start_date=args.start_date,
                end_date=args.end_date,
                categories=args.categories,
                max_papers=args.max
            )
        
        elif args.command == 'bulk':
            run_bulk_download(
                api_client,
                download_manager,
                config,
                start_year=args.start_year,
                max_per_month=args.max_per_month,
                categories=args.categories
            )
        
        elif args.command == 'job':
            if args.job_name in config.jobs:
                run_job(config.jobs[args.job_name], api_client, download_manager, config)
            else:
                logging.error(f"Job '{args.job_name}' not found in configuration")
                print(f"Available jobs: {', '.join(config.jobs.keys())}")
                sys.exit(1)
        
        elif args.command == 'stats':
            show_statistics(download_manager)
        
        elif args.command == 'cleanup':
            cleaned = download_manager.clean_incomplete_downloads()
            if cleaned > 0:
                print(f"Cleaned up {cleaned} incomplete downloads")
            else:
                print("No incomplete downloads found")
    
    except KeyboardInterrupt:
        logging.info("Download interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
        logging.debug("Full traceback:", exc_info=True)
        print(f"\nError: {type(e).__name__}: {str(e)}")
        print("Check the log file for more details.")
        sys.exit(1)


if __name__ == "__main__":
    main()