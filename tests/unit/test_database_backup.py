"""Tests for verified SQLite backups."""

import os
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from app.utils.database_backup import (
    create_backup,
    prune_expired_backups,
    verify_database,
)


def test_create_backup_preserves_data_and_verifies_integrity(
    file_repository, file_service, tmp_path
) -> None:
    file_service.create_task("Backed up task")
    destination = tmp_path / "backups" / "tasks-backup.db"

    result = create_backup(file_repository.database_path, destination)

    assert result == destination.resolve()
    verify_database(result)
    with closing(sqlite3.connect(result)) as connection, connection:
        assert connection.execute("SELECT title FROM tasks").fetchone()[0] == (
            "Backed up task"
        )


def test_backup_refuses_to_overwrite_existing_file(file_repository, tmp_path) -> None:
    destination = tmp_path / "existing.db"
    destination.write_bytes(b"keep")

    with pytest.raises(FileExistsError):
        create_backup(file_repository.database_path, destination)

    assert destination.read_bytes() == b"keep"


def test_backup_rejects_source_as_destination(file_repository) -> None:
    with pytest.raises(ValueError, match="differ"):
        create_backup(file_repository.database_path, file_repository.database_path)


def test_retention_removes_only_expired_application_backups(tmp_path) -> None:
    now = datetime(2026, 11, 10, tzinfo=timezone.utc)
    expired = tmp_path / "task-manager-backup-20261001T000000Z-deadbeef.db"
    recent = tmp_path / "task-manager-backup-20261109T000000Z-cafebabe.db"
    unrelated = tmp_path / "keep-this.db"
    for path in (expired, recent, unrelated):
        path.write_bytes(b"test")
    old_mtime = (now - timedelta(days=31)).timestamp()
    expired.touch()
    os.utime(expired, (old_mtime, old_mtime))

    removed = prune_expired_backups(tmp_path, 30, now=now)

    assert removed == [expired]
    assert not expired.exists()
    assert recent.exists()
    assert unrelated.exists()


def test_retention_requires_positive_duration(tmp_path) -> None:
    with pytest.raises(ValueError, match="at least one day"):
        prune_expired_backups(tmp_path, 0)
