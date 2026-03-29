# Link Organizer

Link Organizer extracts URLs from Markdown, fetches and classifies their content, writes Obsidian-compatible notes into `memory/`, and builds local search indexes for those notes.

## Features

- **Markdown-first input**: `links.md` is the default source of truth for URLs.
- **End-to-end sync pipeline**: `link sync` extracts, fetches, classifies, routes, and writes notes in one run.
- **Obsidian-compatible output**: per-link notes are written to `memory/links/` and grouped topic hubs to `memory/topics/`.
- **Incremental processing**: processed links are tracked in `.cache/index.json` so future syncs can skip successful items.
- **Topic routing**: semantic topic assignment is stored in `.cache/topic_index.db`.
- **Local search**: full-text search uses SQLite FTS in `.cache/search.db`, with optional semantic and hybrid search modes.

## Requirements

- Python 3.13+
- `uv` for environment and package management
- An API key for classification and embeddings if you want AI-powered sync and semantic search

## Installation

Install the project in editable mode:

```bash
uv pip install -e .
```

Install test dependencies if you want to run the test suite:

```bash
uv pip install -e ".[dev]"
```

## Configuration

Create a `.env` file for provider credentials. In the current implementation:

- classification uses `OPENROUTER_API_KEY` or `LITELLM_API_KEY`
- semantic search uses `OPENROUTER_API_KEY` or `OPENAI_API_KEY`

```env
OPENROUTER_API_KEY=your-api-key
```

`config.yaml` is optional. If present, it overrides defaults in the application. See `config.yaml.example` for available settings, including:

- classification categories and content types
- crawler paths and worker counts
- memory output directories and topic routing settings
- search database path and default search mode

## Quick Start

Add URLs to `links.md`, then run:

```bash
link sync
```

That will populate `memory/`, update `.cache/index.json`, and refresh the local search index as a best-effort final step.

## CLI

The package installs the `link` command:

```bash
link --help
```

### `link sync`

Reads links from a Markdown file, crawls content, classifies it, writes notes, and refreshes the search index.

```bash
link sync
link sync --all
link sync --workers 10
link sync --file my_links.md
```

Options:

- `-f, --file`: use a file other than `links.md`
- `--all`: reprocess links even if they already succeeded earlier
- `--workers`: number of crawler workers to use; default is `5`

### `link list`

Lists indexed links from `.cache/index.json`. If notes exist in `memory/links/` that are not tracked by the index, a warning is printed suggesting `link sync --all` to re-sync.

```bash
link list
link list --status Success
link list --category "AI/ML" --limit 20
```

Options:

- `--category`: filter by classification category
- `--status`: filter by status text
- `--limit`: maximum number of results to print; default is `50`

### `link search <query>`

Searches notes in `memory/` using text, semantic, or hybrid search.

```bash
link search python
link search testing --mode text
link search embeddings --mode semantic
link search tutorial --mode hybrid --type link --limit 5
link search routing --mode text --type topic --rebuild
```

Options:

- `--mode {text,semantic,hybrid}`: search mode; default comes from config and is `text` unless overridden
- `--type {link,topic}`: restrict results to link notes or topic notes
- `--limit`: maximum number of results; default is `10`
- `--rebuild`: force a full rebuild of the text index before searching

Notes:

- `text` search uses SQLite FTS5 in `.cache/search.db`
- `semantic` search requires an embeddings API key and stores vectors in the same SQLite database
- `hybrid` search combines text and semantic rankings; if embeddings are unavailable it falls back to text results

### `link stats`

Shows aggregate counts from the link index.

```bash
link stats
```

### `link export`

Exports the current index either as structured JSON or a flat URL list.

```bash
link export
link export --format urls
link export --format json --output export.json
```

Options:

- `-f, --format {json,urls}`: export format; default is `json`
- `-o, --output`: write to a file instead of stdout

### `link reindex`

Rebuilds the local text search index from the Markdown notes already present in `memory/`.

```bash
link reindex
link reindex --rebuild
```

Options:

- `--rebuild`: force a full rebuild of `.cache/search.db`

## Directory Structure

- `links.md`: default input file containing URLs to process
- `memory/`: user-facing Markdown output
- `memory/links/`: canonical per-link notes
- `memory/topics/`: topic hub notes that group related links
- `.cache/`: internal state and local indexes
- `.cache/index.json`: master link status and metadata index
- `.cache/classifications.json`: standalone classification export
- `.cache/dat/`: downloaded raw content and artifacts
- `.cache/topic_index.db`: SQLite topic routing index
- `.cache/search.db`: SQLite search and embedding store

## Running Tests

```bash
uv run pytest
```

## Entry Points

- `link`: installed console script pointing to `src.cli:main`
- `python -m src`: module entry point
- `python cli.py`: compatibility shim for the CLI

## License

MIT
