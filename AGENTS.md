# AGENTS.md

## Project Overview

This is a Python-based link organizer that extracts links from markdown, crawls/downloads content for offline storage, classifies it with an LLM, and routes successful items into a topic memory system.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation, including module descriptions, data structure, and processing pipelines.

## Data Structure

| File/Directory | Description |
|----------------|-------------|
| `links.md` | Input file with URLs to process |
| `index.json` | Master index with links, status, classifications |
| `classifications.json` | Standalone classification export |
| `dat/` | Downloaded content (readable filenames) |
| `memory/topic_index.db` | SQLite topic index with centroid vectors |
| `memory/topics/` | Topic markdown files with grouped link entries |
| `memory/links/` | Canonical per-link markdown notes |
| `public/` | Generated static HTML site |

## Dependencies

- `crawl4ai` - Web crawling with async support
- `requests` - HTTP requests, PDF downloads
- `litellm` - LLM provider abstraction
- `python-dotenv` - Environment config
- `rich` - Terminal UI
- `aiohttp` - OpenRouter direct API transport
- `PyPDF2` - PDF text extraction
- `Pillow` - Screenshot processing
- `pydantic` - Data validation
- `numpy` - Embedding vector math
- `PyYAML` - Config loading
- `pytest` - Testing

## Python Environment

This project uses **uv** as the package manager with a local virtual environment in `.venv/`.
Python version requirement: **3.13+**.

```bash
# Install dependencies (creates .venv if needed)
uv pip install -e .

# Run any python file
uv run python <script.py>

# Add new packages
uv pip install <package>

# Run tests
uv run pytest
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

### Memory Commands

```bash
# Route one or more URLs directly into memory
uv run python cli.py memory-add https://example.com/article
uv run python cli.py memory-add https://example.com/a https://example.com/b -t "Optional title"

# List current memory topics
uv run python cli.py memory-topics
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

## Testing

```bash
uv run pytest                    # All tests
uv run pytest -m unit            # Unit tests only
uv run pytest -m integration     # Integration tests
uv run pytest -m "not slow"      # Skip slow tests

# Useful sanity checks used in this workspace
uv run python cli.py crawl --workers 1
uv run python cli.py crawl --all --workers 1
```

## Key Features

- **Incremental Sync**: Only processes new/failed links
- **Readable Filenames**: `arxiv-2105-00613.pdf` instead of SHA256 hashes
- **AI Classification**: Category, tags, summary, difficulty, quality score
- **Memory Routing**: Topic-based memory sync using embedding similarity
- **Canonical Notes**: One markdown note per link under `memory/links/`
- **Static Site**: Browsable HTML with categories and search
- **Multiple Export Formats**: JSON, Markdown, URL list
- **TUI Progress**: Real-time crawl monitoring

## Processing Pipeline

1. **Extract** - Parse URLs from markdown files
2. **Filter** - Skip already-processed links (incremental)
3. **Fetch** - Download content (HTML→markdown, PDF)
4. **Save** - Store with readable filename
5. **Classify** - AI categorization via LLM
6. **Memory** - Route to topics and write canonical per-link note
7. **Index** - Update `index.json` with crawl/classification/memory metadata
8. **Generate** - Create static HTML site (on demand)