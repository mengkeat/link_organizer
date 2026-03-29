# AGENTS.md

## Project Overview

This is a Python-based link organizer that extracts links from markdown, crawls/downloads content for offline storage, classifies it with an LLM, and routes successful items into a topic memory system (Obsidian-compatible).

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation, including the consolidated 5-module structure.

## Data Structure

| File/Directory | Description |
|----------------|-------------|
| `links.md` | Primary input file with URLs to process |
| `memory/` | User-facing output directory (Obsidian vault style) |
| `memory/topics/` | Topic markdown files with grouped link entries |
| `memory/links/` | Canonical per-link markdown notes |
| `.cache/` | Hidden internal state directory |
| `.cache/index.json` | Master index with links, status, classifications |
| `.cache/dat/` | Raw downloaded content (HTML, PDFs) |
| `.cache/topic_index.db` | SQLite topic index with centroid vectors |

## Dependencies

- `crawl4ai` - Web crawling with async support
- `litellm` - LLM provider abstraction for classification & embeddings
- `requests` - HTTP requests for direct downloads (PDFs)
- `aiohttp` - OpenRouter direct API transport
- `PyPDF2` - PDF text extraction
- `pydantic` - Data validation and models
- `PyYAML` - Configuration management
- `numpy` - Vector math for semantic routing

## Python Environment

This project uses **uv** as the package manager with a local virtual environment in `.venv/`.
Python version requirement: **3.13+**.

```bash
# Install dependencies (creates .venv if needed)
uv pip install -e .

# Sync all links from links.md
link sync

# Run tests
uv run pytest
```

## CLI Commands

The primary interface is the `link` command (installed via `uv pip install -e .`):

### Primary Workflow
- `link sync`: Reads `links.md`, crawls new URLs, and routes them to `memory/`.
  - `--all`: Reprocess all links, even those already successful.
  - `-f, --file`: Specify a different input file instead of `links.md`.

### Utility Commands
- `link list`: Shows all links in the collection.
  - `--category`: Filter by AI-assigned category.
  - `--status`: Filter by status (Success/Failed).
- `link search <query>`: Search by keyword, tag, or category.
- `link stats`: Show collection statistics.
- `link export`: Export to JSON or URL list.

## Testing

```bash
uv run pytest                    # All tests
```

## Key Features

- **Markdown-First**: `links.md` is the only input you need to maintain.
- **Obsidian Integration**: The `memory/` directory is designed to be opened as an Obsidian vault.
- **Consolidated 5-Module Core**: Drastically simplified codebase for easier maintenance.
- **Hidden Cache**: Technical plumbing (indices, raw downloads) is kept out of sight in `.cache/`.
- **AI Classification & Routing**: Automatic semantic grouping of links based on LLM analysis.
