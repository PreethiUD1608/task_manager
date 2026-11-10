"""Integration tests for the SQLite task repository."""

import sqlite3
from contextlib import closing
from datetime import date, datetime, timezone

import pytest

from app.models.task import Priority, Task, TaskStatus
from app.repositories.task_repository import TaskRepository


def test_parameterized_repository_round_trip(repository, service) -> None:
    task = service.create_task("Task'); DROP TABLE tasks; --")
    saved = repository.get(task.id)
    assert saved is not None
    assert saved.title == "Task'); DROP TABLE tasks; --"
    assert repository.list_tasks()


def test_repository_enforces_valid_priority(repository) -> None:
    invalid = Task(
        id=0,
        title="Invalid",
        description="",
        priority=Priority.HIGH,
        category="",
        due_date=None,
        status=TaskStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )
    repository.create(invalid)
    with closing(repository._connect()) as connection, connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE tasks SET priority = ? WHERE id = ?",
                ("Urgent", 1),
            )


def test_in_memory_database_persists_across_repository_connections(repository) -> None:
    task = repository.create(
        Task(
            id=0,
            title="In-memory persistence",
            description="",
            priority=Priority.MEDIUM,
            category="",
            due_date=None,
            status=TaskStatus.PENDING,
            created_at=datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc),
        )
    )

    assert repository.database_path.startswith("file:task_manager_")
    assert "mode=memory" in repository.database_path
    assert repository.get(task.id) == task


def test_in_memory_databases_are_isolated() -> None:
    first = TaskRepository(":memory:")
    second = TaskRepository(":memory:")
    try:
        first.create(
            Task(
                id=0,
                title="Private to first repository",
                description="",
                priority=Priority.LOW,
                category="",
                due_date=None,
                status=TaskStatus.PENDING,
                created_at=datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc),
            )
        )
        assert len(first.list_tasks()) == 1
        assert second.list_tasks() == []
    finally:
        first.close()
        second.close()


def test_due_date_filter_uses_exact_date(service) -> None:
    service.create_task("Today", due_date="2026-11-10")
    service.create_task("Tomorrow", due_date="2026-11-11")
    assert [task.title for task in service.list_tasks(due_date=date(2026, 11, 10))] == [
        "Today"
    ]


def test_pagination_category_lookup_and_batched_iteration(service) -> None:
    service.create_task("First", category="Work")
    service.create_task("Second", category="Study")
    service.create_task("Third", category="Work")

    assert service.count_tasks(category="Work") == 2
    assert [
        task.title
        for task in service.list_tasks(category="Work", limit=1, offset=1)
    ] == ["First"]
    assert service.list_categories() == ["Study", "Work"]
    assert [task.title for task in service.iter_tasks(batch_size=1)] == [
        "Third",
        "Second",
        "First",
    ]


def test_pagination_rejects_unbounded_or_negative_values(service) -> None:
    with pytest.raises(ValueError, match="Page size"):
        service.list_tasks(limit=201)
    with pytest.raises(ValueError, match="offset"):
        service.list_tasks(limit=10, offset=-1)


def test_repository_rejects_nonpositive_batch_size(repository) -> None:
    with pytest.raises(ValueError, match="positive"):
        list(repository.iter_tasks(batch_size=0))