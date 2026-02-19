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
- **Topic Memory Sync**: After classification, links are routed into topic memory using tags/key topics
- **Canonical Link Notes**: Each crawled link gets a markdown note with full converted content

## Installation

```bash
# Clone the repository
git clone https://github.com/mengkeat/link_organizer.git
cd link_organizer

# Install dependencies with uv (creates/uses .venv)
uv pip install -e .
```

Requirements:
- Python 3.13+
- `uv`

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

```bash
# Show all commands
uv run python cli.py --help

# Show help for memory commands
uv run python cli.py memory-add --help
uv run python cli.py memory-topics --help
```

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

### Memory (Topics + Link Notes)

```bash
# Recommended: crawl first (this now auto-routes to memory)
uv run python cli.py crawl

# Add one or more URLs directly into memory router
uv run python cli.py memory-add https://example.com/article
uv run python cli.py memory-add https://example.com/a https://example.com/b -t "Optional Title"

# List current memory topics
uv run python cli.py memory-topics
```

Memory behavior after crawl:
- Successful classification automatically routes links into topic memory.
- Topic notes are written to `memory/topics/`.
- Canonical per-link markdown notes (with converted content) are written to `memory/links/`.
- Memory linkage metadata is stored in `index.json` (`memory_topic_id`, `memory_topic_file`, `memory_link_file`, `memory_error`).

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
# Required by current provider factory
OPENROUTER_API_KEY=your-api-key

# Optional provider selection (defaults to litellm)
LLM_PROVIDER=litellm

# Optional model override (used by classification provider)
LITELLM_MODEL=openrouter/openai/gpt-4

# Optional OpenRouter metadata (when provider=openrouter)
OPENROUTER_REFERER=https://github.com/your-app
OPENROUTER_TITLE=Link Organizer
```

You can also copy `config.yaml.example` to `config.yaml` to customize crawler/memory defaults.

## Data Files

| File | Description |
|------|-------------|
| `links.md` | Input file containing URLs to process |
| `index.json` | Index of all links with status and classifications |
| `classifications.json` | Standalone classification export used by search/build tooling |
| `dat/` | Directory containing downloaded content |
| `memory/topic_index.db` | Topic centroid index used for semantic routing |
| `memory/topics/` | Topic hub markdown files with grouped references |
| `memory/links/` | Per-link canonical markdown notes containing converted content |
| `public/` | Generated static site |

## Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest -m unit
uv run pytest -m integration
uv run pytest -m "not slow"
```

## License

MIT
