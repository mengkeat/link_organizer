"""
Incremental crawler with support for better filenames and progress tracking
"""
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler

from .models import CrawlerConfig, LinkData
from .link_index import LinkIndex, IndexEntry
from .filename_generator import FilenameGenerator
from .content_processor import ContentProcessor
from .classification_service import ClassificationService
from .crawler_utils import CrawlerUtils


async def run_incremental_crawl(
    links: List[str],
    index: LinkIndex,
    use_tui: bool = False,
    workers: int = 5
):
    """
    Run incremental crawl on specified links.
    
    Args:
        links: List of URLs to process
        index: LinkIndex instance for tracking
        use_tui: Whether to show TUI progress
        workers: Number of concurrent workers
    """
    load_dotenv()
    config = CrawlerConfig(
        fetch_workers=workers,
        classification_workers=workers,
        enable_tui=use_tui
    )
    
    os.makedirs(config.data_dir, exist_ok=True)
    
    total = len(links)
    print(f"Processing {total} links...")
    
    classification_service = ClassificationService()
    
    # Track existing filenames to avoid collisions
    existing_filenames = {
        e.readable_filename for e in index.get_all() 
        if e.readable_filename
    }
    
    # Queue setup
    fetch_queue = asyncio.Queue()
    classification_queue = asyncio.Queue()
    results = []
    failed_results = []
    
    for idx, link in enumerate(links):
        await fetch_queue.put((idx, link))
    
    async def enhanced_fetch_worker(crawler, worker_id: int):
        """Fetch worker with readable filename support."""
        while True:
            try:
                idx, link = await asyncio.wait_for(fetch_queue.get(), timeout=2.0)
                if idx is None:
                    fetch_queue.task_done()
                    break
                
                print(f"[{idx+1}/{total}] Fetching: {link}")
                link_id = ContentProcessor.hash_link(link)
                
                try:
                    content, typ, screenshot_base64 = await CrawlerUtils.fetch_and_convert(crawler, link)
                    
                    if not content:
                        # Record failure
                        entry = IndexEntry(
                            link=link,
                            id=link_id,
                            status="Failed: No content",
                            crawled_at=datetime.now().isoformat()
                        )
                        index.add(entry)
                        failed_results.append(entry)
                        fetch_queue.task_done()
                        continue
                    
                    # Generate readable filename
                    readable_name = FilenameGenerator.generate_readable_filename(link, typ or "md")
                    readable_name = FilenameGenerator.make_unique_filename(readable_name, existing_filenames)
                    existing_filenames.add(readable_name)
                    
                    # Also keep hash-based filename for backwards compatibility
                    hash_filename = f"{link_id}.{typ}"
                    
                    # Save content with readable filename
                    filepath = os.path.join(config.data_dir, readable_name)
                    mode = "wb" if typ == "pdf" else "w"
                    encoding = None if typ == "pdf" else "utf-8"
                    
                    with open(filepath, mode, encoding=encoding) as f:
                        f.write(content)
                    
                    # Save screenshot if available
                    screenshot_filename = None
                    if screenshot_base64:
                        screenshot_filename = CrawlerUtils._save_screenshot(
                            screenshot_base64, link_id, config.data_dir
                        )
                    
                    # Create LinkData for classification
                    content_str = content if typ != "pdf" else f"PDF content ({len(content)} bytes)"
                    link_data = LinkData(
                        link=link,
                        id=link_id,
                        filename=hash_filename,
                        content=content_str,
                        screenshot_filename=screenshot_filename,
                        status="Fetched"
                    )
                    # Store readable filename as attribute
                    link_data.readable_filename = readable_name
                    
                    await classification_queue.put(link_data)
                    
                except Exception as e:
                    print(f"[{idx+1}/{total}] Failed: {link} - {e}")
                    entry = IndexEntry(
                        link=link,
                        id=link_id,
                        status=f"Failed: {e}",
                        crawled_at=datetime.now().isoformat()
                    )
                    index.add(entry)
                    failed_results.append(entry)
                
                fetch_queue.task_done()
                
            except asyncio.TimeoutError:
                if fetch_queue.empty():
                    break
            except asyncio.CancelledError:
                break
    
    async def enhanced_classification_worker(worker_id: int):
        """Classification worker that updates index."""
        while True:
            try:
                link_data = await asyncio.wait_for(classification_queue.get(), timeout=2.0)
                if link_data is None:
                    break
                
                print(f"Classifying: {link_data.link}")
                
                try:
                    title = ContentProcessor.generate_title_from_url(link_data.link)
                    classification = await classification_service.classify_content(
                        link_data.link, title, link_data.content
                    )
                    
                    # Create index entry
                    entry = IndexEntry(
                        link=link_data.link,
                        id=link_data.id,
                        filename=link_data.filename,
                        readable_filename=getattr(link_data, 'readable_filename', None),
                        status="Success",
                        crawled_at=datetime.now().isoformat(),
                        classification={
                            "category": classification.category,
                            "subcategory": classification.subcategory,
                            "tags": classification.tags,
                            "summary": classification.summary,
                            "confidence": classification.confidence,
                            "content_type": classification.content_type,
                            "difficulty": classification.difficulty,
                            "quality_score": classification.quality_score,
                            "key_topics": classification.key_topics,
                            "target_audience": classification.target_audience
                        },
                        screenshot_filename=link_data.screenshot_filename
                    )
                    index.add(entry)
                    results.append(entry)
                    
                    print(f"Success: {link_data.link} -> {entry.readable_filename} ({classification.category})")
                    
                except Exception as e:
                    print(f"Classification failed for {link_data.link}: {e}")
                    entry = IndexEntry(
                        link=link_data.link,
                        id=link_data.id,
                        filename=link_data.filename,
                        readable_filename=getattr(link_data, 'readable_filename', None),
                        status=f"Failed: Classification error - {e}",
                        crawled_at=datetime.now().isoformat(),
                        screenshot_filename=link_data.screenshot_filename
                    )
                    index.add(entry)
                    failed_results.append(entry)
                
                classification_queue.task_done()
                await asyncio.sleep(config.request_delay)
                
            except asyncio.TimeoutError:
                if classification_queue.empty():
                    break
            except asyncio.CancelledError:
                break
    
    # Start workers
    classification_workers_tasks = [
        asyncio.create_task(enhanced_classification_worker(i))
        for i in range(config.classification_workers)
    ]
    
    async with AsyncWebCrawler() as crawler:
        fetch_workers_tasks = [
            asyncio.create_task(enhanced_fetch_worker(crawler, i))
            for i in range(config.fetch_workers)
        ]
        
        await fetch_queue.join()
        
        # Send sentinel values
        for _ in range(config.fetch_workers):
            await fetch_queue.put((None, None))
        
        await asyncio.gather(*fetch_workers_tasks, return_exceptions=True)
    
    # Wait for classification to complete
    await classification_queue.join()
    
    for _ in range(config.classification_workers):
        await classification_queue.put(None)
    await asyncio.gather(*classification_workers_tasks, return_exceptions=True)
    
    # Save index
    index.save()
    
    # Also save classifications separately for backwards compatibility
    classifications = {}
    for entry in results:
        if entry.classification:
            classifications[entry.link] = entry.classification
    
    classifications_file = Path(config.classifications_file)
    existing_classifications = {}
    if classifications_file.exists():
        existing_classifications = json.loads(classifications_file.read_text())
    existing_classifications.update(classifications)
    classifications_file.write_text(json.dumps(existing_classifications, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 50)
    print("Crawling complete!")
    print(f"Processed: {len(results)} successful, {len(failed_results)} failed")
    print(f"Index saved to {config.index_file}")
    print(f"Classifications saved to {config.classifications_file}")
