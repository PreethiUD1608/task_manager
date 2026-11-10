"""Domain model for personal tasks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class Priority(str, Enum):
    """Supported task priority levels."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class TaskStatus(str, Enum):
    """Task lifecycle states."""

    PENDING = "Pending"
    COMPLETED = "Completed"


@dataclass(frozen=True, slots=True)
class Task:
    """A task persisted by the task manager."""

    id: int
    title: str
    description: str
    priority: Priority
    category: str
    due_date: date | None
    status: TaskStatus
    created_at: datetime
    parent_task_id: int | None = None

    @property
    def is_completed(self) -> bool:
        """Return whether this task is completed."""
        return self.status is TaskStatus.COMPLETED