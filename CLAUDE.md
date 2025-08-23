# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based link organizer tool that extracts links from a markdown file and crawls/downloads their content for offline storage and organization. The project helps organize links that were lazily pasted into Notion.

## Core Architecture

The project now has a modular architecture with the following components:

### Main Scripts:
1. **`get_count_links.py`** - Link extraction utility that parses markdown files to find URLs using regex patterns for both markdown-style links `[text](url)` and bare URLs
2. **`crawl_links.py`** - Original basic crawler that processes links using crawl4ai
3. **`enhanced_crawler.py`** - Enhanced crawler with AI classification capabilities and worker-based architecture
4. **`link_classifier.py`** - Standalone link classification utility with LLM provider support

### Modular Components (`src/` directory):
- **`models.py`** - Data models and type definitions
- **`classification_service.py`** - Core AI classification service
- **`content_processor.py`** - Content processing utilities  
- **`crawler_utils.py`** - Crawling utility functions
- **`workers.py`** - Async worker implementations for fetching and classification
- **`llm/`** - LLM provider abstraction layer supporting LiteLLM and OpenRouter

## Data Structure

- **Input**: `links.md` - Contains links to be processed (markdown format)
- **Output Directory**: `dat/` - Stores processed content with SHA256-hashed filenames
- **Index**: `index.json` - Maps original links to their processed files and status

## Dependencies

The project uses:
- `crawl4ai` - Main web crawling library with async support
- `requests` - For PDF downloads  
- `litellm` - LLM provider abstraction layer
- `python-dotenv` - Environment variable management
- `pytest` - Testing framework
- Standard library modules: `hashlib`, `json`, `asyncio`, `urllib.parse`, `re`, `pathlib`

## Python Environment

Environment can be activated with 
```bash
source ~/venv/linkenv/bin/activate
```

The UV python package manager is used. All installations of python packages to use 
```bash
uv pip ...
```

## Common Commands

### Installing Dependencies

Since this is a simple Python project without a package manager configuration file, dependencies must be installed manually:

```bash
uv pip install crawl4ai requests litellm python-dotenv pytest
```

### Running the Tools

- Extract and count links: `python get_count_links.py`
- Basic crawler: `python crawl_links.py` 
- Enhanced crawler with AI classification: `python enhanced_crawler.py`
- Standalone classification: `python link_classifier.py`

### Testing

Run tests using pytest:
```bash
pytest
```

Run specific test categories:
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only  
pytest -m "not slow"    # Skip slow tests
```

## Key Implementation Details

- Uses SHA256 hashing to generate unique filenames for processed content
- Implements semaphore-based concurrency control with configurable limits
- Handles both PDF and HTML content with appropriate processing
- Creates an index mapping original URLs to processed files for tracking
- Excludes navigation, footer elements and external links during crawling
- Modular LLM provider system supporting LiteLLM and OpenRouter
- Worker-based async architecture for fetch and classification tasks
- AI-powered content classification with categories, tags, and summaries
- Comprehensive test suite with pytest configuration