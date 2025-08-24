"""
Status tracking system for monitoring crawler progress
"""
import time
from typing import Dict, List, Optional
from collections import deque

from .models import QueueStats, WorkerStatus, ProcessingStage


class StatusTracker:
    """Centralized status tracking for crawler operations"""
    
    def __init__(self):
        """Initialize status tracker with empty state containers."""
        self.queue_stats = QueueStats()
        self.worker_statuses: Dict[str, WorkerStatus] = {}
        self.recent_activities: deque = deque(maxlen=100)  # Last 100 activities
        self.link_stages: Dict[str, ProcessingStage] = {}  # link -> current stage
        self.active_links: Dict[str, str] = {}  # worker_id -> link being processed
        
    def update_queue_stats(self, **kwargs):
        """Update queue statistics with provided keyword arguments."""
        for key, value in kwargs.items():
            if hasattr(self.queue_stats, key):
                setattr(self.queue_stats, key, value)
    
    def register_worker(self, worker_id: str, worker_type: str):
        """Register a new worker with specified ID and type."""
        self.worker_statuses[worker_id] = WorkerStatus(
            worker_id=worker_id,
            worker_type=worker_type
        )
        
    def update_worker_status(self, worker_id: str, status: str, 
                           current_task: Optional[str] = None):
        """Update worker status and current task information."""
        if worker_id in self.worker_statuses:
            worker = self.worker_statuses[worker_id]
            worker.status = status
            worker.current_task = current_task
            worker.last_update = time.time()
            
            if current_task:
                self.active_links[worker_id] = current_task
            elif worker_id in self.active_links:
                del self.active_links[worker_id]
    
    def update_link_stage(self, link: str, stage: ProcessingStage):
        """Update the processing stage of a link and log activity."""
        self.link_stages[link] = stage
        self.add_activity(f"Link {link[:50]}... -> {stage.value}")
        
    def add_activity(self, message: str):
        """Add timestamped activity message to recent activities log."""
        timestamp = time.strftime("%H:%M:%S")
        self.recent_activities.append(f"[{timestamp}] {message}")
        
    def get_worker_summary(self) -> Dict[str, int]:
        """Get summary count of workers by status state."""
        summary = {"idle": 0, "working": 0, "error": 0}
        for worker in self.worker_statuses.values():
            summary[worker.status] = summary.get(worker.status, 0) + 1
        return summary
        
    def get_stage_summary(self) -> Dict[str, int]:
        """Get summary count of links by processing stage."""
        summary = {}
        for stage in self.link_stages.values():
            summary[stage.value] = summary.get(stage.value, 0) + 1
        return summary
        
    def get_recent_activities(self, count: int = 20) -> List[str]:
        """Get recent activity messages up to specified count."""
        return list(self.recent_activities)[-count:]
        
    def get_active_tasks(self) -> List[tuple]:
        """Get list of currently active tasks as (worker_id, link) tuples."""
        return [(worker_id, link) for worker_id, link in self.active_links.items()]


# Global status tracker instance
_status_tracker = None


def get_status_tracker() -> StatusTracker:
    """Get the global singleton status tracker instance."""
    global _status_tracker
    if _status_tracker is None:
        _status_tracker = StatusTracker()
    return _status_tracker