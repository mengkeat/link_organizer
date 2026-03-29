# Architecture

## Core Architecture

The project is structured as a consolidated pipeline with five core modules in the `src/` directory. It uses a single CLI entry point (`cli.py`) to manage the entire workflow.

### Entry Points
1. **`cli.py`** - Main CLI interface (`link` command) for all user operations.

### Core Modules (`src/` directory)

#### 1. `src/core.py` (Configuration & Base Models)
- Merges configuration management (YAML-based) and Pydantic data models (`LinkData`, `ClassificationResult`, etc.).
- Centralizes logging and environment setup.

#### 2. `src/index.py` (Link Index & Extraction)
- Manages the `LinkIndex` (the master record of processed links) and the `LinkExtractor`.
- Responsible for parsing `links.md` (or any other markdown file) for new URLs.

#### 3. `src/crawler.py` (Crawling & Processing)
- Merges the `UnifiedCrawler`, `ContentProcessor`, and `FilenameGenerator`.
- Handles fetching web content (via `crawl4ai` for HTML or `requests` for PDFs), extracting text, and generating human-readable filenames.

#### 4. `src/classifier.py` (AI Classification)
- Merges the `ClassificationService` and LLM provider abstractions (`LiteLLM`, `OpenRouter`).
- Uses LLM prompts to categorize links, generate summaries, and assign tags.

#### 5. `src/memory.py` (Obsidian Memory System)
- Merges the topic memory system, including the `MemoryRouter`, `TopicIndexManager` (SQLite-based), and Markdown writers.
- Routes new links into topic hubs (`memory/topics/`) and creates individual canonical link notes (`memory/links/`) with full content.

### Test Components (`tests/` directory)
- **`test_config.py`** - Configuration and core model tests.
- **`test_content_processor.py`** - Text and PDF processing tests.
- **`test_link_classifier.py`** - AI classification logic tests.
- **`test_link_extractor.py`** - URL parsing from markdown tests.
- **`test_llm_providers.py`** - LLM backend provider tests.
- **`test_models.py`** - Pydantic model validation tests.
- **`test_memory_system.py`** - Topic routing and markdown output tests.
- **`fixtures.py`** - Shared test fixtures and mocks.

## Data Structure

The project hides internal complexity by using a `.cache/` directory, while keeping the user-facing output in `memory/`.

| File/Directory | Description |
|----------------|-------------|
| `links.md` | Primary source of truth for all links. |
| `memory/` | The user's Markdown vault (ready for Obsidian). |
| `memory/topics/` | Topic hub files grouping related link references. |
| `memory/links/` | Detailed individual link notes with full content. |
| `.cache/` | **Hidden** internal state directory. |
| `.cache/index.json` | Master index mapping URLs to their processing status and metadata. |
| `.cache/dat/` | Stored raw downloaded files (HTML/PDF). |
| `.cache/topic_index.db` | SQLite database storing topic centroid vectors for semantic matching. |

## Processing Pipeline

The `link sync` command executes the following 7-step pipeline:

1. **Extract**: Parse all URLs from `links.md`.
2. **Filter**: Compare URLs against `.cache/index.json` to identify new or failed links.
3. **Fetch**: Download content (HTML converted to Markdown, or raw PDFs).
4. **Save**: Persist the raw content into `.cache/dat/` using human-readable filenames.
5. **Classify**: Send content samples to the LLM for categorization, tagging, and summarization.
6. **Route**: Use embedding similarity to assign the link to an existing or new topic hub.
7. **Write**: Generate the canonical link note and append the backlink to the relevant topic hub in `memory/`.
8. **Finalize**: Update the index to ensure subsequent runs skip these links.
