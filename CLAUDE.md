# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based link organizer tool that extracts links from a markdown file and crawls/downloads their content for offline storage and organization. The project helps organize links that were lazily pasted into Notion.

## Core Architecture

The project has a modular architecture with CLI interface and the following components:

### Entry Points:
1. **`cli.py`** - Main CLI interface (`link` command) for all operations
2. **`get_count_links.py`** - Link extraction utility
3. **`enhanced_crawler.py`** - Enhanced crawler with AI classification
4. **`enhanced_crawler_tui.py`** - Crawler with Terminal User Interface

### Core Modules (`src/` directory):

#### Data Management:
- **`models.py`** - Data models (LinkData, ClassificationResult, CrawlerConfig, etc.)
- **`link_index.py`** - Index management with incremental sync support
- **`filename_generator.py`** - Human-readable filename generation from URLs

#### Crawling & Processing:
- **`content_processor.py`** - Content extraction (PDF text, markdown)
- **`crawler_utils.py`** - Web crawling utilities (PDF download, HTML→markdown)
- **`incremental_crawler.py`** - Incremental crawl with readable filenames
- **`workers.py`** - Async worker implementations

#### Classification:
- **`classification_service.py`** - AI-powered content classification
- **`llm/`** - LLM provider abstraction (LiteLLM, OpenRouter)

#### UI & Output:
- **`static_site_generator.py`** - HTML site generation from collection
- **`status_tracker.py`** - Progress tracking
- **`tui.py`** - Terminal User Interface components

### Test Components (`tests/` directory):
- **`test_classification.py`** - Classification functionality tests
- **`test_link_classifier.py`** - Unit tests for LinkClassifier
- **`test_llm_providers.py`** - Unit tests for LLM providers
- **`test_tui.py`** - TUI testing with mock data

## Data Structure

| File/Directory | Description |
|----------------|-------------|
| `links.md` | Input file with URLs to process |
| `index.json` | Master index with links, status, classifications |
| `classifications.json` | Classification results (backwards compat) |
| `dat/` | Downloaded content (readable filenames) |
| `public/` | Generated static HTML site |

## Dependencies

- `crawl4ai` - Web crawling with async support
- `requests` - HTTP requests, PDF downloads
- `litellm` - LLM provider abstraction
- `python-dotenv` - Environment config
- `rich` - Terminal UI
- `PyPDF2` - PDF text extraction
- `Pillow` - Screenshot processing
- `pytest` - Testing

## Python Environment

This project uses **uv** as the package manager with a local virtual environment in `.venv/`.

```bash
# Install dependencies (creates .venv if needed)
uv pip install -e .

# Run any python file
uv run python <script.py>

# Add new packages
uv pip install <package>
```

## CLI Commands

All commands use `uv run python cli.py <command>`:

### Managing Links

```bash
# Add one or more links
uv run python cli.py add https://example.com https://arxiv.org/abs/2105.00613

# List all links
uv run python cli.py list

# List with filters
uv run python cli.py list --category "AI/ML"
uv run python cli.py list --status success
uv run python cli.py list --tag python
uv run python cli.py list --limit 50 --verbose

# Search by keyword
uv run python cli.py search "machine learning"

# Remove a link
uv run python cli.py remove https://example.com
```

### Crawling & Classification

```bash
# Incremental crawl (only new links)
uv run python cli.py crawl

# Crawl all links (reprocess everything)
uv run python cli.py crawl --all

# Retry failed links only
uv run python cli.py crawl --retry

# With TUI progress display
uv run python cli.py crawl --tui

# Custom input file and worker count
uv run python cli.py crawl -f my-links.md --workers 10
```

### Viewing Collection

```bash
# Show statistics
uv run python cli.py stats

# List all categories
uv run python cli.py categories

# List all tags
uv run python cli.py tags
```

### Export & Import

```bash
# Export as JSON
uv run python cli.py export -f json -o backup.json

# Export as markdown
uv run python cli.py export -f markdown -o links-export.md

# Export URLs only
uv run python cli.py export -f urls -o urls.txt

# Import links from markdown file
uv run python cli.py import bookmarks.md
```

### Static Site Generation

```bash
# Generate with defaults (output: public/)
uv run python cli.py generate

# Custom output and title
uv run python cli.py generate -o docs -t "My Reading List" -d "Curated articles"
```

## Legacy Scripts

```bash
uv run python get_count_links.py       # Extract links from links.md
uv run python enhanced_crawler.py      # Original crawler with classification
uv run python enhanced_crawler_tui.py  # Crawler with TUI
```

## Testing

```bash
uv run pytest                    # All tests
uv run pytest -m unit            # Unit tests only
uv run pytest -m integration     # Integration tests
uv run pytest -m "not slow"      # Skip slow tests
```

## Key Features

- **Incremental Sync**: Only processes new/failed links
- **Readable Filenames**: `arxiv-2105-00613.pdf` instead of SHA256 hashes
- **AI Classification**: Category, tags, summary, difficulty, quality score
- **Static Site**: Browsable HTML with categories and search
- **Multiple Export Formats**: JSON, Markdown, URL list
- **TUI Progress**: Real-time crawl monitoring

## Processing Pipeline

1. **Extract** - Parse URLs from markdown files
2. **Filter** - Skip already-processed links (incremental)
3. **Fetch** - Download content (HTML→markdown, PDF)
4. **Save** - Store with readable filename
5. **Classify** - AI categorization via LLM
6. **Index** - Update index.json with metadata
7. **Generate** - Create static HTML site (on demand)