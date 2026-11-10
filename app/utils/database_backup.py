"""Create and verify consistent SQLite backups."""

from __future__ import annotations

import argparse
import logging
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)
BACKUP_PATTERN = re.compile(
    r"^task-manager-backup-\d{8}T\d{6}Z-[0-9a-f]{8}\.db$"
)


def verify_database(database_path: Path | str) -> None:
    """Raise if a SQLite database is missing or fails its integrity check."""
    path = Path(database_path)
    if not path.is_file():
        raise FileNotFoundError(f"Database file does not exist: {path}")
    with closing(sqlite3.connect(path)) as connection:
        result = connection.execute("PRAGMA quick_check").fetchone()
    if result is None or result[0] != "ok":
        raise sqlite3.DatabaseError(f"Database integrity check failed: {path}")


def create_backup(source: Path | str, destination: Path | str) -> Path:
    """Create a consistent SQLite backup without overwriting an existing file."""
    source_path = Path(source).expanduser().resolve()
    destination_path = Path(destination).expanduser().resolve()
    if source_path == destination_path:
        raise ValueError("Backup destination must differ from the source database.")
    if not source_path.is_file():
        raise FileNotFoundError(f"Database file does not exist: {source_path}")
    if destination_path.exists():
        raise FileExistsError(f"Backup already exists: {destination_path}")

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with closing(sqlite3.connect(source_path)) as source_connection:
            with closing(sqlite3.connect(destination_path)) as backup_connection:
                source_connection.backup(backup_connection)
                result = backup_connection.execute(
                    "PRAGMA quick_check"
                ).fetchone()
                if result is None or result[0] != "ok":
                    raise sqlite3.DatabaseError(
                        "Created backup failed integrity check."
                    )
        return destination_path
    except Exception:
        destination_path.unlink(missing_ok=True)
        raise


def create_backup_in_directory(
    source: Path | str, directory: Path | str
) -> Path:
    """Create a uniquely named, verified backup in a destination directory."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = (
        Path(directory)
        / f"task-manager-backup-{timestamp}-{uuid4().hex[:8]}.db"
    )
    return create_backup(source, destination)


def prune_expired_backups(
    directory: Path | str,
    retention_days: int,
    *,
    now: datetime | None = None,
) -> list[Path]:
    """Remove only app-generated backups older than the retention window."""
    if retention_days < 1:
        raise ValueError("Backup retention must be at least one day.")
    backup_directory = Path(directory).expanduser()
    if not backup_directory.is_dir():
        return []
    current_time = now or datetime.now(timezone.utc)
    retention_seconds = timedelta(days=retention_days).total_seconds()
    cutoff = current_time.timestamp() - retention_seconds
    removed: list[Path] = []
    for candidate in backup_directory.iterdir():
        if not BACKUP_PATTERN.fullmatch(candidate.name) or not candidate.is_file():
            continue
        if candidate.stat().st_mtime < cutoff:
            candidate.unlink()
            removed.append(candidate)
    return removed


def main() -> None:
    """Run the backup CLI."""
    parser = argparse.ArgumentParser(
        description="Create a verified task database backup."
    )
    from app.config.settings import settings

    parser.add_argument(
        "--directory",
        type=Path,
        default=settings.database_path.parent / "backups",
        help="Backup directory (default: a backups directory beside the database).",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=30,
        help="Retain app-generated backups for this many days (default: 30).",
    )
    args = parser.parse_args()
    if args.retention_days < 1:
        parser.error("--retention-days must be at least 1.")
    backup_path = create_backup_in_directory(settings.database_path, args.directory)
    expired = prune_expired_backups(args.directory, args.retention_days)
    logger.info("Created and verified SQLite backup at %s", backup_path)
    print(f"Backup created and verified: {backup_path}")
    print(f"Expired backups removed: {len(expired)}")


if __name__ == "__main__":
    main()
