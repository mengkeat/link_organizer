# Architecture

## Core Architecture

The project has a modular architecture with CLI interface and the following components:

### Entry Points:
1. **`cli.py`** - Main CLI interface (`link` command) for all operations
2. **`get_count_links.py`** - Link extraction utility (deprecated, use `src.link_extractor`)
3. **`crawl_links.py`** - Basic crawler (deprecated, use CLI)
4. **`enhanced_crawler.py`** - Enhanced crawler (deprecated, use CLI)
5. **`enhanced_crawler_tui.py`** - Crawler with TUI (deprecated, use CLI with `--tui`)

### Core Modules (`src/` directory):

#### Configuration:
- **`config.py`** - Configuration management (YAML-based, with defaults)

#### Data Management:
- **`models.py`** - Pydantic data models with validation (LinkData, ClassificationResult, CrawlerConfig, etc.)
- **`link_index.py`** - Index management with incremental sync support
- **`filename_generator.py`** - Human-readable filename generation from URLs
- **`link_extractor.py`** - Link extraction from markdown files

#### Crawling & Processing:
- **`content_processor.py`** - Content extraction (PDF text, markdown, hashing)
- **`crawler_utils.py`** - Web crawling utilities (PDF download, HTML→markdown)
- **`unified_crawler.py`** - Unified crawler with all modes (incremental, TUI, classification)
- **`incremental_crawler.py`** - Incremental crawl (legacy, use UnifiedCrawler)
- **`workers.py`** - Async worker implementations

#### Classification:
- **`classification_service.py`** - AI-powered content classification
- **`llm/`** - LLM provider abstraction (LiteLLM, OpenRouter)

#### UI & Output:
- **`static_site_generator.py`** - HTML site generation from collection
- **`status_tracker.py`** - Progress tracking
- **`tui.py`** - Terminal User Interface components

#### Memory System (`src/memory/`):
- **`models.py`** - Pydantic models (TopicEntry, TopicIndex, MemoryLinkEntry)
- **`topic_index_manager.py`** - Topic index storage using SQLite (centroid vectors stored as BLOBs)
- **`memory_router.py`** - Routes links to topics based on embedding cosine similarity
- **`markdown_writer.py`** - Writes topic markdown files with link entries
- **`embedding_client.py`** - Embedding provider abstraction (LiteLLM)

### Test Components (`tests/` directory):
- **`test_config.py`** - Configuration tests
- **`test_content_processor.py`** - Content processor tests
- **`test_incremental_crawler.py`** - Crawler tests with mocks
- **`test_link_classifier.py`** - Unit tests for LinkClassifier
- **`test_link_extractor.py`** - Link extraction tests
- **`test_llm_providers.py`** - Unit tests for LLM providers
- **`test_models.py`** - Pydantic model validation tests
- **`test_tui.py`** - TUI testing with mock data
- **`test_memory_system.py`** - Memory system tests (index, router, immutability)
- **`test_build_search_docs.py`** - Search document generation tests
- **`fixtures.py`** - Shared test fixtures and mocks

## Data Structure

| File/Directory | Description |
|----------------|-------------|
| `links.md` | Input file with URLs to process |
| `index.json` | Master index with links, status, classifications |
| `classifications.json` | Classification results (backwards compat) |
| `dat/` | Downloaded content (readable filenames) |
| `public/` | Generated static HTML site |
| `memory/topic_index.db` | SQLite database storing topic centroids (embedding vectors as BLOBs) and metadata |
| `memory/topics/` | Topic markdown files with grouped link entries |

## Processing Pipeline

1. **Extract** - Parse URLs from markdown files
2. **Filter** - Skip already-processed links (incremental)
3. **Fetch** - Download content (HTML→markdown, PDF)
4. **Save** - Store with readable filename
5. **Classify** - AI categorization via LLM
6. **Index** - Update index.json with metadata
7. **Generate** - Create static HTML site (on demand)

## Memory System Pipeline

1. **Embed** - Generate embedding vector for link content via LLM
2. **Route** - Find best matching topic by cosine similarity against centroids in SQLite
3. **Match/Create** - Append to existing topic if similarity ≥ threshold, otherwise create new topic
4. **Update** - Update topic centroid using running average, persist to SQLite
5. **Write** - Append link entry to topic markdown file
