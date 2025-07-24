"""Configuration management for ArXiv Downloader."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml
import logging

logger = logging.getLogger(__name__)


@dataclass
class DownloadConfig:
    """Configuration for download operations."""
    rate_limit: float = 3.0
    timeout: int = 30
    chunk_size: int = 8192
    max_retries: int = 3
    retry_delay: float = 5.0
    
    # Pacing controls
    batch_size: int = 10  # Number of downloads before longer pause
    batch_pause: float = 10.0  # Seconds to pause after each batch
    daily_limit: Optional[int] = None  # Maximum downloads per day (None = unlimited)
    
    # Session controls
    session_pause_after: int = 100  # Pause after this many downloads
    session_pause_duration: float = 60.0  # How long to pause (seconds)


@dataclass
class DirectoryConfig:
    """Configuration for directory structure."""
    base_dir: str = "arxiv_papers"
    pdf_subdir: str = "pdf"
    metadata_subdir: str = "metadata"
    
    @property
    def pdf_dir(self) -> Path:
        """Get full path to PDF directory."""
        return Path(self.base_dir) / self.pdf_subdir
    
    @property
    def metadata_dir(self) -> Path:
        """Get full path to metadata directory."""
        return Path(self.base_dir) / self.metadata_subdir


@dataclass
class APIConfig:
    """Configuration for ArXiv API."""
    base_url: str = "http://export.arxiv.org/api/query"
    max_results_per_query: int = 1000
    default_sort_by: str = "submittedDate"
    default_sort_order: str = "descending"


@dataclass
class LoggingConfig:
    """Configuration for logging."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(levelname)s - %(message)s"
    file: Optional[str] = None


@dataclass
class JobConfig:
    """Configuration for specific job types."""
    name: str
    enabled: bool = True
    categories: List[str] = field(default_factory=list)
    max_papers_per_run: Optional[int] = None
    date_range_days: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    
    # For bulk downloads
    bulk_start_year: Optional[int] = None
    bulk_max_per_month: int = 500
    
    # For scheduled jobs
    schedule: Optional[str] = None  # cron format
    
    # Custom query
    custom_query: Optional[str] = None


@dataclass
class Config:
    """Main configuration class."""
    download: DownloadConfig = field(default_factory=DownloadConfig)
    directories: DirectoryConfig = field(default_factory=DirectoryConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    jobs: Dict[str, JobConfig] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
            
            config = cls()
            
            # Load download config
            if 'download' in data:
                download_data = data['download']
                config.download = DownloadConfig(**download_data)
            
            # Load directory config
            if 'directories' in data:
                config.directories = DirectoryConfig(**data['directories'])
            
            # Load API config
            if 'api' in data:
                config.api = APIConfig(**data['api'])
            
            # Load logging config
            if 'logging' in data:
                config.logging = LoggingConfig(**data['logging'])
            
            # Load job configs
            if 'jobs' in data:
                for job_name, job_data in data['jobs'].items():
                    config.jobs[job_name] = JobConfig(name=job_name, **job_data)
            
            logger.info(f"Configuration loaded from {config_path}")
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            raise
    
    def to_yaml(self, config_path: Path) -> None:
        """Save configuration to YAML file."""
        data = {
            'download': {
                'rate_limit': self.download.rate_limit,
                'timeout': self.download.timeout,
                'chunk_size': self.download.chunk_size,
                'max_retries': self.download.max_retries,
                'retry_delay': self.download.retry_delay,
                'batch_size': self.download.batch_size,
                'batch_pause': self.download.batch_pause,
                'session_pause_after': self.download.session_pause_after,
                'session_pause_duration': self.download.session_pause_duration,
            },
            'directories': {
                'base_dir': self.directories.base_dir,
                'pdf_subdir': self.directories.pdf_subdir,
                'metadata_subdir': self.directories.metadata_subdir,
            },
            'api': {
                'base_url': self.api.base_url,
                'max_results_per_query': self.api.max_results_per_query,
                'default_sort_by': self.api.default_sort_by,
                'default_sort_order': self.api.default_sort_order,
            },
            'logging': {
                'level': self.logging.level,
                'format': self.logging.format,
            }
        }
        
        if self.logging.file:
            data['logging']['file'] = self.logging.file
        
        # Add daily limit if set
        if self.download.daily_limit is not None:
            data['download']['daily_limit'] = self.download.daily_limit
        
        # Add jobs
        if self.jobs:
            data['jobs'] = {}
            for job_name, job in self.jobs.items():
                job_data = {
                    'enabled': job.enabled,
                }
                
                # Only add non-None optional fields
                if job.categories:
                    job_data['categories'] = job.categories
                if job.max_papers_per_run is not None:
                    job_data['max_papers_per_run'] = job.max_papers_per_run
                if job.date_range_days is not None:
                    job_data['date_range_days'] = job.date_range_days
                if job.start_date:
                    job_data['start_date'] = job.start_date
                if job.end_date:
                    job_data['end_date'] = job.end_date
                if job.bulk_start_year is not None:
                    job_data['bulk_start_year'] = job.bulk_start_year
                if job.bulk_max_per_month != 500:
                    job_data['bulk_max_per_month'] = job.bulk_max_per_month
                if job.schedule:
                    job_data['schedule'] = job.schedule
                if job.custom_query:
                    job_data['custom_query'] = job.custom_query
                
                data['jobs'][job_name] = job_data
        
        with open(config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration saved to {config_path}")


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or return default."""
    if config_path and config_path.exists():
        return Config.from_yaml(config_path)
    else:
        logger.info("Using default configuration")
        return Config()