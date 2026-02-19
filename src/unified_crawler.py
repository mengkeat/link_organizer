"""
Unified crawler module that combines all crawling functionality.
"""
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from dotenv import load_dotenv
from crawl4ai import AsyncWebCrawler

from .models import CrawlerConfig, LinkData, ProcessingStage
from .link_index import LinkIndex, IndexEntry
from .filename_generator import FilenameGenerator
from .content_processor import ContentProcessor
from .classification_service import ClassificationService
from .crawler_utils import CrawlerUtils
from .status_tracker import get_status_tracker
from .tui import CrawlerTUI
from .config import get_config
from .logging_config import get_logger
from .memory.embedding_client import LiteLLMEmbeddingClient
from .memory.link_writer import LinkMarkdownWriter
from .memory.markdown_writer import MarkdownWriter
from .memory.memory_router import MemoryRouter
from .memory.models import MemoryLinkEntry
from .memory.topic_index_manager import TopicIndexManager

logger = get_logger("unified_crawler")


class UnifiedCrawler:
    """
    Unified crawler that supports all crawling modes:
    - Basic crawling (fetch and save content)
    - Classification (AI-powered categorization)
    - TUI (terminal user interface for progress)
    - Incremental mode (skip already processed links)
    """

    def __init__(
        self,
        incremental: bool = True,
        use_tui: bool = False,
        enable_classification: bool = True,
        workers: int = 5,
        data_dir: str = "dat",
        index_file: str = "index.json",
        classifications_file: str = "classifications.json",
        max_retries: int = 3,
        request_delay: float = 1.0,
    ):
        """
        Initialize the unified crawler.

        Args:
            incremental: Whether to skip already processed links
            use_tui: Whether to show TUI progress display
            enable_classification: Whether to classify content using AI
            workers: Number of concurrent workers for fetching and classification
            data_dir: Directory to store downloaded content
            index_file: Path to the index JSON file
            classifications_file: Path to store classifications
            max_retries: Maximum retries for failed classifications
            request_delay: Delay between classification requests
        """
        self.incremental = incremental
        self.use_tui = use_tui
        self.enable_classification = enable_classification
        self.workers = workers

        self.config = CrawlerConfig(
            data_dir=data_dir,
            index_file=index_file,
            classifications_file=classifications_file,
            max_retries=max_retries,
            fetch_workers=workers,
            classification_workers=workers,
            request_delay=request_delay,
            enable_tui=use_tui,
        )

        self._classification_service: Optional[ClassificationService] = None
        self._index: Optional[LinkIndex] = None
        self._memory_router: Optional[MemoryRouter] = None
        self._memory_writer: Optional[MarkdownWriter] = None
        self._memory_index_manager: Optional[TopicIndexManager] = None
        self._link_writer: Optional[LinkMarkdownWriter] = None
        self._memory_init_error: Optional[str] = None
        self._memory_link_note_max_chars: int = 120000

    @property
    def classification_service(self) -> ClassificationService:
        """Lazy-load classification service."""
        if self._classification_service is None:
            self._classification_service = ClassificationService()
        return self._classification_service

    def get_index(self) -> LinkIndex:
        """Get or create LinkIndex instance."""
        if self._index is None:
            self._index = LinkIndex(Path(self.config.index_file))
        return self._index

    async def run(
        self,
        links: List[str],
        index: Optional[LinkIndex] = None,
    ) -> dict:
        """
        Run the crawler on the provided links.

        Args:
            links: List of URLs to process
            index: Optional LinkIndex instance (creates one if not provided)

        Returns:
            Dictionary with crawl statistics
        """
        load_dotenv()
        self._setup_memory_pipeline()

        if index is not None:
            self._index = index

        os.makedirs(self.config.data_dir, exist_ok=True)

        total = len(links)
        if total == 0:
            logger.info("No links to process.")
            return {"total": 0, "success": 0, "failed": 0}

        logger.info("Processing %d links...", total)

        # Initialize status tracker for TUI
        status_tracker = get_status_tracker() if self.use_tui else None
        if status_tracker:
            status_tracker.queue_stats.total_count = total
            for link in links:
                status_tracker.update_link_stage(link, ProcessingStage.PENDING)
            status_tracker.add_activity(f"Starting crawler with {total} links")

        # Track existing filenames to avoid collisions
        idx = self.get_index()
        existing_filenames = {
            e.readable_filename for e in idx.get_all() if e.readable_filename
        }

        # Queue setup
        fetch_queue: asyncio.Queue = asyncio.Queue()
        classification_queue: asyncio.Queue = asyncio.Queue()
        results: List[IndexEntry] = []
        failed_results: List[IndexEntry] = []

        for i, link in enumerate(links):
            await fetch_queue.put((i, link))

        # Setup TUI if enabled
        tui = CrawlerTUI(status_tracker) if self.use_tui and status_tracker else None

        if tui:
            async with tui.live_context():
                await self._run_workers(
                    fetch_queue,
                    classification_queue,
                    results,
                    failed_results,
                    existing_filenames,
                    total,
                    status_tracker,
                )
        else:
            await self._run_workers(
                fetch_queue,
                classification_queue,
                results,
                failed_results,
                existing_filenames,
                total,
                status_tracker,
            )

        # Save index
        idx.save()

        # Save classifications to a standalone file for downstream tooling
        if self.enable_classification:
            self._save_classifications(results)

        # Print summary
        success_count = len(results)
        failed_count = len(failed_results)

        if tui:
            tui.print_summary()
        else:
            logger.info("Crawling complete! Processed: %d successful, %d failed", success_count, failed_count)
            logger.info("Index saved to %s", self.config.index_file)
            if self.enable_classification:
                logger.info("Classifications saved to %s", self.config.classifications_file)

        return {
            "total": total,
            "success": success_count,
            "failed": failed_count,
        }

    def _setup_memory_pipeline(self) -> None:
        """Initialize memory routing + markdown writers (best-effort)."""
        try:
            config = get_config()
            memory_dir = Path(config.memory.output_dir)
            topics_dir = memory_dir / config.memory.topics_subdir
            links_dir = memory_dir / config.memory.links_subdir
            self._memory_link_note_max_chars = config.memory.link_note_max_chars

            embedding_client = LiteLLMEmbeddingClient(
                model=config.memory.embedding_model
            )
            index_manager = TopicIndexManager(memory_dir / "topic_index.db")
            if not index_manager.embedding_model:
                index_manager.embedding_model = config.memory.embedding_model
                index_manager.save()

            writer = MarkdownWriter(topics_dir)
            router = MemoryRouter(
                embedding_client=embedding_client,
                index_manager=index_manager,
                writer=writer,
                similarity_threshold=config.memory.similarity_threshold,
            )
            link_writer = LinkMarkdownWriter(links_dir)

            self._memory_router = router
            self._memory_writer = writer
            self._memory_index_manager = index_manager
            self._link_writer = link_writer
            self._memory_init_error = None
        except Exception as e:
            self._memory_router = None
            self._memory_writer = None
            self._memory_index_manager = None
            self._link_writer = None
            self._memory_init_error = str(e)
            logger.warning("Memory pipeline disabled: %s", e)

    async def _run_workers(
        self,
        fetch_queue: asyncio.Queue,
        classification_queue: asyncio.Queue,
        results: List[IndexEntry],
        failed_results: List[IndexEntry],
        existing_filenames: set,
        total: int,
        status_tracker,
    ):
        """Run fetch and classification workers."""
        # Start queue stats updater if TUI is enabled
        stats_task = None
        if self.use_tui and status_tracker:
            stats_task = asyncio.create_task(
                self._update_queue_stats(
                    fetch_queue, classification_queue, results, failed_results, total
                )
            )

        # Create classification workers if classification is enabled
        classification_workers_tasks = []
        if self.enable_classification:
            classification_workers_tasks = [
                asyncio.create_task(
                    self._classification_worker(
                        classification_queue,
                        results,
                        failed_results,
                        i,
                    )
                )
                for i in range(self.config.classification_workers)
            ]

        async with AsyncWebCrawler() as crawler:
            fetch_workers_tasks = [
                asyncio.create_task(
                    self._fetch_worker(
                        crawler,
                        fetch_queue,
                        classification_queue,
                        results,
                        failed_results,
                        existing_filenames,
                        total,
                        i,
                    )
                )
                for i in range(self.config.fetch_workers)
            ]

            await fetch_queue.join()

            # Send sentinel values to terminate fetch workers
            for _ in range(self.config.fetch_workers):
                await fetch_queue.put((None, None))

            await asyncio.gather(*fetch_workers_tasks, return_exceptions=True)

        # Wait for classification to complete if enabled
        if self.enable_classification:
            await classification_queue.join()

            for _ in range(self.config.classification_workers):
                await classification_queue.put(None)
            await asyncio.gather(*classification_workers_tasks, return_exceptions=True)

        # Stop stats updater
        if stats_task:
            stats_task.cancel()
            try:
                await stats_task
            except asyncio.CancelledError:
                pass

    async def _fetch_worker(
        self,
        crawler,
        fetch_queue: asyncio.Queue,
        classification_queue: asyncio.Queue,
        results: List[IndexEntry],
        failed_results: List[IndexEntry],
        existing_filenames: set,
        total: int,
        worker_id: int,
    ):
        """Fetch worker that downloads content from URLs."""
        worker_name = f"fetcher-{worker_id + 1}"
        status_tracker = get_status_tracker() if self.config.enable_tui else None

        if status_tracker:
            status_tracker.register_worker(worker_name, "fetch")
            status_tracker.update_worker_status(worker_name, "idle")

        idx = self.get_index()

        while True:
            try:
                if status_tracker:
                    status_tracker.update_worker_status(worker_name, "idle")

                item = await fetch_queue.get()
                i, link = item
                if i is None:
                    fetch_queue.task_done()
                    break

                if status_tracker:
                    status_tracker.update_worker_status(worker_name, "working", link)
                    status_tracker.update_link_stage(link, ProcessingStage.FETCHING)

                logger.info("[%d/%d] Fetching: %s", i + 1, total, link)
                link_id = ContentProcessor.hash_link(link)

                try:
                    content, typ, screenshot_base64 = await CrawlerUtils.fetch_and_convert(
                        crawler, link
                    )

                    if not content:
                        entry = IndexEntry(
                            link=link,
                            id=link_id,
                            status="Failed: No content",
                            crawled_at=datetime.now().isoformat(),
                        )
                        idx.add(entry)
                        failed_results.append(entry)
                        if status_tracker:
                            status_tracker.update_link_stage(link, ProcessingStage.FAILED)
                        fetch_queue.task_done()
                        continue

                    # Generate readable filename
                    readable_name = FilenameGenerator.generate_readable_filename(
                        link, typ or "md"
                    )
                    readable_name = FilenameGenerator.make_unique_filename(
                        readable_name, existing_filenames
                    )
                    existing_filenames.add(readable_name)

                    # Save content with readable filename
                    filepath = os.path.join(self.config.data_dir, readable_name)
                    mode = "wb" if typ == "pdf" else "w"
                    encoding = None if typ == "pdf" else "utf-8"

                    with open(filepath, mode, encoding=encoding) as f:
                        f.write(content)

                    # Save screenshot if available
                    screenshot_filename = None
                    if screenshot_base64:
                        screenshot_filename = CrawlerUtils._save_screenshot(
                            screenshot_base64, link_id, self.config.data_dir
                        )

                    if status_tracker:
                        status_tracker.update_link_stage(
                            link, ProcessingStage.FETCH_COMPLETE
                        )

                    if self.enable_classification:
                        # Create LinkData for classification
                        content_str = (
                            content
                            if typ != "pdf"
                            else f"PDF content ({len(content)} bytes)"
                        )
                        link_data = LinkData(
                            link=link,
                            id=link_id,
                            filename=readable_name,
                            content=content_str,
                            screenshot_filename=screenshot_filename,
                            status="fetching",
                            readable_filename=readable_name,
                            content_type=typ,
                            source_file_path=filepath,
                        )
                        await classification_queue.put(link_data)
                    else:
                        # No classification - mark as success immediately
                        entry = IndexEntry(
                            link=link,
                            id=link_id,
                            filename=readable_name,
                            readable_filename=readable_name,
                            status="Success",
                            crawled_at=datetime.now().isoformat(),
                            screenshot_filename=screenshot_filename,
                        )
                        idx.add(entry)
                        results.append(entry)
                        if status_tracker:
                            status_tracker.update_link_stage(link, ProcessingStage.SUCCESS)
                        logger.info("[%d/%d] Success: %s -> %s", i + 1, total, link, readable_name)

                except Exception as e:
                    logger.error("[%d/%d] Failed: %s - %s", i + 1, total, link, e)
                    entry = IndexEntry(
                        link=link,
                        id=link_id,
                        status=f"Failed: {e}",
                        crawled_at=datetime.now().isoformat(),
                    )
                    idx.add(entry)
                    failed_results.append(entry)
                    if status_tracker:
                        status_tracker.update_link_stage(link, ProcessingStage.FAILED)

                fetch_queue.task_done()

            except asyncio.CancelledError:
                break

    async def _classification_worker(
        self,
        classification_queue: asyncio.Queue,
        results: List[IndexEntry],
        failed_results: List[IndexEntry],
        worker_id: int,
    ):
        """Classification worker that classifies fetched content."""
        worker_name = f"classifier-{worker_id + 1}"
        status_tracker = get_status_tracker() if self.config.enable_tui else None

        if status_tracker:
            status_tracker.register_worker(worker_name, "classification")
            status_tracker.update_worker_status(worker_name, "idle")

        idx = self.get_index()

        while True:
            try:
                if status_tracker:
                    status_tracker.update_worker_status(worker_name, "idle")

                link_data = await classification_queue.get()
                if link_data is None:
                    classification_queue.task_done()
                    break

                if status_tracker:
                    status_tracker.update_worker_status(
                        worker_name, "working", link_data.link
                    )
                    status_tracker.update_link_stage(
                        link_data.link, ProcessingStage.CLASSIFYING
                    )

                logger.info("Classifying: %s", link_data.link)

                try:
                    title = ContentProcessor.generate_title_from_url(link_data.link)
                    classification = await self.classification_service.classify_content(
                        link_data.link, title, link_data.content
                    )

                    # Create index entry
                    entry = IndexEntry(
                        link=link_data.link,
                        id=link_data.id,
                        filename=link_data.filename,
                        readable_filename=link_data.readable_filename,
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
                            "target_audience": classification.target_audience,
                        },
                        screenshot_filename=link_data.screenshot_filename,
                    )

                    if self._memory_router and self._memory_writer and self._link_writer and self._memory_index_manager:
                        try:
                            logger.debug("Routing %s to memory system", link_data.link)
                            link_content_markdown = ""
                            if link_data.content_type == "md":
                                link_content_markdown = link_data.content or ""
                            elif link_data.source_file_path:
                                link_content_markdown = ContentProcessor.extract_content_from_file(
                                    Path(link_data.source_file_path)
                                )

                            max_content_len = self._memory_link_note_max_chars
                            content_truncated = len(link_content_markdown) > max_content_len
                            content_for_note = link_content_markdown[:max_content_len]

                            topic_hints = [
                                classification.category,
                                classification.subcategory,
                                *classification.tags,
                                *classification.key_topics,
                            ]
                            topic_hints = [h for h in topic_hints if h]

                            topic_title = (
                                classification.subcategory
                                or classification.category
                                or title
                            )

                            memory_entry = MemoryLinkEntry(
                                url=link_data.link,
                                title=title,
                                tags=classification.tags,
                                summary=classification.summary,
                                key_insight=", ".join(classification.key_topics),
                                raw_snippet=(link_content_markdown or "")[:300],
                                key_topics=classification.key_topics,
                                content_markdown=content_for_note,
                                source_filename=link_data.readable_filename or "",
                                content_type=link_data.content_type or "",
                                content_truncated=content_truncated,
                            )

                            topic_id = await self._memory_router.route_link(
                                entry=memory_entry,
                                content=link_content_markdown,
                                title_for_new_topic=topic_title,
                                topic_hints=topic_hints,
                                append_to_topic=False,
                            )
                            topic_filename = self._memory_index_manager.get_filename(topic_id) or ""

                            link_note_path = self._link_writer.write_link_note(
                                entry=memory_entry,
                                topic_id=topic_id,
                                topic_filename=topic_filename,
                            )
                            memory_entry.link_note_path = link_note_path
                            if topic_filename:
                                self._memory_writer.append_link(topic_filename, memory_entry)

                            entry.memory_topic_id = topic_id
                            entry.memory_topic_file = topic_filename
                            entry.memory_link_file = link_note_path
                            logger.info("Memory routed %s -> topic %s", link_data.link, topic_filename)
                        except Exception as mem_err:
                            logger.error("Memory routing failed for %s: %s", link_data.link, mem_err)
                            entry.memory_error = str(mem_err)
                    elif self._memory_init_error:
                        entry.memory_error = self._memory_init_error

                    idx.add(entry)
                    results.append(entry)

                    if status_tracker:
                        status_tracker.update_link_stage(
                            link_data.link, ProcessingStage.SUCCESS
                        )
                        status_tracker.update_queue_stats(completed_count=len(results))

                    logger.info(
                        "Success: %s -> %s (%s)", link_data.link, entry.readable_filename, classification.category
                    )

                except Exception as e:
                    logger.error("Classification failed for %s: %s", link_data.link, e)
                    entry = IndexEntry(
                        link=link_data.link,
                        id=link_data.id,
                        filename=link_data.filename,
                        readable_filename=link_data.readable_filename,
                        status=f"Failed: Classification error - {e}",
                        crawled_at=datetime.now().isoformat(),
                        screenshot_filename=link_data.screenshot_filename,
                    )
                    idx.add(entry)
                    failed_results.append(entry)
                    if status_tracker:
                        status_tracker.update_link_stage(
                            link_data.link, ProcessingStage.FAILED
                        )
                        status_tracker.add_activity(f"Classification failed: {e}")

                classification_queue.task_done()
                await asyncio.sleep(self.config.request_delay)

            except asyncio.CancelledError:
                break

    async def _update_queue_stats(
        self,
        fetch_queue: asyncio.Queue,
        classification_queue: asyncio.Queue,
        results: List,
        failed_results: List,
        total: int,
    ):
        """Periodically update queue statistics for TUI display."""
        status_tracker = get_status_tracker()

        while True:
            try:
                status_tracker.update_queue_stats(
                    fetch_queue_size=fetch_queue.qsize(),
                    classification_queue_size=classification_queue.qsize(),
                    completed_count=len(results),
                    failed_count=len(failed_results),
                    total_count=total,
                )
                await asyncio.sleep(0.5)
            except asyncio.CancelledError:
                break

    def _save_classifications(self, results: List[IndexEntry]):
        """Save classifications to a standalone JSON file."""
        classifications = {}
        for entry in results:
            if entry.classification:
                classifications[entry.link] = entry.classification

        classifications_file = Path(self.config.classifications_file)
        existing_classifications = {}
        if classifications_file.exists():
            try:
                existing_classifications = json.loads(
                    classifications_file.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                existing_classifications = {}
        existing_classifications.update(classifications)
        classifications_file.write_text(
            json.dumps(existing_classifications, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


async def run_unified_crawl(
    links: List[str],
    index: Optional[LinkIndex] = None,
    incremental: bool = True,
    use_tui: bool = False,
    enable_classification: bool = True,
    workers: int = 5,
) -> dict:
    """
    Convenience function to run a unified crawl.

    Args:
        links: List of URLs to process
        index: Optional LinkIndex instance
        incremental: Whether to skip already processed links
        use_tui: Whether to show TUI progress
        enable_classification: Whether to classify content
        workers: Number of concurrent workers

    Returns:
        Dictionary with crawl statistics
    """
    crawler = UnifiedCrawler(
        incremental=incremental,
        use_tui=use_tui,
        enable_classification=enable_classification,
        workers=workers,
    )
    return await crawler.run(links, index)
