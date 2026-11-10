"""Tests for legacy database upgrades and schema version tracking."""

import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import pytest

from app.repositories.task_repository import TaskRepository
from app.utils.database_backup import verify_database


def test_initial_migration_preserves_existing_unversioned_database(tmp_path) -> None:
    """Upgrade the original schema in place without losing task records."""
    database_path = tmp_path / "legacy.db"
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT '',
                due_date TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                parent_task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO tasks
                (title, description, priority, category, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Keep this task",
                "",
                "Medium",
                "",
                "Pending",
                datetime(2026, 11, 10, tzinfo=timezone.utc).isoformat(),
            ),
        )

    repository = TaskRepository(database_path)

    assert repository.list_tasks()[0].title == "Keep this task"
    migration_backups = list((tmp_path / "backups").glob("task-manager-backup-*.db"))
    assert len(migration_backups) == 1
    verify_database(migration_backups[0])
    with closing(sqlite3.connect(database_path)) as connection, connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='idx_tasks_status_due_date'"
        ).fetchone()


def test_repository_rejects_unsupported_future_schema(tmp_path) -> None:
    database_path = tmp_path / "future.db"
    with closing(sqlite3.connect(database_path)) as connection, connection:
        connection.execute("PRAGMA user_version = 99")

    with pytest.raises(RuntimeError, match="newer than this application"):
        TaskRepository(database_path)


def test_repository_supports_shared_in_memory_database() -> None:
    repository = TaskRepository(":memory:")
    try:
        assert repository.database_path.startswith("file:task_manager_")
        assert repository.list_tasks() == []
    finally:
        repository.close()
