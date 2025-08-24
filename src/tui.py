"""
Terminal User Interface for monitoring crawler progress
"""
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.progress import TaskID
from rich.text import Text
from rich.live import Live
from rich.align import Align

from .status_tracker import StatusTracker, get_status_tracker


class CrawlerTUI:
    """Terminal User Interface for crawler monitoring"""
    
    def __init__(self, status_tracker: Optional[StatusTracker] = None):
        """Initialize TUI with console and status tracker."""
        self.console = Console()
        self.status_tracker = status_tracker or get_status_tracker()
        self.live_display: Optional[Live] = None
        self.progress_task: Optional[TaskID] = None
        self._running = False
        
    def create_layout(self) -> Layout:
        """Create the main TUI layout with header, main content, and footer."""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=7)
        )
        
        layout["main"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="queues", size=8),
            Layout(name="workers"),
        )
        
        layout["right"].split_column(
            Layout(name="progress", size=8),
            Layout(name="activities")
        )
        
        return layout
        
    def create_header(self) -> Panel:
        """Create header panel with runtime and progress statistics."""
        stats = self.status_tracker.queue_stats
        elapsed = int(stats.elapsed_time)
        hours, remainder = divmod(elapsed, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        title = Text("Link Organizer Crawler", style="bold blue")
        subtitle = f"Runtime: {hours:02d}:{minutes:02d}:{seconds:02d} | "
        subtitle += f"Total: {stats.total_count} | "
        subtitle += f"Complete: {stats.completed_count} | "
        subtitle += f"Failed: {stats.failed_count}"
        
        return Panel(
            Align.center(title + "\n" + subtitle),
            style="bright_blue",
            title="Status"
        )
        
    def create_queue_panel(self) -> Panel:
        """Create queue status panel showing fetch and classification queues."""
        stats = self.status_tracker.queue_stats
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Queue", style="cyan")
        table.add_column("Size", justify="right")
        table.add_column("Status")
        
        # Fetch queue
        fetch_status = "🟢 Active" if stats.fetch_queue_size > 0 else "⚪ Empty"
        table.add_row("Fetch", str(stats.fetch_queue_size), fetch_status)
        
        # Classification queue  
        class_status = "🟢 Active" if stats.classification_queue_size > 0 else "⚪ Empty"
        table.add_row("Classification", str(stats.classification_queue_size), class_status)
        
        return Panel(table, title="Queue Status", border_style="green")
        
    def create_worker_panel(self) -> Panel:
        """Create worker status panel showing all workers and their states."""
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Worker", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Status")
        table.add_column("Current Task", max_width=30)
        
        for worker_id, worker in self.status_tracker.worker_statuses.items():
            status_icon = {
                "idle": "⚪",
                "working": "🟢", 
                "error": "🔴"
            }.get(worker.status, "❓")
            
            task_display = worker.current_task or "-"
            if len(task_display) > 30:
                task_display = task_display[:27] + "..."
                
            table.add_row(
                worker_id,
                worker.worker_type,
                f"{status_icon} {worker.status}",
                task_display
            )
            
        return Panel(table, title="Worker Status", border_style="blue")
        
    def create_progress_panel(self) -> Panel:
        """Create progress panel showing processing stages and completion."""
        stats = self.status_tracker.queue_stats
        stage_summary = self.status_tracker.get_stage_summary()
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Stage", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Percentage", justify="right")
        
        total = stats.total_count or 1  # Avoid division by zero
        
        for stage, count in stage_summary.items():
            percentage = (count / total) * 100
            table.add_row(
                stage.title(),
                str(count),
                f"{percentage:.1f}%"
            )
            
        # Add overall completion
        table.add_row(
            "─" * 20, "─" * 5, "─" * 8, style="dim"
        )
        table.add_row(
            "Overall Complete",
            str(stats.completed_count + stats.failed_count),
            f"{stats.completion_percentage:.1f}%",
            style="bold green"
        )
        
        return Panel(table, title="Progress Summary", border_style="yellow")
        
    def create_activity_panel(self) -> Panel:
        """Create recent activity panel showing latest processing events."""
        activities = self.status_tracker.get_recent_activities(15)
        
        if not activities:
            content = Text("No recent activities", style="dim")
        else:
            content = "\n".join(activities[-15:])  # Show last 15 activities
            
        return Panel(
            content, 
            title="Recent Activities", 
            border_style="magenta",
            height=15
        )
        
    def create_footer(self) -> Panel:
        """Create footer panel showing currently active tasks."""
        stats = self.status_tracker.queue_stats
        active_tasks = self.status_tracker.get_active_tasks()
        
        content = []
        if active_tasks:
            content.append("Currently Processing:")
            for worker_id, link in active_tasks[:5]:  # Show first 5
                content.append(f"  {worker_id}: {link[:60]}...")
            if len(active_tasks) > 5:
                content.append(f"  ... and {len(active_tasks) - 5} more")
        else:
            content.append("No active tasks")
            
        return Panel(
            "\n".join(content),
            title="Active Tasks",
            border_style="cyan"
        )
        
    def update_display(self) -> Layout:
        """Update the entire TUI display with current data."""
        layout = self.create_layout()
        
        layout["header"].update(self.create_header())
        layout["queues"].update(self.create_queue_panel())
        layout["workers"].update(self.create_worker_panel())
        layout["progress"].update(self.create_progress_panel())
        layout["activities"].update(self.create_activity_panel())
        layout["footer"].update(self.create_footer())
        
        return layout
        
    @asynccontextmanager
    async def live_context(self):
        """Context manager for live display with automatic updates."""
        try:
            self._running = True
            layout = self.update_display()
            
            with Live(layout, console=self.console, refresh_per_second=2) as live:
                self.live_display = live
                
                # Start update task
                update_task = asyncio.create_task(self._update_loop())
                
                try:
                    yield self
                finally:
                    self._running = False
                    update_task.cancel()
                    try:
                        await update_task
                    except asyncio.CancelledError:
                        pass
                        
        finally:
            self.live_display = None
            
    async def _update_loop(self):
        """Background task to continuously update display."""
        while self._running:
            try:
                if self.live_display:
                    layout = self.update_display()
                    self.live_display.update(layout)
                await asyncio.sleep(0.5)  # Update every 0.5 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue
                self.status_tracker.add_activity(f"TUI update error: {e}")
                await asyncio.sleep(1)
                
    def print_summary(self):
        """Print final summary statistics after crawling completion."""
        stats = self.status_tracker.queue_stats
        
        self.console.print("\n[bold green]Crawling Complete![/bold green]")
        self.console.print(f"Total processed: {stats.completed_count + stats.failed_count}/{stats.total_count}")
        self.console.print(f"Successful: {stats.completed_count}")
        self.console.print(f"Failed: {stats.failed_count}")
        self.console.print(f"Total time: {stats.elapsed_time:.1f}s")
        
        if stats.completed_count > 0:
            avg_time = stats.elapsed_time / stats.completed_count
            self.console.print(f"Average time per link: {avg_time:.1f}s")