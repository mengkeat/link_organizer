# Link Organizer

A powerful tool for organizing, crawling, and classifying web links. Extract links from markdown files, download content for offline storage, classify them with AI, and generate a static site to browse your collection.

## Features

- **Link Extraction**: Parse markdown files to extract URLs
- **Web Crawling**: Download and save web content (HTML → Markdown, PDFs)
- **AI Classification**: Automatic categorization using LLM providers (LiteLLM, OpenRouter)
- **Incremental Sync**: Only process new links, skip already-saved ones
- **Readable Filenames**: Human-friendly filenames like `arxiv-2105-00613.pdf` instead of SHA256 hashes
- **Static Site Generation**: Generate a browsable HTML site from your collection
- **CLI Interface**: Full command-line interface for all operations
- **TUI Progress**: Optional terminal UI for monitoring crawl progress

## Installation

```bash
# Clone the repository
git clone https://github.com/mengkeat/link_organizer.git
cd link_organizer

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies with uv
uv pip install -e .

# Or with pip
pip install -e .
```

## Quick Start

```bash
# 1. Add your links to links.md or add via CLI
uv run python cli.py add https://example.com/article https://arxiv.org/abs/2105.00613

# 2. Crawl and classify links
uv run python cli.py crawl

# 3. Generate static site
uv run python cli.py generate

# 4. Open public/index.html in your browser
```

## CLI Commands

All commands are run with `uv run python cli.py <command>`. After installing with `uv pip install -e .`, you can use `link <command>` directly.

### Managing Links

```bash
# Add links
uv run python cli.py add <url> [<url> ...]

# List all links
uv run python cli.py list

# List with filters
uv run python cli.py list --category "AI/ML" --limit 50 --verbose
uv run python cli.py list --status success
uv run python cli.py list --tag python

# Search links
uv run python cli.py search "machine learning"

# Remove a link
uv run python cli.py remove <url>
```

### Crawling

```bash
# Incremental crawl (only new links)
uv run python cli.py crawl

# Crawl from specific file
uv run python cli.py crawl -f my-links.md

# Reprocess all links
uv run python cli.py crawl --all

# Retry failed links
uv run python cli.py crawl --retry

# With TUI progress display
uv run python cli.py crawl --tui

# Adjust worker count
uv run python cli.py crawl --workers 10
```

### Viewing Collection

```bash
# Show statistics
uv run python cli.py stats

# List categories
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

# Import from markdown file
uv run python cli.py import bookmarks.md
```

### Static Site Generation

```bash
# Generate with defaults
uv run python cli.py generate

# Custom output directory and title
uv run python cli.py generate -o docs -t "My Reading List" -d "Curated tech articles"
```

## Configuration

Create a `.env` file with your LLM provider settings:

```env
# For LiteLLM (default)
LITELLM_API_KEY=your-api-key
LITELLM_MODEL=gpt-4o-mini

# For OpenRouter
OPENROUTER_API_KEY=your-openrouter-key
LLM_PROVIDER=openrouter
```

## Project Structure

```
link_organizer/
├── cli.py                     # CLI entry point
├── get_count_links.py         # Link extraction from markdown
├── enhanced_crawler.py        # Original enhanced crawler
├── enhanced_crawler_tui.py    # Crawler with TUI
├── src/
│   ├── __init__.py
│   ├── models.py              # Data models (LinkData, ClassificationResult, etc.)
│   ├── link_index.py          # Index management with incremental sync
│   ├── filename_generator.py  # Human-readable filename generation
│   ├── content_processor.py   # Content extraction (PDF, markdown)
│   ├── classification_service.py  # AI classification
│   ├── crawler_utils.py       # Crawling utilities
│   ├── incremental_crawler.py # Incremental crawl implementation
│   ├── static_site_generator.py   # HTML site generation
│   ├── workers.py             # Async worker implementations
│   ├── status_tracker.py      # Progress tracking
│   ├── tui.py                 # Terminal UI components
│   └── llm/                   # LLM provider abstraction
│       ├── __init__.py
│       ├── base.py
│       ├── litellm_provider.py
│       └── openrouter_provider.py
├── tests/
│   ├── test_classification.py
│   ├── test_link_classifier.py
│   ├── test_llm_providers.py
│   └── test_tui.py
├── dat/                       # Downloaded content storage
├── public/                    # Generated static site
├── links.md                   # Input links file
├── index.json                 # Link index with metadata
└── classifications.json       # Classification results
```

## Data Files

| File | Description |
|------|-------------|
| `links.md` | Input file containing URLs to process |
| `index.json` | Index of all links with status and classifications |
| `classifications.json` | Classification results for each link |
| `dat/` | Directory containing downloaded content |
| `public/` | Generated static site |

## Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

## Legacy Scripts

The original scripts are still available for backwards compatibility:

```bash
# Extract and count links
uv run python get_count_links.py

# Basic crawler
uv run python crawl_links.py

# Enhanced crawler with AI classification
uv run python enhanced_crawler.py

# Enhanced crawler with TUI
uv run python enhanced_crawler_tui.py
```

## License

MIT
