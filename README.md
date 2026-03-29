# Link Organizer

A streamlined tool for organizing, crawling, and classifying web links into an Obsidian-compatible markdown vault.

## Features

- **Markdown-First**: Uses `links.md` as the source of truth.
- **Automated Workflow**: A single `sync` command extracts, crawls, classifies, and routes links.
- **AI Classification**: Automatic categorization and tagging using LLMs (LiteLLM, OpenRouter).
- **Topic Routing**: Semantically groups links into topic-based markdown files.
- **Canonical Notes**: Generates individual markdown notes for every link with its full content.
- **Obsidian Ready**: Output is stored in `memory/` as clean Markdown with YAML frontmatter.

## Quick Start

1. **Install Dependencies**:
   ```bash
   uv pip install -e .
   ```

2. **Configure AI**:
   Create a `.env` file:
   ```env
   OPENROUTER_API_KEY=your-api-key
   ```

3. **Sync your links**:
   Add URLs to `links.md`, then run:
   ```bash
   link sync
   ```

## CLI Usage

### Primary Command
- `link sync`: Synchronizes `links.md` with your collection.
  - `--all`: Reprocess all links (even if already successful).
  - `-f, --file`: Use a different input file instead of `links.md`.

### Utility Commands
- `link list`: List all links in the collection.
  - `--category`: Filter by category.
  - `--status`: Filter by status (Success/Failed).
- `link search <query>`: Search your collection by keyword, tag, or category.
- `link stats`: Show collection statistics.
- `link export`: Export your collection to JSON or URL list.

## Directory Structure

- `links.md`: Your input file (add URLs here).
- `memory/`: Your output vault.
  - `links/`: Individual markdown notes for each crawled link.
  - `topics/`: Themed hubs grouping related links.
- `.cache/`: Internal state (hidden).
  - `dat/`: Raw downloaded content.
  - `index.json`: Link status and classification metadata.
  - `topic_index.db`: SQLite database for semantic routing.

## Configuration

Custom settings can be defined in `config.yaml`. See `config.yaml.example` for available options.

## License

MIT
