"""Download manager for handling PDF downloads and metadata storage."""

import json
import logging
import time
import re
import unicodedata
from datetime import datetime, date
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import requests

from config import DownloadConfig, DirectoryConfig
from arxiv_api import ArxivPaper

logger = logging.getLogger(__name__)


class DownloadManager:
    """Manages downloading PDFs and saving metadata."""
    
    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 255) -> str:
        """
        Sanitize a filename to be safe for all filesystems.
        
        Args:
            filename: The filename to sanitize
            max_length: Maximum length for the filename (default 255)
            
        Returns:
            A sanitized filename safe for use on all systems
        """
        # Normalize unicode characters
        filename = unicodedata.normalize('NFKD', filename)
        
        # Replace path separators and other unsafe characters
        # Keep alphanumeric, dots, hyphens, and underscores
        filename = re.sub(r'[^\w\s.-]', '_', filename)
        
        # Replace multiple underscores/spaces with single underscore
        filename = re.sub(r'[\s_]+', '_', filename)
        
        # Remove leading/trailing dots and underscores
        filename = filename.strip('._')
        
        # Handle reserved names on Windows
        reserved_names = {'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                         'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                         'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'}
        
        name_parts = filename.rsplit('.', 1)
        if name_parts[0].upper() in reserved_names:
            filename = f"_{filename}"
        
        # Ensure filename isn't empty
        if not filename:
            filename = "unnamed_file"
        
        # Truncate to max length while preserving extension if possible
        if len(filename) > max_length:
            name_parts = filename.rsplit('.', 1)
            if len(name_parts) == 2 and len(name_parts[1]) < 10:
                # Preserve extension
                max_name_length = max_length - len(name_parts[1]) - 1
                filename = f"{name_parts[0][:max_name_length]}.{name_parts[1]}"
            else:
                filename = filename[:max_length]
        
        return filename
    
    def __init__(self, download_config: DownloadConfig, directory_config: DirectoryConfig):
        """Initialize the download manager.
        
        Args:
            download_config: Download configuration
            directory_config: Directory configuration
        """
        self.download_config = download_config
        self.directory_config = directory_config
        
        # Create directories
        self._setup_directories()
        
        # Statistics
        self.stats = {
            'total_attempted': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'skipped_existing': 0
        }
        
        # Daily limit tracking
        self.daily_downloads: Dict[str, int] = {}
        self.session_downloads = 0
        self._load_daily_stats()
    
    def _setup_directories(self) -> None:
        """Create necessary directories."""
        base_dir = Path(self.directory_config.base_dir)
        base_dir.mkdir(exist_ok=True)
        
        self.directory_config.pdf_dir.mkdir(exist_ok=True)
        self.directory_config.metadata_dir.mkdir(exist_ok=True)
        
        logger.info(f"Directories initialized: PDFs={self.directory_config.pdf_dir}, "
                   f"Metadata={self.directory_config.metadata_dir}")
    
    def _get_stats_file(self) -> Path:
        """Get path to daily stats file."""
        return Path(self.directory_config.base_dir) / "download_stats.json"
    
    def _load_daily_stats(self) -> None:
        """Load daily download statistics."""
        stats_file = self._get_stats_file()
        if stats_file.exists():
            try:
                with open(stats_file, 'r') as f:
                    data = json.load(f)
                    self.daily_downloads = data.get('daily_downloads', {})
                    # Clean up old entries (keep last 7 days)
                    today = date.today()
                    self.daily_downloads = {
                        day: count for day, count in self.daily_downloads.items()
                        if (today - date.fromisoformat(day)).days < 7
                    }
            except Exception as e:
                logger.warning(f"Could not load daily stats: {e}")
                self.daily_downloads = {}
    
    def _save_daily_stats(self) -> None:
        """Save daily download statistics."""
        stats_file = self._get_stats_file()
        try:
            with open(stats_file, 'w') as f:
                json.dump({
                    'daily_downloads': self.daily_downloads,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save daily stats: {e}")
    
    def _check_daily_limit(self) -> Tuple[bool, int]:
        """Check if daily limit has been reached.
        
        Returns:
            Tuple of (can_download, downloads_today)
        """
        if self.download_config.daily_limit is None:
            return True, 0
        
        today_str = date.today().isoformat()
        downloads_today = self.daily_downloads.get(today_str, 0)
        
        can_download = downloads_today < self.download_config.daily_limit
        return can_download, downloads_today
    
    def _increment_daily_count(self) -> None:
        """Increment today's download count."""
        today_str = date.today().isoformat()
        self.daily_downloads[today_str] = self.daily_downloads.get(today_str, 0) + 1
        self._save_daily_stats()
    
    def _download_with_retry(self, url: str, filepath: Path) -> bool:
        """Download a file with retry logic.
        
        Args:
            url: URL to download from
            filepath: Path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(self.download_config.max_retries):
            try:
                response = requests.get(
                    url,
                    stream=True,
                    timeout=self.download_config.timeout
                )
                response.raise_for_status()
                
                # Write file in chunks
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=self.download_config.chunk_size):
                        if chunk:
                            f.write(chunk)
                
                return True
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Download attempt {attempt + 1} failed for {url}: {e}")
                if attempt < self.download_config.max_retries - 1:
                    time.sleep(self.download_config.retry_delay)
                else:
                    logger.error(f"All download attempts failed for {url}")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error downloading {url}: {e}")
                return False
        
        return False
    
    def download_paper(self, paper: ArxivPaper) -> bool:
        """Download a single paper (PDF and metadata).
        
        Args:
            paper: ArxivPaper object containing paper information
            
        Returns:
            True if successful, False otherwise
        """
        self.stats['total_attempted'] += 1
        
        # Sanitize arxiv_id for safe filename
        # e.g., "math/9201254" becomes "math_9201254"
        safe_arxiv_id = self.sanitize_filename(paper.arxiv_id)
        
        pdf_filename = f"{safe_arxiv_id}.pdf"
        pdf_filepath = self.directory_config.pdf_dir / pdf_filename
        
        metadata_filename = f"{safe_arxiv_id}.json"
        metadata_filepath = self.directory_config.metadata_dir / metadata_filename
        
        # Check if already exists
        if pdf_filepath.exists() and metadata_filepath.exists():
            logger.debug(f"Already exists: {paper.arxiv_id}")
            self.stats['skipped_existing'] += 1
            return True  # Return True but don't count as new download
        
        # Save metadata first (it's small and less likely to fail)
        if not metadata_filepath.exists():
            if not self._save_metadata(paper, metadata_filepath):
                self.stats['failed_downloads'] += 1
                return False
        
        # Download PDF if not exists
        if not pdf_filepath.exists():
            logger.info(f"Downloading: {paper.arxiv_id} -> {safe_arxiv_id}")
            if self._download_with_retry(paper.pdf_url, pdf_filepath):
                logger.info(f"Downloaded: {pdf_filename}")
                self.stats['successful_downloads'] += 1
                self._increment_daily_count()
                self.session_downloads += 1
                return True
            else:
                # Remove metadata if PDF download failed
                if metadata_filepath.exists():
                    metadata_filepath.unlink()
                self.stats['failed_downloads'] += 1
                return False
        
        self.stats['successful_downloads'] += 1
        return True
    
    def _save_metadata(self, paper: ArxivPaper, filepath: Path) -> bool:
        """Save paper metadata as JSON.
        
        Args:
            paper: ArxivPaper object
            filepath: Path to save the metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(paper.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save metadata for {paper.arxiv_id}: {e}")
            return False
    
    def download_papers(self, papers: List[ArxivPaper], rate_limit: float = 3.0) -> Dict[str, int]:
        """Download multiple papers with rate limiting and pacing controls.
        
        Args:
            papers: List of ArxivPaper objects
            rate_limit: Seconds between downloads
            
        Returns:
            Dictionary with download statistics
        """
        total = len(papers)
        logger.info(f"Starting download of {total} papers")
        
        # Check daily limit at start
        can_download, downloads_today = self._check_daily_limit()
        if not can_download:
            logger.warning(f"Daily limit reached ({self.download_config.daily_limit} downloads). "
                         f"Already downloaded {downloads_today} today.")
            return self.stats
        
        downloads_in_batch = 0
        
        for i, paper in enumerate(papers):
            # Check daily limit before each download
            can_download, downloads_today = self._check_daily_limit()
            if not can_download:
                logger.info(f"Daily limit reached ({self.download_config.daily_limit} downloads). "
                          f"Stopping for today. Progress: {i}/{total}")
                break
            
            # Check if file exists before attempting download
            safe_id = paper.arxiv_id.replace('/', '_')
            pdf_path = self.directory_config.pdf_dir / f"{safe_id}.pdf"
            metadata_path = self.directory_config.metadata_dir / f"{safe_id}.json"
            already_exists = pdf_path.exists() and metadata_path.exists()
            
            # Download paper
            download_result = self.download_paper(paper)
            
            # Only count actual NEW downloads for pacing (not skipped files)
            if download_result and not already_exists:
                downloads_in_batch += 1
            
            # Progress update
            if (i + 1) % 50 == 0:
                logger.info(f"Progress: {i + 1}/{total} "
                          f"(Success: {self.stats['successful_downloads']}, "
                          f"Failed: {self.stats['failed_downloads']}, "
                          f"Skipped: {self.stats['skipped_existing']}, "
                          f"Today: {downloads_today})")
            
            # Pacing controls (except for last paper)
            if i < total - 1:
                # Regular rate limit between each request
                time.sleep(rate_limit)
                
                # Batch pause: longer pause every N downloads
                if downloads_in_batch > 0 and downloads_in_batch % self.download_config.batch_size == 0:
                    logger.info(f"Batch of {self.download_config.batch_size} complete. "
                              f"Pausing for {self.download_config.batch_pause} seconds...")
                    time.sleep(self.download_config.batch_pause)
                
                # Session pause: even longer pause every 100 downloads
                if (self.session_downloads > 0 and 
                    self.session_downloads % self.download_config.session_pause_after == 0):
                    logger.info(f"Session milestone: {self.session_downloads} downloads. "
                              f"Taking a {self.download_config.session_pause_duration} second break...")
                    time.sleep(self.download_config.session_pause_duration)
        
        logger.info(f"Download session complete! "
                   f"Success: {self.stats['successful_downloads']}, "
                   f"Failed: {self.stats['failed_downloads']}, "
                   f"Skipped: {self.stats['skipped_existing']}, "
                   f"Total today: {self.daily_downloads.get(date.today().isoformat(), 0)}")
        
        return self.stats
    
    def clean_incomplete_downloads(self) -> int:
        """Clean up incomplete downloads (orphaned files).
        
        Returns:
            Number of files cleaned up
        """
        cleaned = 0
        
        # Find PDFs without metadata
        pdf_files = set(f.stem for f in self.directory_config.pdf_dir.glob("*.pdf"))
        metadata_files = set(f.stem for f in self.directory_config.metadata_dir.glob("*.json"))
        
        # Remove PDFs without metadata
        pdfs_without_metadata = pdf_files - metadata_files
        for arxiv_id in pdfs_without_metadata:
            pdf_path = self.directory_config.pdf_dir / f"{arxiv_id}.pdf"
            if pdf_path.exists():
                logger.info(f"Removing orphaned PDF: {arxiv_id}.pdf")
                pdf_path.unlink()
                cleaned += 1
        
        # Remove metadata without PDFs
        metadata_without_pdfs = metadata_files - pdf_files
        for arxiv_id in metadata_without_pdfs:
            metadata_path = self.directory_config.metadata_dir / f"{arxiv_id}.json"
            if metadata_path.exists():
                logger.info(f"Removing orphaned metadata: {arxiv_id}.json")
                metadata_path.unlink()
                cleaned += 1
        
        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} incomplete downloads")
        
        return cleaned
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get download statistics and storage info.
        
        Returns:
            Dictionary with statistics
        """
        pdf_files = list(self.directory_config.pdf_dir.glob("*.pdf"))
        metadata_files = list(self.directory_config.metadata_dir.glob("*.json"))
        
        total_size = sum(f.stat().st_size for f in pdf_files)
        
        today_downloads = self.daily_downloads.get(date.today().isoformat(), 0)
        
        return {
            'total_papers': len(pdf_files),
            'total_metadata': len(metadata_files),
            'total_size_bytes': total_size,
            'total_size_gb': round(total_size / (1024**3), 2),
            'download_stats': self.stats,
            'storage_path': str(Path(self.directory_config.base_dir).absolute()),
            'daily_stats': {
                'downloads_today': today_downloads,
                'daily_limit': self.download_config.daily_limit,
                'recent_days': self.daily_downloads
            }
        }