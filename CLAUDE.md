# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based link organizer tool that extracts links from a markdown file and crawls/downloads their content for offline storage and organization. The project helps organize links that were lazily pasted into Notion. The system uses a lightweight SQLite database with direct connections (no ORM) for optimal performance and simplicity.

## Core Architecture

The project has a modular architecture with the following components:

### Main Scripts:
1. **`get_count_links.py`** - Link extraction utility that parses markdown files to find URLs using regex patterns for both markdown-style links `[text](url)` and bare URLs
2. **`crawl_links.py`** - Original basic crawler that processes links using crawl4ai
3. **`enhanced_crawler.py`** - Enhanced crawler with AI classification capabilities and worker-based architecture
4. **`enhanced_crawler_tui.py`** - Enhanced crawler with Terminal User Interface (TUI) for live progress monitoring
5. **`link_classifier.py`** - Standalone link classification utility with LLM provider support

### Modular Components (`src/` directory):
- **`models.py`** - Dataclass-based models for LinkData, ClassificationResult, and TUI status tracking
- **`database.py`** - Lightweight SQLite database operations using direct sqlite3 connections with thread-local connection management
- **`classification_service.py`** - AI-powered content classification service using LLM providers
- **`collection_service.py`** - Smart link collection service with hierarchical clustering based on content embeddings
- **`content_processor.py`** - Content processing and text extraction utilities  
- **`crawler_utils.py`** - Web crawling utility functions
- **`workers.py`** - Async worker implementations for concurrent fetching and classification (with TUI status reporting)
- **`status_tracker.py`** - Centralized status tracking system for monitoring crawler progress
- **`tui.py`** - Rich terminal user interface components for live progress monitoring
- **`api.py`** - FastAPI web server for browser-based interface
- **`llm/`** - LLM provider abstraction layer supporting LiteLLM and OpenRouter APIs

### Test Components (`tests/` directory):
- **`test_classification_service.py`** - Unit tests for classification service functionality
- **`test_llm_providers.py`** - Unit tests for LLM provider implementations  
- **`test_tui.py`** - TUI testing script with mock data simulation
- **`test_build_search_docs.py`** - Unit tests for search documentation generation

### Supporting Scripts (`scripts/` directory):
- **`build_search_docs.py`** - Builds search index and documentation from processed links

## Data Structure & Storage

### Database Schema
The system uses a lightweight SQLite database (`links.db`) with the following tables:
- **`link_data`** - Core link information (id, url, filename, status, content, screenshot_filename, embedding)
- **`classification_results`** - AI classification data (category, subcategory, tags, summary, confidence, etc.)
- **`collections`** - User-defined and auto-generated collections
- **`link_collections`** - Many-to-many relationship between links and collections

### File Structure
- **Input**: `links.md` - Contains links to be processed (markdown format)
- **Database**: `links.db` - SQLite database with direct sqlite3 connections (no ORM)
- **Output Directory**: `dat/` - Stores processed content with SHA256-hashed filenames
- **Index Files**: `index.json`, `classifications.json` - Legacy JSON exports for compatibility
- **Search Interface**: `public/` - Web-based search interface files
  - `search.html` - Main search interface
  - `search-worker.js` - Web worker for search functionality
  - `search-data.js` - Generated search index data

## Dependencies

The project uses a minimal set of lightweight dependencies:

### Core Dependencies
- `crawl4ai` - Main web crawling library with async support
- `requests` - For PDF downloads and HTTP requests
- `litellm` - LLM provider abstraction layer for AI classification
- `python-dotenv` - Environment variable management
- `rich` - Terminal User Interface library for live progress monitoring
- `sentence-transformers` - For generating content embeddings for clustering
- `scipy` - Scientific computing library for hierarchical clustering
- `numpy` - Numerical computing support
- `fastapi` - Web framework for API server
- `uvicorn` - ASGI server for FastAPI

### Development Dependencies
- `pytest` - Testing framework
- `pytest-asyncio` - Async testing support

### Removed Dependencies
- ~~`sqlalchemy`~~ - Removed in favor of direct sqlite3 connections for better performance and simplicity

### Standard Library
- `sqlite3` - Database operations (built-in)
- `threading` - Thread-local database connections (built-in) 
- `hashlib`, `json`, `asyncio`, `urllib.parse`, `re`, `pathlib` - Core utilities (built-in)

## Python Environment

Environment can be activated with 
```bash
source ~/venv/linkenv/bin/activate
```

The UV python package manager is used. All installations of python packages to use 
```bash
uv pip ...
```

## Common Commands

### Installing Dependencies

Install from the requirements.txt file:

```bash
uv pip install -r requirements.txt
```

Or install manually:

```bash
uv pip install crawl4ai requests litellm python-dotenv rich sentence-transformers scipy numpy fastapi uvicorn pytest pytest-asyncio
```

### Running the Tools

#### Link Extraction and Analysis
```bash
# Extract and count links from markdown file
python get_count_links.py

# View links that will be processed
python get_count_links.py | head -20
```

#### Web Crawling
```bash
# Basic crawler (simple database operations)
python crawl_links.py

# Enhanced crawler with AI classification
python enhanced_crawler.py

# Enhanced crawler with Terminal User Interface (recommended)
python enhanced_crawler_tui.py

# Enhanced crawler without TUI (console mode)
python enhanced_crawler_tui.py --no-tui

# Adjust worker count for concurrent processing
python enhanced_crawler_tui.py --workers 10
```

#### Classification and Organization
```bash
# Standalone link classification (requires existing crawled content)
python link_classifier.py

# Generate smart collections using content clustering
python -c "from src.collection_service import CollectionService; cs = CollectionService(); cs.cluster_links()"

# Build search index for web interface
python scripts/build_search_docs.py
```

#### Web Interface
```bash
# Start web server (serves search interface and API)
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Access web interface at: http://localhost:8000
```

#### Database Operations
```bash
# Check database status and statistics
python -c "from src.database import db; links = db.get_all_links(); print(f'Total links: {len(links)}'); classified = [l for l in links if l.classification]; print(f'Classified: {len(classified)}')"

# View collections
python -c "from src.database import db; collections = db.get_all_collections(); [print(f'Collection {id}: {name}') for id, name, desc in collections]"

# Clean up failed links
python -c "from src.database import db; failed = db.get_links_by_status('Failed'); print(f'Failed links: {len(failed)}')"
```

### Testing

#### Run All Tests
```bash
# Run complete test suite
pytest

# Run with verbose output
pytest -v

# Run tests in parallel (faster)
pytest -n auto
```

#### Run Specific Test Categories
```bash
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only  
pytest -m "not slow"    # Skip slow tests
```

#### Run Specific Test Files
```bash
# Test database and classification service
pytest tests/test_classification_service.py -v

# Test LLM providers
pytest tests/test_llm_providers.py -v

# Test search document generation
pytest tests/test_build_search_docs.py -v
```

#### Test TUI Components
```bash
# Test TUI functionality with mock data
python tests/test_tui.py

# Test TUI components interactively
python -c "from tests.test_tui import main; main()"
```

#### Database Testing
```bash
# Test database operations directly
python -c "
from src.database import Database
import tempfile
import os

# Create test database
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
temp_db.close()
test_db = Database(temp_db.name)

print('✓ Database created successfully')
print(f'Tables: {[table[0] for table in test_db._get_connection().execute(\"SELECT name FROM sqlite_master WHERE type=\'table\'\").fetchall()]}')

# Cleanup
test_db.close()
os.unlink(temp_db.name)
print('✓ Test database cleaned up')
"
```

## Key Implementation Details

### Database Architecture
- **Direct SQLite connections** using `sqlite3` module (no ORM overhead)
- **Thread-local connection management** for safe concurrent access
- **Context manager pattern** for automatic transaction handling and rollback
- **Lightweight schema** with proper foreign key relationships and indexes
- **JSON serialization** for complex data types (tags, embeddings, etc.)

### Performance Features  
- **SHA256 hashing** for unique, deterministic filenames for processed content
- **Semaphore-based concurrency** with configurable worker limits
- **Async/await architecture** for non-blocking I/O operations
- **Thread-safe database operations** using connection pooling
- **Efficient content indexing** with selective field loading

### Content Processing
- **Dual format support** for both PDF and HTML content processing
- **Smart content extraction** excluding navigation, footer elements and external links
- **Content deduplication** using URL-based hashing
- **Screenshot capture** support for visual content archival

### AI Integration
- **Modular LLM provider system** supporting LiteLLM and OpenRouter APIs
- **Structured classification** with categories, subcategories, tags, and confidence scores
- **Content embeddings** for semantic similarity and smart clustering
- **Hierarchical clustering** for automatic collection generation using scipy

### User Interface
- **Rich Terminal UI** with real-time progress monitoring and queue status
- **Web-based search interface** with client-side search capabilities
- **RESTful API** for integration with other tools
- **Live activity logging** and worker status tracking

### Testing & Quality
- **Comprehensive test suite** with unit and integration tests
- **Mock providers** for testing AI classification without API calls
- **Temporary database fixtures** for isolated test environments
- **Async test support** with pytest-asyncio

## Terminal User Interface (TUI) Features

The `enhanced_crawler_tui.py` script provides a rich terminal interface for monitoring crawler progress in real-time:

### TUI Components:
- **Header**: Shows runtime, total links, completion counts
- **Queue Status**: Real-time queue sizes for fetch and classification operations
- **Worker Status**: Individual worker states (idle/working/error) and current tasks
- **Progress Summary**: Breakdown by processing stage with percentages
- **Recent Activities**: Live activity log showing processing events
- **Active Tasks**: Currently processing links by worker

### TUI Usage Examples:
```bash
# Run with TUI (default - recommended for interactive use)
python enhanced_crawler_tui.py

# Run without TUI (console mode - better for logging/automation)
python enhanced_crawler_tui.py --no-tui

# Adjust concurrent worker counts
python enhanced_crawler_tui.py --workers 10 --classification-workers 5

# Test TUI with mock data (development/demo)
python tests/test_tui.py
```

### Processing Stages Tracked:
- `PENDING` - Link queued but not started
- `FETCHING` - Currently downloading content
- `FETCH_COMPLETE` - Content downloaded, ready for classification
- `CLASSIFYING` - AI classification in progress  
- `SUCCESS` - Processing completed successfully
- `FAILED` - Processing failed after retries

## Complete Workflow Guide

### 1. Initial Setup
```bash
# Activate environment and install dependencies
source ~/venv/linkenv/bin/activate
uv pip install -r requirements.txt

# Verify setup
python -c "from src.database import db; print('✓ Database initialized successfully')"
```

### 2. Prepare Links for Processing
```bash
# Create or update links.md with your links
echo "https://example.com/article1
https://example.com/article2" > links.md

# Verify link extraction
python get_count_links.py
```

### 3. Crawl and Process Links
```bash
# Option A: Enhanced crawler with TUI (recommended for interactive sessions)
python enhanced_crawler_tui.py

# Option B: Enhanced crawler without TUI (better for automation/scripts)  
python enhanced_crawler_tui.py --no-tui

# Option C: Basic crawler (simple, no AI classification)
python crawl_links.py
```

### 4. Verify and Analyze Results
```bash
# Check processing status
python -c "
from src.database import db
links = db.get_all_links()
print(f'Total links: {len(links)}')
by_status = {}
for link in links:
    status = link.status
    by_status[status] = by_status.get(status, 0) + 1
for status, count in by_status.items():
    print(f'  {status}: {count}')
"

# View successful classifications
python -c "
from src.database import db
classified = [l for l in db.get_all_links() if l.classification]
print(f'Successfully classified: {len(classified)}')
for link in classified[:5]:  # Show first 5
    print(f'  {link.link}: {link.classification.category}')
"
```

### 5. Generate Collections and Search Index
```bash
# Create smart collections using content clustering
python -c "
from src.collection_service import CollectionService
cs = CollectionService()
cs.cluster_links()
print('✓ Collections generated')
"

# Build search index for web interface
python scripts/build_search_docs.py
```

### 6. Launch Web Interface
```bash
# Start the web server
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Open browser to http://localhost:8000 for search interface
```

### 7. Maintenance and Troubleshooting
```bash
# View database statistics
python -c "
from src.database import db
import os
db_size = os.path.getsize('links.db') / 1024 / 1024
print(f'Database size: {db_size:.2f} MB')
"

# Clean up failed links (optional)
python -c "
from src.database import db
failed = db.get_links_by_status('Failed')
print(f'Found {len(failed)} failed links')
# Remove them if needed:
# for link in failed:
#     with db.get_connection() as conn:
#         conn.execute('DELETE FROM link_data WHERE id = ?', (link.id,))
"

# Re-run classification on successful fetches without classification
python -c "
import asyncio
from src.classification_service import ClassificationService
async def reclassify():
    cs = ClassificationService()
    await cs.classify_pending_links()
asyncio.run(reclassify())
"
```

## Troubleshooting

### Common Issues

**Database locked errors:**
- The database uses thread-local connections, but if you see lock errors, ensure only one crawler process is running at a time.

**Memory issues with large link sets:**
- Reduce worker counts: `python enhanced_crawler_tui.py --workers 3 --classification-workers 2`
- Process in smaller batches by splitting `links.md`

**API rate limiting:**
- Increase delays in crawler configuration
- Use different LLM providers (OpenRouter has higher limits than OpenAI)

**Test failures:**
- Ensure no other process is using the database during tests
- Run `pytest tests/ -v` to see detailed test output

### Performance Tuning

**For faster processing:**
```bash
# Increase worker counts (if system can handle it)
python enhanced_crawler_tui.py --workers 15 --classification-workers 8

# Use faster LLM models (in .env file)
# LLM_PROVIDER=litellm
# LLM_MODEL=gpt-3.5-turbo  # faster than gpt-4
```

**For stability with limited resources:**
```bash
# Reduce concurrency
python enhanced_crawler_tui.py --workers 3 --classification-workers 2

# Use local/smaller models if available
# LLM_PROVIDER=litellm  
# LLM_MODEL=ollama/llama2  # if running Ollama locally
```