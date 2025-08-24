#!/usr/bin/env python3
"""
Enhanced Link Crawler with TUI Support
Terminal User Interface version of the enhanced crawler
"""

import os
import json
import asyncio
import argparse
from pathlib import Path
from dotenv import load_dotenv

from crawl4ai import AsyncWebCrawler
from get_count_links import extract_links_from_file
from src import (
    CrawlerConfig, ClassificationService, ProcessingStage,
    fetch_worker, classification_worker, get_status_tracker, CrawlerTUI
)

LINKS_MD = "links.md"


async def update_queue_stats(fetch_queue, classification_queue, results, failed_results, total):
    """Periodically update queue statistics for TUI display."""
    status_tracker = get_status_tracker()
    
    while True:
        try:
            status_tracker.update_queue_stats(
                fetch_queue_size=fetch_queue.qsize(),
                classification_queue_size=classification_queue.qsize(),
                completed_count=len(results),
                failed_count=len(failed_results),
                total_count=total
            )
            await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            break


async def main_enhanced_tui(enable_tui: bool = True):
    """Enhanced main function with optional TUI support for real-time monitoring."""
    load_dotenv()
    config = CrawlerConfig(enable_tui=enable_tui)
    os.makedirs(config.data_dir, exist_ok=True)
    
    links = extract_links_from_file(LINKS_MD)
    total = len(links)
    
    # Initialize status tracker
    status_tracker = get_status_tracker()
    status_tracker.queue_stats.total_count = total
    
    # Initialize all links as pending
    for link in links:
        status_tracker.update_link_stage(link, ProcessingStage.PENDING)
    
    print(f"Found {total} links in {LINKS_MD}")
    status_tracker.add_activity(f"Starting crawler with {total} links")

    classification_service = ClassificationService()
    
    fetch_queue = asyncio.Queue()
    classification_queue = asyncio.Queue()
    results = []
    failed_results = []
    failed_classifications = asyncio.Queue()

    # Fill fetch queue
    for idx, link in enumerate(links):
        await fetch_queue.put((idx, link))

    # Setup TUI if enabled
    tui = CrawlerTUI(status_tracker) if enable_tui else None
    
    if tui:
        async with tui.live_context():
            await run_crawler(
                classification_service, config, fetch_queue, classification_queue,
                results, failed_results, failed_classifications, total
            )
    else:
        await run_crawler(
            classification_service, config, fetch_queue, classification_queue,
            results, failed_results, failed_classifications, total
        )

    # Process failed classifications
    while not failed_classifications.empty():
        failed_results.append(await failed_classifications.get())

    # Save results
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

    if tui:
        tui.print_summary()
    else:
        print("\nEnhanced crawling complete!")
        print(f"Processed {len(index)}/{total} links")
        print(f"Index saved to {config.index_file}")
        print(f"Classifications saved to {config.classifications_file}")


async def run_crawler(classification_service, config, fetch_queue, classification_queue,
                     results, failed_results, failed_classifications, total):
    """Run crawler workers with fetch and classification tasks."""
    
    # Start queue stats updater if TUI is enabled
    stats_task = None
    if config.enable_tui:
        stats_task = asyncio.create_task(
            update_queue_stats(fetch_queue, classification_queue, results, failed_results, total)
        )

    # Create classification workers with unique IDs
    classification_workers = [
        asyncio.create_task(
            classification_worker(
                classification_service, 
                classification_queue, 
                results, 
                failed_classifications,
                config,
                worker_id=f"classifier-{i+1}"
            )
        )
        for i in range(config.classification_workers)
    ]

    async with AsyncWebCrawler() as crawler:
        # Create fetch workers with unique IDs
        fetch_workers = [
            asyncio.create_task(
                fetch_worker(
                    crawler, 
                    fetch_queue, 
                    classification_queue, 
                    failed_results, 
                    total, 
                    config,
                    worker_id=f"fetcher-{i+1}"
                )
            )
            for i in range(config.fetch_workers)
        ]

        await fetch_queue.join()

        # Send sentinel values to terminate fetch workers
        for _ in range(config.fetch_workers):
            await fetch_queue.put((None, None))
        
        # Wait for workers to finish gracefully
        await asyncio.gather(*fetch_workers, return_exceptions=True)

    await classification_queue.join()

    # Terminate classification workers
    for _ in range(config.classification_workers):
        await classification_queue.put(None)
    await asyncio.gather(*classification_workers)

    # Stop stats updater
    if stats_task:
        stats_task.cancel()
        try:
            await stats_task
        except asyncio.CancelledError:
            pass


def main():
    """Main entry point with command line argument parsing for TUI crawler."""
    parser = argparse.ArgumentParser(description="Enhanced Link Crawler with TUI")
    parser.add_argument("--no-tui", action="store_true", 
                       help="Disable TUI and run in console mode")
    parser.add_argument("--workers", type=int, default=5,
                       help="Number of worker threads (default: 5)")
    
    args = parser.parse_args()
    
    # Override config if workers specified
    if args.workers != 5:
        from src.models import CrawlerConfig
        CrawlerConfig.fetch_workers = args.workers
        CrawlerConfig.classification_workers = args.workers
    
    enable_tui = not args.no_tui
    asyncio.run(main_enhanced_tui(enable_tui))


if __name__ == "__main__":
    main()