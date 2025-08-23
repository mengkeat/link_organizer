#!/usr/bin/env python3
"""
Simple TUI test with mock data
"""
import asyncio
import time
import sys
from pathlib import Path

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from src import StatusTracker, CrawlerTUI, ProcessingStage

async def mock_processing_simulation():
    """Simulate processing with mock data for TUI testing and demonstration."""
    status_tracker = StatusTracker()
    tui = CrawlerTUI(status_tracker)
    
    # Initialize mock data
    test_links = [
        "https://example.com/link1",
        "https://example.com/link2", 
        "https://example.com/link3",
        "https://example.com/link4",
        "https://example.com/link5"
    ]
    
    status_tracker.queue_stats.total_count = len(test_links)
    
    # Register mock workers
    for i in range(3):
        status_tracker.register_worker(f"fetcher-{i+1}", "fetch")
        status_tracker.register_worker(f"classifier-{i+1}", "classification")
    
    # Initialize links as pending
    for link in test_links:
        status_tracker.update_link_stage(link, ProcessingStage.PENDING)
    
    async with tui.live_context():
        status_tracker.add_activity("Starting mock processing simulation")
        
        # Simulate processing each link
        for i, link in enumerate(test_links):
            worker_id = f"fetcher-{(i % 3) + 1}"
            
            # Fetch stage
            status_tracker.update_worker_status(worker_id, "working", link)
            status_tracker.update_link_stage(link, ProcessingStage.FETCHING)
            status_tracker.update_queue_stats(fetch_queue_size=len(test_links) - i - 1)
            await asyncio.sleep(2)
            
            # Classification stage
            class_worker_id = f"classifier-{(i % 3) + 1}"
            status_tracker.update_worker_status(worker_id, "idle")
            status_tracker.update_link_stage(link, ProcessingStage.FETCH_COMPLETE)
            status_tracker.update_worker_status(class_worker_id, "working", link)
            status_tracker.update_link_stage(link, ProcessingStage.CLASSIFYING)
            status_tracker.update_queue_stats(classification_queue_size=len(test_links) - i - 1)
            await asyncio.sleep(2)
            
            # Complete
            status_tracker.update_worker_status(class_worker_id, "idle")
            status_tracker.update_link_stage(link, ProcessingStage.SUCCESS)
            status_tracker.update_queue_stats(
                completed_count=i + 1,
                classification_queue_size=max(0, len(test_links) - i - 2)
            )
            status_tracker.add_activity(f"Completed processing: {link}")
            await asyncio.sleep(1)
    
    tui.print_summary()

if __name__ == "__main__":
    print("Starting TUI test simulation...")
    print("This will show a live dashboard for ~20 seconds")
    print("Press Ctrl+C to exit early")
    
    try:
        asyncio.run(mock_processing_simulation())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    
    print("TUI test completed!")