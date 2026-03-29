# AGENTS.md

## Project Overview

This is a Python-based link organizer that extracts links from Markdown, crawls or downloads content for offline storage, classifies it with an LLM, writes Obsidian-compatible notes into `memory/`, and maintains local search indexes for those notes.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation covering the current CLI, pipeline, and search modules.

## Data Structure

| File/Directory | Description |
|----------------|-------------|
| `links.md` | Primary input file with URLs to process |
| `memory/` | User-facing output directory (Obsidian vault style) |
| `memory/topics/` | Topic markdown files with grouped link entries |
| `memory/links/` | Canonical per-link markdown notes |
| `.cache/` | Hidden internal state directory |
| `.cache/index.json` | Master index with links, status, classifications |
| `.cache/classifications.json` | Standalone classification export |
| `.cache/dat/` | Raw downloaded content (HTML, PDFs) |
| `.cache/topic_index.db` | SQLite topic index with centroid vectors |
| `.cache/search.db` | SQLite text search and embedding store |

## Dependencies

- `crawl4ai` - Web crawling with async support
- `litellm` - LLM provider abstraction for classification & embeddings
- `requests` - HTTP requests for direct downloads (PDFs)
- `aiohttp` - OpenRouter direct API transport
- `PyPDF2` - PDF text extraction
- `pydantic` - Data validation and models
- `PyYAML` - Optional `config.yaml` loading
- `numpy` - Vector math for topic routing and similarity
- `sqlite3` - Built-in persistence for topic routing and search indexes

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
  - `--workers`: Set the crawler worker count. Default: `5`.

### Utility Commands
- `link list`: Shows all links in the collection. Warns when `memory/links/` and `.cache/index.json` are out of sync.
  - `--category`: Filter by AI-assigned category.
  - `--status`: Filter by status (Success/Failed).
- `link search <query>`: Search by keyword, tag, or category.
  - `--mode {text|semantic|hybrid}`: Search mode.
  - `--type {link|topic}`: Restrict results by note type.
  - `--limit`: Maximum number of results to print.
  - `--rebuild`: Force a full text-index rebuild before searching.
- `link stats`: Show collection statistics.
- `link export`: Export to JSON or URL list.
  - `-f, --format {json|urls}`: Output format.
  - `-o, --output`: Write the export to a file.
- `link reindex`: Rebuild the local search index from existing `memory/` notes.
  - `--rebuild`: Force a full rebuild of `.cache/search.db`.

## Testing

```bash
uv run pytest                    # All tests
```

## Key Features

- **Markdown-First**: `links.md` is the only input you need to maintain.
- **Obsidian Integration**: The `memory/` directory is designed to be opened as an Obsidian vault.
- **CLI-First Workflow**: A single command drives extraction, crawling, classification, routing, and note generation.
- **Hidden Cache**: Technical plumbing (indices, raw downloads) is kept out of sight in `.cache/`.
- **AI Classification & Routing**: Automatic semantic grouping of links based on LLM analysis.
- **Local Search**: SQLite-backed text search plus optional semantic and hybrid search over generated notes.
