# Architecture

## Overview

The project is a CLI-first pipeline that turns Markdown link lists into an Obsidian-compatible note collection. It combines crawling, classification, topic routing, and local search on top of a small set of Python modules in `src/`.

## Entry Points

1. **`src/cli.py`**: main CLI implementation for the installed `link` command.
2. **`src/__main__.py`**: module entry point for `python -m src`.
3. **`cli.py`**: compatibility shim that forwards to `src.cli:main`.

## Source Modules

### `src/core.py`

- Defines application configuration using dataclasses.
- Loads optional `config.yaml` overrides.
- Centralizes logging.
- Holds shared Pydantic models such as `LinkData` and `ClassificationResult`.

### `src/index.py`

- Extracts URLs from Markdown input files.
- Manages the persisted link index stored in `.cache/index.json`.
- Provides the data access layer used by listing, stats, export, and incremental sync.
- The CLI detects when `memory/links/` contains notes not tracked in `.cache/index.json` and warns the user to re-sync.

### `src/crawler.py`

- Orchestrates sync execution over extracted links.
- Fetches HTML and PDF content.
- Saves downloaded artifacts under `.cache/dat/`.
- Coordinates classification and memory writes.

### `src/classifier.py`

- Handles AI-based content classification.
- Produces category, summary, tags, and other structured metadata.
- Uses provider-backed LLM calls configured from environment variables.

### `src/memory.py`

- Implements topic routing and Markdown output generation.
- Persists topic centroids in `.cache/topic_index.db`.
- Writes topic hubs to `memory/topics/` and canonical link notes to `memory/links/`.

### `src/search_documents.py`

- Walks the `memory/` tree and normalizes notes into searchable documents.
- Parses lightweight YAML-style frontmatter from generated Markdown notes.
- Distinguishes `link` versus `topic` note types based on directory layout.

### `src/search_index.py`

- Builds and updates the SQLite FTS5 text index in `.cache/search.db`.
- Tracks note modification times for incremental refresh.
- Executes ranked full-text search queries.

### `src/embeddings.py`

- Stores semantic embeddings in SQLite alongside search metadata.
- Calls an OpenAI-compatible embeddings endpoint.
- Implements vector normalization and cosine-similarity-based retrieval.

### `src/search.py`

- Provides the public search orchestration layer.
- Supports `text`, `semantic`, and `hybrid` modes.
- Refreshes the text index before search and falls back gracefully when semantic search is unavailable.

## Data Layout

The project keeps user-facing notes in `memory/` and implementation state in `.cache/`.

| File/Directory | Description |
|----------------|-------------|
| `links.md` | Default source file containing URLs to process. |
| `memory/` | User-facing Markdown vault. |
| `memory/topics/` | Topic hub notes with grouped link references. |
| `memory/links/` | Canonical per-link notes with summaries and captured content. |
| `.cache/` | Internal state directory. |
| `.cache/index.json` | Master index of link status and metadata. |
| `.cache/classifications.json` | Export of standalone classification results. |
| `.cache/dat/` | Downloaded raw content and related artifacts. |
| `.cache/topic_index.db` | SQLite topic centroid store for routing. |
| `.cache/search.db` | SQLite FTS and embedding store for local search. |

## Processing Pipeline

`link sync` runs the following high-level flow:

1. **Extract**: parse all supported URLs from `links.md` or a supplied input file.
2. **De-duplicate**: drop repeated links before any network work begins.
3. **Filter**: compare links against `.cache/index.json` to decide what should run incrementally.
4. **Fetch**: download and normalize source content from web pages or PDFs.
5. **Persist raw content**: save fetched artifacts into `.cache/dat/`.
6. **Classify**: generate summaries, tags, and category metadata using the configured LLM provider.
7. **Route**: compare embeddings against existing topic centroids in `.cache/topic_index.db`.
8. **Write notes**: create or update the Markdown outputs in `memory/links/` and `memory/topics/`.
9. **Update indexes**: persist the latest processing state and refresh the local search index as a best-effort follow-up step.

## Search Architecture

- **Text search**: uses SQLite FTS5 over normalized note content.
- **Semantic search**: stores embeddings in `.cache/search.db` and requires API credentials.
- **Hybrid search**: combines text and semantic ranking with reciprocal rank fusion.

## Test Coverage

- **`tests/test_config.py`**: configuration loading and defaults.
- **`tests/test_content_processor.py`**: content extraction and processing behavior.
- **`tests/test_link_classifier.py`**: classification result handling.
- **`tests/test_link_extractor.py`**: Markdown URL extraction.
- **`tests/test_llm_providers.py`**: LLM provider integrations.
- **`tests/test_memory_system.py`**: topic routing and Markdown note generation.
- **`tests/test_models.py`**: model validation.
- **`tests/test_search.py`**: search document parsing, indexing, and orchestration.
- **`tests/fixtures.py`**: shared fixtures and helpers.
