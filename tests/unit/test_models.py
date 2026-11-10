"""Tests for task domain models."""

from datetime import datetime, timezone

from app.models.task import Priority, Task, TaskStatus


def test_task_model_exposes_completion_state() -> None:
    task = Task(
        id=1,
        title="Review",
        description="",
        priority=Priority.MEDIUM,
        category="",
        due_date=None,
        status=TaskStatus.COMPLETED,
        created_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
    )
    assert task.is_completed