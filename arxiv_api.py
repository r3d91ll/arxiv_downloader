"""ArXiv API client with proper type hints."""

import time
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

from config import APIConfig

logger = logging.getLogger(__name__)



@dataclass
class ArxivPaper:
    """Represents an ArXiv paper with metadata."""
    arxiv_id: str
    title: str
    authors: List[str]
    abstract: str
    categories: List[str]
    published: str
    updated: str
    pdf_url: str
    abs_url: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'arxiv_id': self.arxiv_id,
            'title': self.title,
            'authors': self.authors,
            'abstract': self.abstract,
            'categories': self.categories,
            'published': self.published,
            'updated': self.updated,
            'pdf_url': self.pdf_url,
            'abs_url': self.abs_url,
            'fetched_at': datetime.now().isoformat()
        }


class ArxivAPIClient:
    """Client for interacting with the ArXiv API."""
    
    def __init__(self, config: APIConfig, rate_limit: float = 3.0):
        """Initialize the API client.
        
        Args:
            config: API configuration
            rate_limit: Seconds between API requests
        """
        self.config = config
        self.rate_limit = rate_limit
        self.last_request_time: Optional[float] = None
        
    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between API requests."""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit:
                sleep_time = self.rate_limit - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _parse_entry(self, entry: ET.Element) -> Optional[ArxivPaper]:
        """Parse a single entry from the API response.
        
        Args:
            entry: XML element representing a paper entry
            
        Returns:
            ArxivPaper object or None if parsing fails
        """
        try:
            # Extract arxiv ID from the id URL
            id_url = entry.find('{http://www.w3.org/2005/Atom}id').text
            # URL format: http://arxiv.org/abs/hep-lat/9107001v1
            # or: http://arxiv.org/abs/2401.00001v2
            
            # Get everything after /abs/
            if '/abs/' in id_url:
                arxiv_id_with_version = id_url.split('/abs/')[-1]
            else:
                arxiv_id_with_version = id_url.split('/')[-1]
            
            # Remove version number (v1, v2, etc.)
            arxiv_id = arxiv_id_with_version.split('v')[0]
            
            logger.debug(f"Parsed arxiv_id: {arxiv_id} from URL: {id_url}")
            
            # Get title
            title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
            
            # Get authors
            authors = []
            for author in entry.findall('{http://www.w3.org/2005/Atom}author'):
                name = author.find('{http://www.w3.org/2005/Atom}name').text
                authors.append(name)
            
            # Get abstract
            abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
            
            # Get categories
            categories = []
            for category in entry.findall('{http://arxiv.org/schemas/atom}category'):
                categories.append(category.get('term'))
            
            # Get dates
            published = entry.find('{http://www.w3.org/2005/Atom}published').text
            updated = entry.find('{http://www.w3.org/2005/Atom}updated').text
            
            # Get links
            # Old format (pre-2007): category/YYMMNNN (no .pdf extension)
            # New format (2007+): YYMM.NNNNN (with .pdf extension)
            if '/' in arxiv_id:
                # Old format - no .pdf extension
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
            else:
                # New format - needs .pdf extension
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
            abs_url = f"https://arxiv.org/abs/{arxiv_id}"
            
            return ArxivPaper(
                arxiv_id=arxiv_id,
                title=title,
                authors=authors,
                abstract=abstract,
                categories=categories,
                published=published,
                updated=updated,
                pdf_url=pdf_url,
                abs_url=abs_url
            )
            
        except Exception as e:
            logger.error(f"Error parsing entry: {e}")
            return None
    
    def search(
        self,
        query: str,
        max_results: int = 1000,
        start: int = 0,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Tuple[List[ArxivPaper], int]:
        """Search for papers on ArXiv.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            start: Starting index for pagination
            sort_by: Sort field (default from config)
            sort_order: Sort order (default from config)
            
        Returns:
            Tuple of (list of papers, total results count)
        """
        self._enforce_rate_limit()
        
        params = {
            'search_query': query,
            'start': start,
            'max_results': min(max_results, self.config.max_results_per_query),
            'sortBy': sort_by or self.config.default_sort_by,
            'sortOrder': sort_order or self.config.default_sort_order
        }
        
        try:
            logger.info(f"Searching ArXiv with query: {query}")
            response = requests.get(self.config.base_url, params=params, timeout=30)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.text)
            
            # Get total results
            total_results_elem = root.find('{http://a9.com/-/spec/opensearch/1.1/}totalResults')
            total_results = int(total_results_elem.text) if total_results_elem is not None else 0
            
            # Parse entries
            papers = []
            for entry in root.findall('{http://www.w3.org/2005/Atom}entry'):
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)
            
            logger.info(f"Found {len(papers)} papers (total: {total_results})")
            return papers, total_results
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return [], 0
        except ET.ParseError as e:
            logger.error(f"Failed to parse API response: {e}")
            return [], 0
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}")
            return [], 0
    
    def get_papers_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        categories: Optional[List[str]] = None,
        max_results: int = 10000
    ) -> List[ArxivPaper]:
        """Get papers within a date range.
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            categories: Optional list of categories to filter
            max_results: Maximum number of results
            
        Returns:
            List of papers
        """
        # Build date query
        date_query = f"submittedDate:[{start_date.strftime('%Y%m%d')}0000 TO {end_date.strftime('%Y%m%d')}2359]"
        
        # Add category filter if specified
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query = f"{date_query} AND ({cat_query})"
        else:
            query = date_query
        
        all_papers = []
        start = 0
        
        while start < max_results:
            papers, total = self.search(
                query=query,
                max_results=min(self.config.max_results_per_query, max_results - start),
                start=start
            )
            
            if not papers:
                break
                
            all_papers.extend(papers)
            start += len(papers)
            
            logger.info(f"Progress: {len(all_papers)}/{min(total, max_results)}")
            
            if len(papers) < self.config.max_results_per_query:
                break
        
        return all_papers[:max_results]
    
    def get_recent_papers(
        self,
        days_back: int = 1,
        categories: Optional[List[str]] = None,
        max_results: int = 1000
    ) -> List[ArxivPaper]:
        """Get recent papers from the last N days.
        
        Args:
            days_back: Number of days to look back
            categories: Optional list of categories to filter
            max_results: Maximum number of results
            
        Returns:
            List of papers
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        return self.get_papers_by_date_range(
            start_date=start_date,
            end_date=end_date,
            categories=categories,
            max_results=max_results
        )