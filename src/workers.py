"""
Async worker functions for concurrent crawling and classification operations
"""
import asyncio
from typing import List, Optional

from .models import LinkData, CrawlerConfig, ProcessingStage
from .crawler_utils import CrawlerUtils
from .classification_service import ClassificationService
from .content_processor import ContentProcessor
from .status_tracker import get_status_tracker


async def fetch_worker(crawler, fetch_queue: asyncio.Queue, classification_queue: asyncio.Queue, 
                      failed_results: List[LinkData], total: int, config: CrawlerConfig, 
                      worker_id: Optional[str] = None):
    """Worker that fetches content from URLs and queues them for classification"""
    if worker_id is None:
        worker_id = f"fetch-{id(asyncio.current_task())}"
    
    status_tracker = get_status_tracker() if config.enable_tui else None
    if status_tracker:
        status_tracker.register_worker(worker_id, "fetch")
        status_tracker.update_worker_status(worker_id, "idle")
    
    while True:
        try:
            if status_tracker:
                status_tracker.update_worker_status(worker_id, "idle")
            
            idx, link = await asyncio.wait_for(fetch_queue.get(), timeout=1.0)
            if idx is None:  # Sentinel value to terminate
                fetch_queue.task_done()
                break
            
            if status_tracker:
                status_tracker.update_worker_status(worker_id, "working", link)
                status_tracker.update_link_stage(link, ProcessingStage.FETCHING)
                
            link_data = await CrawlerUtils.fetch_link_content(crawler, link, idx, total, config.data_dir)
            
            if link_data.content and link_data.status == "Fetched":
                if status_tracker:
                    status_tracker.update_link_stage(link, ProcessingStage.FETCH_COMPLETE)
                await classification_queue.put(link_data)
            else:
                if status_tracker:
                    status_tracker.update_link_stage(link, ProcessingStage.FAILED)
                failed_results.append(link_data)
                
            fetch_queue.task_done()
        except asyncio.TimeoutError:
            # Check if queue is empty and all tasks are done
            if fetch_queue.empty():
                break
        except asyncio.CancelledError:
            break
        except Exception as e:
            if status_tracker:
                status_tracker.update_worker_status(worker_id, "error", f"Error: {e}")
                status_tracker.add_activity(f"Fetch worker error: {e}")
            print(f"Error in fetch worker for link {link}: {e}")
            fetch_queue.task_done()


async def classification_worker(classification_service: ClassificationService, 
                              classification_queue: asyncio.Queue,
                              results: List[LinkData], 
                              failed_queue: asyncio.Queue,
                              config: CrawlerConfig,
                              worker_id: Optional[str] = None):
    """Worker that processes classification tasks from a queue with retry logic"""
    if worker_id is None:
        worker_id = f"class-{id(asyncio.current_task())}"
    
    status_tracker = get_status_tracker() if config.enable_tui else None
    if status_tracker:
        status_tracker.register_worker(worker_id, "classification")
        status_tracker.update_worker_status(worker_id, "idle")
    
    while True:
        try:
            if status_tracker:
                status_tracker.update_worker_status(worker_id, "idle")
            
            link_data = await classification_queue.get()
            if link_data is None:
                break

            retries = getattr(link_data, 'retries', 0)
            
            if status_tracker:
                status_tracker.update_worker_status(worker_id, "working", link_data.link)
                status_tracker.update_link_stage(link_data.link, ProcessingStage.CLASSIFYING)
            
            print(f"Classifying: {link_data.link} (attempt {retries + 1})")

            try:
                title = ContentProcessor.generate_title_from_url(link_data.link)
                classification = await classification_service.classify_content(
                    link_data.link, title, link_data.content
                )

                link_data.classification = classification
                link_data.status = "Success"
                results.append(link_data)
                
                if status_tracker:
                    status_tracker.update_link_stage(link_data.link, ProcessingStage.SUCCESS)
                    status_tracker.update_queue_stats(completed_count=len(results))
                
                print(f"Success: {link_data.link} -> {link_data.filename} ({classification.category})")
                
            except Exception as e:
                print(f"Classification failed for {link_data.link}: {e}")
                
                if status_tracker:
                    status_tracker.add_activity(f"Classification failed: {e}")
                
                if retries < config.max_retries:
                    setattr(link_data, 'retries', retries + 1)
                    await classification_queue.put(link_data)
                    print(f"Re-queued {link_data.link} for retry.")
                else:
                    print(f"Max retries reached for {link_data.link}. Marking as failed.")
                    link_data.status = f"Failed: Max retries exceeded. Last error: {e}"
                    await failed_queue.put(link_data)
                    
                    if status_tracker:
                        status_tracker.update_link_stage(link_data.link, ProcessingStage.FAILED)
                    
            finally:
                classification_queue.task_done()
                await asyncio.sleep(config.request_delay)
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            if status_tracker:
                status_tracker.update_worker_status(worker_id, "error", f"Error: {e}")
                status_tracker.add_activity(f"Classification worker error: {e}")