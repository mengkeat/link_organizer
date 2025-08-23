"""
Async worker functions for concurrent crawling and classification operations
"""
import asyncio
from typing import List

from .models import LinkData, CrawlerConfig
from .crawler_utils import CrawlerUtils
from .classification_service import ClassificationService
from .content_processor import ContentProcessor


async def fetch_worker(crawler, fetch_queue: asyncio.Queue, classification_queue: asyncio.Queue, 
                      failed_results: List[LinkData], total: int, config: CrawlerConfig):
    """Worker that fetches content from URLs and queues them for classification"""
    while True:
        try:
            idx, link = await asyncio.wait_for(fetch_queue.get(), timeout=1.0)
            if idx is None:  # Sentinel value to terminate
                fetch_queue.task_done()
                break
                
            link_data = await CrawlerUtils.fetch_link_content(crawler, link, idx, total, config.data_dir)
            
            if link_data.content and link_data.status == "Fetched":
                await classification_queue.put(link_data)
            else:
                failed_results.append(link_data)
                
            fetch_queue.task_done()
        except asyncio.TimeoutError:
            # Check if queue is empty and all tasks are done
            if fetch_queue.empty():
                break
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in fetch worker for link {link}: {e}")
            fetch_queue.task_done()


async def classification_worker(classification_service: ClassificationService, 
                              classification_queue: asyncio.Queue,
                              results: List[LinkData], 
                              failed_queue: asyncio.Queue,
                              config: CrawlerConfig):
    """Worker that processes classification tasks from a queue with retry logic"""
    while True:
        try:
            link_data = await classification_queue.get()
            if link_data is None:
                break

            retries = getattr(link_data, 'retries', 0)
            print(f"Classifying: {link_data.link} (attempt {retries + 1})")

            try:
                title = ContentProcessor.generate_title_from_url(link_data.link)
                classification = await classification_service.classify_content(
                    link_data.link, title, link_data.content
                )

                link_data.classification = classification
                link_data.status = "Success"
                results.append(link_data)
                
                print(f"Success: {link_data.link} -> {link_data.filename} ({classification.category})")
                
            except Exception as e:
                print(f"Classification failed for {link_data.link}: {e}")
                
                if retries < config.max_retries:
                    setattr(link_data, 'retries', retries + 1)
                    await classification_queue.put(link_data)
                    print(f"Re-queued {link_data.link} for retry.")
                else:
                    print(f"Max retries reached for {link_data.link}. Marking as failed.")
                    link_data.status = f"Failed: Max retries exceeded. Last error: {e}"
                    await failed_queue.put(link_data)
                    
            finally:
                classification_queue.task_done()
                await asyncio.sleep(config.request_delay)
                
        except asyncio.CancelledError:
            break