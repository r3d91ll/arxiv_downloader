#!/usr/bin/env python3
"""Test script to debug early arXiv paper downloads."""

import logging
import argparse
import os
from datetime import datetime
from config import Config, APIConfig
from arxiv_api import ArxivAPIClient

# Setup logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Parse command line arguments and environment variables
parser = argparse.ArgumentParser(description='Test early arXiv paper downloads')
parser.add_argument('--rate-limit', type=float, help='Rate limit in seconds between API calls')
args = parser.parse_args()

# Get rate limit from args, env, or default to 3.0
rate_limit = args.rate_limit or float(os.environ.get('ARXIV_RATE_LIMIT', '3.0'))

# Create a simple config
api_config = APIConfig()
client = ArxivAPIClient(api_config, rate_limit=rate_limit)

print(f"Using rate limit: {rate_limit} seconds")

# Test 1: Search for papers from July 1991
print("=== Testing July 1991 papers ===")
papers, total = client.search(
    query="submittedDate:[199107010000 TO 199107312359]",
    max_results=10
)

print(f"Found {len(papers)} papers (total: {total})")

# Helper function to truncate title at word boundary
def truncate_title(title, max_length=60):
    if len(title) <= max_length:
        return title
    # Find last space before max_length
    truncated = title[:max_length]
    last_space = truncated.rfind(' ')
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."

# Display up to 5 papers, or fewer if less available
num_to_display = min(5, len(papers))
for i, paper in enumerate(papers[:num_to_display]):
    print(f"\nPaper {i+1}:")
    print(f"  ID: {paper.arxiv_id}")
    print(f"  Title: {truncate_title(paper.title)}")
    print(f"  PDF URL: {paper.pdf_url}")
    print(f"  Categories: {paper.categories}")

# Test 2: Try a specific known early paper
print("\n\n=== Testing specific early paper query ===")
papers2, total2 = client.search(
    query="cat:hep-lat",
    max_results=5,
    sort_by="submittedDate",
    sort_order="ascending"
)

print(f"Found {len(papers2)} papers in hep-lat")
for paper in papers2:
    print(f"\nID: {paper.arxiv_id}")
    print(f"Title: {truncate_title(paper.title)}")
    print(f"PDF URL: {paper.pdf_url}")
    print(f"Published: {paper.published}")

# Test 3: Try without date restriction
print("\n\n=== Testing all papers sorted by oldest ===")
papers3, total3 = client.search(
    query="all:*",
    max_results=5,
    sort_by="submittedDate",
    sort_order="ascending"
)

print(f"Found {len(papers3)} papers")
for paper in papers3:
    print(f"\nID: {paper.arxiv_id}")
    print(f"Title: {truncate_title(paper.title)}")
    print(f"PDF URL: {paper.pdf_url}")
    print(f"Published: {paper.published}")