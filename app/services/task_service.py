"""Application use cases for managing tasks."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Callable, Iterator

from app.models.task import Priority, Task, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.utils.validators import (
    validate_category,
    validate_description,
    validate_due_date,
    validate_priority,
    validate_title,
)

Clock = Callable[[], datetime]


class TaskService:
    """Validate and coordinate task operations."""

    def __init__(
        self, repository: TaskRepository, clock: Clock | None = None
    ) -> None:
        """Create a task service with an optional injectable UTC clock."""
        self.repository = repository
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def create_task(
        self,
        title: str,
        description: str = "",
        priority: Priority | str = Priority.MEDIUM,
        category: str = "",
        due_date: date | str | None = None,
        parent_task_id: int | None = None,
    ) -> Task:
        """Validate and create a pending task."""
        if parent_task_id is not None:
            parent = self.repository.get(parent_task_id)
            if parent is None:
                raise LookupError(f"Parent task {parent_task_id} was not found.")
            if parent.parent_task_id is not None:
                raise ValueError("Subtasks cannot have nested subtasks.")
        task = Task(
            id=0,
            title=validate_title(title),
            description=validate_description(description),
            priority=validate_priority(priority),
            category=validate_category(category),
            due_date=validate_due_date(due_date),
            status=TaskStatus.PENDING,
            created_at=self.clock(),
            parent_task_id=parent_task_id,
        )
        return self.repository.create(task)

    def update_task(
        self,
        task_id: int,
        *,
        title: str,
        description: str,
        priority: Priority | str,
        category: str,
        due_date: date | str | None,
    ) -> Task:
        """Validate and update task details without changing its status."""
        current = self._get_required(task_id)
        updated = Task(
            id=current.id,
            title=validate_title(title),
            description=validate_description(description),
            priority=validate_priority(priority),
            category=validate_category(category),
            due_date=validate_due_date(due_date),
            status=current.status,
            created_at=current.created_at,
            parent_task_id=current.parent_task_id,
        )
        return self.repository.update(updated)

    def set_completed(self, task_id: int, completed: bool) -> Task:
        """Set a task's completion state."""
        current = self._get_required(task_id)
        updated = Task(
            id=current.id,
            title=current.title,
            description=current.description,
            priority=current.priority,
            category=current.category,
            due_date=current.due_date,
            status=TaskStatus.COMPLETED if completed else TaskStatus.PENDING,
            created_at=current.created_at,
            parent_task_id=current.parent_task_id,
        )
        return self.repository.update(updated)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task and its subtasks."""
        return self.repository.delete(task_id)

    def get_task(self, task_id: int) -> Task | None:
        """Return a task by ID."""
        return self.repository.get(task_id)

    def list_tasks(
        self,
        *,
        search: str = "",
        status: TaskStatus | str | None = None,
        priority: Priority | str | None = None,
        category: str | None = None,
        due_date: date | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        """Return tasks matching supported search and filter criteria."""
        normalized_status = (
            status.value if isinstance(status, TaskStatus) else status
        )
        normalized_priority = (
            priority.value if isinstance(priority, Priority) else priority
        )
        if normalized_status and normalized_status not in {
            item.value for item in TaskStatus
        }:
            raise ValueError("Invalid task status.")
        if normalized_priority:
            normalized_priority = validate_priority(normalized_priority).value
        if due_date is not None:
            due_date = validate_due_date(due_date)
        return self.repository.list_tasks(
            search=search,
            status=normalized_status,
            priority=normalized_priority,
            category=validate_category(category) if category else None,
            due_date=due_date,
            limit=limit,
            offset=offset,
        )

    def count_tasks(
        self,
        *,
        search: str = "",
        status: TaskStatus | str | None = None,
        priority: Priority | str | None = None,
        category: str | None = None,
        due_date: date | None = None,
    ) -> int:
        """Count tasks matching the requested filters."""
        normalized_status = (
            status.value if isinstance(status, TaskStatus) else status
        )
        normalized_priority = (
            priority.value if isinstance(priority, Priority) else priority
        )
        if normalized_status and normalized_status not in {
            item.value for item in TaskStatus
        }:
            raise ValueError("Invalid task status.")
        if normalized_priority:
            normalized_priority = validate_priority(normalized_priority).value
        normalized_due_date = (
            validate_due_date(due_date) if due_date is not None else None
        )
        return self.repository.count_tasks(
            search=search,
            status=normalized_status,
            priority=normalized_priority,
            category=validate_category(category) if category else None,
            due_date=normalized_due_date,
        )

    def list_categories(self) -> list[str]:
        """Return distinct categories without loading full task records."""
        return self.repository.list_categories()

    def iter_tasks(self, batch_size: int = 500) -> Iterator[Task]:
        """Yield tasks in batches for streaming exports."""
        return self.repository.iter_tasks(batch_size)

    def dashboard(self, today: date | None = None) -> dict[str, int]:
        """Return dashboard counts for the supplied or current local date."""
        current_date = today or self.clock().astimezone().date()
        return self.repository.counts(current_date)

    def _get_required(self, task_id: int) -> Task:
        """Return a task or raise a not-found error."""
        task = self.repository.get(task_id)
        if task is None:
            raise LookupError(f"Task {task_id} was not found.")
        return task