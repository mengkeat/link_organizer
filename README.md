# Link Organizer - Simplified

A simplified Python tool for crawling and organizing links from markdown files. 

*Lazy pasting links into Notion causes tracking to go out of hand - this tool organizes them.*

## Quick Start

1. **Setup environment:**
```bash
source ~/venv/linkenv/bin/activate
uv pip install -r requirements.txt
```

2. **Prepare your links:**
```bash
# Create links.md with your URLs (one per line or markdown format)
echo "https://example.com
https://github.com/anthropics/claude" > links.md
```

3. **Basic crawling:**
```bash
# Simple crawling without AI classification
python crawler.py

# With AI classification (requires .env with LLM keys)
python crawler.py --classify

# Adjust concurrency
python crawler.py --workers 8
```

## Key Features

- **Single unified crawler** - One script handles everything
- **Optional AI classification** - Enable with `--classify` flag  
- **SQLite database** - Lightweight storage with no ORM overhead
- **Controlled concurrency** - Configurable worker count
- **PDF and HTML support** - Handles both content types
- **Simple progress output** - No complex TUI, just clear logging

## Architecture

```
crawler.py          # Main unified crawler (RECOMMENDED)
get_count_links.py  # Extract links from markdown
src/
  ├── database.py   # SQLite operations  
  ├── models.py     # Data structures
  ├── classification.py  # AI classification
  └── llm/          # LLM providers
legacy/             # Old complex implementations
```

## Simple Workflow

1. **Extract links**: `python get_count_links.py` (optional - just to preview)
2. **Crawl basic**: `python crawler.py` 
3. **Crawl with AI**: `python crawler.py --classify`
4. **Check results**: Results saved to `index.json` and SQLite database

## Benefits of Simplification

- **Reduced complexity**: From 25 Python files to ~8 core files
- **Single entry point**: One `crawler.py` instead of 3 different crawlers
- **No over-engineering**: Removed complex worker systems, TUI, status tracking
- **Easy to understand**: Clear, linear processing flow
- **Still powerful**: All core functionality preserved

## Migration from Legacy

The old complex crawlers are moved to `legacy/` directory:
- `legacy/crawl_links.py` - Original basic crawler
- `legacy/enhanced_crawler.py` - Complex worker-based crawler  
- `legacy/enhanced_crawler_tui.py` - TUI version
- `legacy/src/` - Complex modular components (workers, TUI, etc.)

Use the new unified `crawler.py` for all future crawling needs.
