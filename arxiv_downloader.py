#!/usr/bin/env python3
"""
Simple ArXiv PDF Downloader
Downloads arXiv papers as PDFs into a single directory with standard naming.
Files self-organize chronologically by arXiv ID.
"""

import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import List, Optional
import argparse
import json

class SimpleArxivDownloader:
    def __init__(self, download_dir: str = "arxiv_papers", rate_limit: float = 3.0):
        """
        Simple arXiv downloader that saves PDFs with standard naming.
        
        Args:
            download_dir: Directory to save PDFs and metadata
            rate_limit: Seconds between requests (respect arXiv limits)
        """
        self.download_dir = Path(download_dir)
        self.pdf_dir = self.download_dir / "pdf"
        self.metadata_dir = self.download_dir / "metadata"
        
        # Create directories
        self.download_dir.mkdir(exist_ok=True)
        self.pdf_dir.mkdir(exist_ok=True)
        self.metadata_dir.mkdir(exist_ok=True)
        
        self.rate_limit = rate_limit
        self.arxiv_api_url = "http://export.arxiv.org/api/query"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Downloader initialized. PDFs: {self.pdf_dir}, Metadata: {self.metadata_dir}")
        
    def save_metadata(self, arxiv_id: str, metadata: dict) -> bool:
        """Save metadata as JSON file."""
        metadata_file = self.metadata_dir / f"{arxiv_id}.json"
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save metadata for {arxiv_id}: {e}")
            return False
    
    def download_pdf(self, arxiv_id: str) -> bool:
        """Download a single PDF by arXiv ID."""
        filename = f"{arxiv_id}.pdf"
        filepath = self.pdf_dir / filename
        
        # Skip if already exists
        if filepath.exists():
            self.logger.debug(f"Already exists: {filename}")
            return True
            
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        try:
            response = requests.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            self.logger.info(f"Downloaded: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download {arxiv_id}: {e}")
            return False
    
    def fetch_papers_with_metadata(self, query: str, max_results: int = 1000, start: int = 0) -> List[dict]:
        """Fetch arXiv papers with full metadata."""
        params = {
            'search_query': query,
            'start': start,
            'max_results': min(max_results, 1000),  # arXiv limit
            'sortBy': 'submittedDate',
            'sortOrder': 'descending'
        }
        
        try:
            response = requests.get(self.arxiv_api_url, params=params, timeout=30)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            
            papers = []
            for entry in entries:
                # Extract arXiv ID
                id_url = entry.find('{http://www.w3.org/2005/Atom}id').text
                arxiv_id = id_url.split('/')[-1]
                
                # Extract metadata
                title = entry.find('{http://www.w3.org/2005/Atom}title').text.strip()
                abstract = entry.find('{http://www.w3.org/2005/Atom}summary').text.strip()
                published = entry.find('{http://www.w3.org/2005/Atom}published').text
                updated = entry.find('{http://www.w3.org/2005/Atom}updated').text
                
                # Extract authors
                authors = []
                for author in entry.findall('{http://www.w3.org/2005/Atom}author'):
                    name = author.find('{http://www.w3.org/2005/Atom}name').text
                    authors.append(name)
                
                # Extract categories
                categories = []
                for category in entry.findall('{http://arxiv.org/schemas/atom}primary_category'):
                    categories.append(category.get('term'))
                for category in entry.findall('{http://arxiv.org/schemas/atom}category'):
                    cat_term = category.get('term')
                    if cat_term not in categories:
                        categories.append(cat_term)
                
                # Extract links
                pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                abs_url = f"https://arxiv.org/abs/{arxiv_id}"
                
                metadata = {
                    'arxiv_id': arxiv_id,
                    'title': title,
                    'authors': authors,
                    'abstract': abstract,
                    'categories': categories,
                    'published': published,
                    'updated': updated,
                    'pdf_url': pdf_url,
                    'abs_url': abs_url,
                    'fetched_at': datetime.now().isoformat()
                }
                
                papers.append(metadata)
                
            return papers
            
        except Exception as e:
            self.logger.error(f"Failed to fetch papers with metadata: {e}")
            return []
    
    def download_recent_papers(self, days_back: int = 1) -> int:
        """Download papers from the last N days."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        query = f"submittedDate:[{start_date.strftime('%Y%m%d')} TO {end_date.strftime('%Y%m%d')}]"
        
        self.logger.info(f"Fetching papers from last {days_back} days...")
        papers = self.fetch_papers_with_metadata(query, max_results=5000)
        
        return self.download_papers_with_metadata(papers)
    
    def download_by_category(self, category: str, max_papers: int = 1000) -> int:
        """Download papers by category (e.g., 'cs.AI', 'cs.LG')."""
        query = f"cat:{category}"
        
        self.logger.info(f"Fetching {max_papers} papers from category: {category}")
        papers = self.fetch_papers_with_metadata(query, max_results=max_papers)
        
        return self.download_papers_with_metadata(papers)
    
    def download_date_range(self, start_date: str, end_date: str, max_papers: int = 10000) -> int:
        """
        Download papers from a date range.
        
        Args:
            start_date: Format 'YYYY-MM-DD'
            end_date: Format 'YYYY-MM-DD'
            max_papers: Maximum papers to download
        """
        start_fmt = start_date.replace('-', '')
        end_fmt = end_date.replace('-', '')
        
        query = f"submittedDate:[{start_fmt} TO {end_fmt}]"
        
        self.logger.info(f"Fetching papers from {start_date} to {end_date}")
        
        # Handle large date ranges in batches
        all_papers = []
        batch_size = 1000
        start_idx = 0
        
        while len(all_papers) < max_papers:
            batch_papers = self.fetch_papers_with_metadata(query, max_results=batch_size, start=start_idx)
            if not batch_papers:
                break
                
            all_papers.extend(batch_papers)
            start_idx += batch_size
            
            self.logger.info(f"Fetched {len(all_papers)} papers so far...")
            time.sleep(self.rate_limit)
            
        return self.download_papers_with_metadata(all_papers[:max_papers])
    
    def download_papers_with_metadata(self, papers: List[dict]) -> int:
        """Download a list of papers with metadata."""
        if not papers:
            self.logger.warning("No papers to download")
            return 0
            
        self.logger.info(f"Starting download of {len(papers)} papers...")
        
        downloaded_count = 0
        for i, paper in enumerate(papers, 1):
            arxiv_id = paper['arxiv_id']
            
            # Save metadata first
            if self.save_metadata(arxiv_id, paper):
                # Then download PDF
                if self.download_pdf(arxiv_id):
                    downloaded_count += 1
            
            # Rate limiting
            if i < len(papers):  # Don't sleep after last download
                time.sleep(self.rate_limit)
                
            # Progress update
            if i % 50 == 0:
                self.logger.info(f"Progress: {i}/{len(papers)} ({downloaded_count} successful)")
        
        self.logger.info(f"Download complete! {downloaded_count}/{len(papers)} successful")
        return downloaded_count
    
    def bulk_download_all(self, start_year: int = 2020, max_per_month: int = 500):
        """
        Download arXiv papers in bulk, organized by month.
        
        Args:
            start_year: Year to start from
            max_per_month: Limit papers per month (for storage management)
        """
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        self.logger.info(f"Starting bulk download from {start_year}")
        
        total_downloaded = 0
        
        for year in range(start_year, current_year + 1):
            end_month = current_month if year == current_year else 12
            
            for month in range(1, end_month + 1):
                start_date = f"{year}-{month:02d}-01"
                
                # Calculate end date (last day of month)
                if month == 12:
                    end_date = f"{year}-12-31"
                else:
                    next_month = datetime(year, month + 1, 1) - timedelta(days=1)
                    end_date = next_month.strftime("%Y-%m-%d")
                
                self.logger.info(f"Processing {year}-{month:02d}...")
                
                count = self.download_date_range(start_date, end_date, max_per_month)
                total_downloaded += count
                
                # Be respectful - longer pause between months
                time.sleep(30)
                
        self.logger.info(f"Bulk download complete! Total: {total_downloaded} papers")
        return total_downloaded
    
    def get_stats(self) -> dict:
        """Get download statistics."""
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        metadata_files = list(self.metadata_dir.glob("*.json"))
        
        if not pdf_files:
            return {"total_papers": 0, "total_size_gb": 0}
        
        total_size = sum(f.stat().st_size for f in pdf_files)
        
        return {
            "total_papers": len(pdf_files),
            "total_metadata": len(metadata_files),
            "total_size_gb": round(total_size / (1024**3), 2),
            "pdf_dir": str(self.pdf_dir),
            "metadata_dir": str(self.metadata_dir)
        }


def main():
    parser = argparse.ArgumentParser(description="Simple arXiv PDF Downloader")
    parser.add_argument("--dir", default="arxiv_papers", help="Download directory")
    parser.add_argument("--rate", type=float, default=3.0, help="Rate limit (seconds)")
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Recent papers
    recent_parser = subparsers.add_parser("recent", help="Download recent papers")
    recent_parser.add_argument("--days", type=int, default=1, help="Days back")
    
    # By category
    cat_parser = subparsers.add_parser("category", help="Download by category")
    cat_parser.add_argument("category", help="arXiv category (e.g., cs.AI)")
    cat_parser.add_argument("--max", type=int, default=1000, help="Max papers")
    
    # Date range
    date_parser = subparsers.add_parser("range", help="Download date range")
    date_parser.add_argument("start_date", help="Start date (YYYY-MM-DD)")
    date_parser.add_argument("end_date", help="End date (YYYY-MM-DD)")
    date_parser.add_argument("--max", type=int, default=10000, help="Max papers")
    
    # Bulk download
    bulk_parser = subparsers.add_parser("bulk", help="Bulk download all")
    bulk_parser.add_argument("--start-year", type=int, default=2020, help="Start year")
    bulk_parser.add_argument("--max-per-month", type=int, default=500, help="Max per month")
    
    # Stats
    subparsers.add_parser("stats", help="Show download statistics")
    
    args = parser.parse_args()
    
    downloader = SimpleArxivDownloader(args.dir, args.rate)
    
    if args.command == "recent":
        downloader.download_recent_papers(args.days)
    elif args.command == "category":
        downloader.download_by_category(args.category, args.max)
    elif args.command == "range":
        downloader.download_date_range(args.start_date, args.end_date, args.max)
    elif args.command == "bulk":
        downloader.bulk_download_all(args.start_year, args.max_per_month)
    elif args.command == "stats":
        stats = downloader.get_stats()
        print(f"Total papers: {stats['total_papers']}")
        print(f"Total metadata files: {stats['total_metadata']}")
        print(f"Total size: {stats['total_size_gb']} GB")
        print(f"PDF directory: {stats['pdf_dir']}")
        print(f"Metadata directory: {stats['metadata_dir']}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()