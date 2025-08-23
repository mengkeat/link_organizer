#!/usr/bin/env python3
"""
Enhanced Link Crawler with AI Classification
Extends the original crawler with automatic classification capabilities
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

from crawl4ai import AsyncWebCrawler
from get_count_links import extract_links_from_file
from src import (
    LinkData, CrawlerConfig, ClassificationService,
    fetch_worker, classification_worker
)

LINKS_MD = "links.md"



async def main_enhanced():
    """Enhanced main function with classification and retry queue"""
    load_dotenv()
    config = CrawlerConfig()
    os.makedirs(config.data_dir, exist_ok=True)
    
    links = extract_links_from_file(LINKS_MD)
    total = len(links)
    print(f"Found {total} links in {LINKS_MD}")

    classification_service = ClassificationService()
    
    fetch_queue = asyncio.Queue()
    classification_queue = asyncio.Queue()
    results = []
    failed_results = []
    failed_classifications = asyncio.Queue()

    for idx, link in enumerate(links):
        await fetch_queue.put((idx, link))

    classification_workers = [
        asyncio.create_task(
            classification_worker(
                classification_service, 
                classification_queue, 
                results, 
                failed_classifications,
                config
            )
        )
        for _ in range(config.classification_workers)
    ]

    async with AsyncWebCrawler() as crawler:
        fetch_workers = [
            asyncio.create_task(
                fetch_worker(
                    crawler, 
                    fetch_queue, 
                    classification_queue, 
                    failed_results, 
                    total, 
                    config
                )
            )
            for _ in range(config.fetch_workers)
        ]

        await fetch_queue.join()

        # Send sentinel values to terminate fetch workers
        for _ in range(config.fetch_workers):
            await fetch_queue.put((None, None))
        
        # Wait for workers to finish gracefully
        await asyncio.gather(*fetch_workers, return_exceptions=True)

    await classification_queue.join()

    for _ in range(config.classification_workers):
        await classification_queue.put(None)
    await asyncio.gather(*classification_workers)

    while not failed_classifications.empty():
        failed_results.append(await failed_classifications.get())

    all_results = results + failed_results
    index = [link_data.to_dict() for link_data in all_results]
    classifications = {
        link_data.link: link_data.classification
        for link_data in results 
        if link_data.classification
    }

    with open(config.index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    classification_service.save_classifications(
        classifications, 
        Path(config.classifications_file)
    )

    print(f"\nEnhanced crawling complete!")
    print(f"Processed {len(index)}/{total} links")
    print(f"Index saved to {config.index_file}")
    print(f"Classifications saved to {config.classifications_file}")

def main():
    """Entry point for enhanced crawler with classification capabilities."""
    asyncio.run(main_enhanced())

if __name__ == "__main__":
    main()