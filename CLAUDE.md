# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based link organizer tool that extracts links from a markdown file and crawls/downloads their content for offline storage and organization. The project helps organize links that were lazily pasted into Notion.

## Core Architecture

The project consists of three main Python scripts:

1. **`get_count_links.py`** - Link extraction utility that parses markdown files to find URLs using regex patterns for both markdown-style links `[text](url)` and bare URLs
2. **`crawl_links.py`** - Main crawler that processes extracted links asynchronously using crawl4ai, handles both HTML content (converted to markdown) and PDF downloads, and stores processed content in the `dat/` directory with SHA256-hashed filenames
3. **`crawl_test.py`** - Simple test script demonstrating crawl4ai usage on Hacker News

## Data Structure

- **Input**: `links.md` - Contains links to be processed (markdown format)
- **Output Directory**: `dat/` - Stores processed content with SHA256-hashed filenames
- **Index**: `index.json` - Maps original links to their processed files and status

## Dependencies

The project uses:
- `crawl4ai` - Main web crawling library with async support
- `requests` - For PDF downloads
- Standard library modules: `hashlib`, `json`, `asyncio`, `urllib.parse`, `re`

## Common Commands

Since this is a simple Python project without a package manager configuration file, dependencies must be installed manually:

```bash
pip install crawl4ai requests
```

### Running the Tools

- Extract and count links: `python get_count_links.py`
- Process all links: `python crawl_links.py` 
- Test crawler: `python crawl_test.py`

## Key Implementation Details

- Uses SHA256 hashing to generate unique filenames for processed content
- Implements semaphore-based concurrency control (limit of 8 concurrent requests)
- Handles both PDF and HTML content with appropriate processing
- Creates an index mapping original URLs to processed files for tracking
- Excludes navigation, footer elements and external links during crawling