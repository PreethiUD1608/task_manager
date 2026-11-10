"""SQLite persistence for tasks."""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Generator, Iterator
from uuid import uuid4

from app.models.task import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).with_name("migrations")
MAX_PAGE_SIZE = 200


def _build_task_filters(
    *,
    search: str,
    status: str | None,
    priority: str | None,
    category: str | None,
    due_date: date | None,
) -> tuple[str, list[Any]]:
    """Build shared, parameterized WHERE clauses for task queries."""
    clauses: list[str] = []
    parameters: list[Any] = []
    if search.strip():
        clauses.append("instr(lower(title), lower(?)) > 0")
        parameters.append(search.strip())
    if status:
        clauses.append("status = ?")
        parameters.append(status)
    if priority:
        clauses.append("priority = ?")
        parameters.append(priority)
    if category:
        clauses.append("category = ?")
        parameters.append(category)
    if due_date is not None:
        clauses.append("due_date = ?")
        parameters.append(due_date.isoformat())
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, parameters


class TaskRepository:
    """Parameterized SQLite data access for tasks."""

    def __init__(self, database_path: Path | str) -> None:
        """Initialize the repository and create its schema if needed."""
        raw_database_path = str(database_path)
        self._is_memory_database = raw_database_path == ":memory:"
        self._memory_anchor: sqlite3.Connection | None = None
        if self._is_memory_database:
            self.database_path = (
                f"file:task_manager_{uuid4().hex}?mode=memory&cache=shared"
            )
            self._memory_anchor = sqlite3.connect(
                self.database_path, timeout=5.0, uri=True
            )
        else:
            self.database_path = str(Path(raw_database_path).expanduser())
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        try:
            self.initialize()
        except BaseException:
            self.close()
            raise

    def _connect(self) -> sqlite3.Connection:
        """Create a configured SQLite connection."""
        connection = sqlite3.connect(
            self.database_path, timeout=5.0, uri=self._is_memory_database
        )
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 5000")
        except sqlite3.Error:
            connection.close()
            raise
        return connection

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a transactional connection and always close it afterward."""
        connection = self._connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def close(self) -> None:
        """Release the anchor that keeps an in-memory database alive."""
        if self._memory_anchor is not None:
            self._memory_anchor.close()
            self._memory_anchor = None

    def initialize(self) -> None:
        """Apply sequential SQL migrations to the configured database."""
        try:
            with self._connection() as connection:
                current_version = int(
                    connection.execute("PRAGMA user_version").fetchone()[0]
                )
                has_application_tables = bool(
                    connection.execute(
                        """
                        SELECT EXISTS (
                            SELECT 1 FROM sqlite_master
                            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                        )
                        """
                    ).fetchone()[0]
                )
            migrations = sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql"))
            latest_version = (
                int(migrations[-1].name.split("_", maxsplit=1)[0])
                if migrations
                else 0
            )
            if current_version > latest_version:
                raise RuntimeError(
                    "Database schema is newer than this application supports."
                )
            if current_version < latest_version and has_application_tables:
                from app.utils.database_backup import create_backup_in_directory

                create_backup_in_directory(
                    self.database_path, Path(self.database_path).parent / "backups"
                )
            for migration in migrations:
                version = int(migration.name.split("_", maxsplit=1)[0])
                if version <= current_version:
                    continue
                if version != current_version + 1:
                    raise RuntimeError(
                        f"Missing database migration before version {version}."
                    )
                with self._connection() as connection:
                    connection.executescript(
                        "BEGIN IMMEDIATE;\n" + migration.read_text(encoding="utf-8")
                    )
                    connection.execute(f"PRAGMA user_version = {version}")
                    connection.commit()
                current_version = version
        except sqlite3.Error:
            logger.exception("Could not initialize task database")
            raise

    @staticmethod
    def _to_task(row: sqlite3.Row) -> Task:
        """Convert a database row into a domain task."""
        due_date_value = row["due_date"]
        return Task(
            id=int(row["id"]),
            title=str(row["title"]),
            description=str(row["description"]),
            priority=Priority(row["priority"]),
            category=str(row["category"]),
            due_date=date.fromisoformat(due_date_value) if due_date_value else None,
            status=TaskStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            parent_task_id=row["parent_task_id"],
        )

    def create(self, task: Task) -> Task:
        """Insert a task and return it with its generated database ID."""
        try:
            with self._connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO tasks
                        (title, description, priority, category, due_date,
                         status, created_at, parent_task_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.title,
                        task.description,
                        task.priority.value,
                        task.category,
                        task.due_date.isoformat() if task.due_date else None,
                        task.status.value,
                        task.created_at.isoformat(),
                        task.parent_task_id,
                    ),
                )
                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?", (cursor.lastrowid,)
                ).fetchone()
                if row is None:
                    raise RuntimeError("Created task could not be read back.")
                return self._to_task(row)
        except sqlite3.Error:
            logger.exception("Could not create task")
            raise

    def get(self, task_id: int) -> Task | None:
        """Return a task by ID, or ``None`` if it does not exist."""
        try:
            with self._connection() as connection:
                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?", (task_id,)
                ).fetchone()
                return self._to_task(row) if row else None
        except sqlite3.Error:
            logger.exception("Could not read task")
            raise

    def list_tasks(
        self,
        *,
        search: str = "",
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        due_date: date | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Task]:
        """Return matching tasks, optionally restricted to a bounded page."""
        if limit is not None and not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f"Page size must be between 1 and {MAX_PAGE_SIZE}.")
        if offset < 0:
            raise ValueError("Page offset cannot be negative.")
        where, parameters = _build_task_filters(
            search=search,
            status=status,
            priority=priority,
            category=category,
            due_date=due_date,
        )
        query = (
            f"SELECT * FROM tasks {where} "
            "ORDER BY CASE status WHEN 'Pending' THEN 0 ELSE 1 END, "
            "CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, id DESC"
        )
        if limit is not None:
            query += " LIMIT ? OFFSET ?"
            parameters.extend((limit, offset))
        try:
            with self._connection() as connection:
                rows = connection.execute(query, parameters).fetchall()
                return [self._to_task(row) for row in rows]
        except sqlite3.Error:
            logger.exception("Could not list tasks")
            raise

    def count_tasks(
        self,
        *,
        search: str = "",
        status: str | None = None,
        priority: str | None = None,
        category: str | None = None,
        due_date: date | None = None,
    ) -> int:
        """Count tasks matching the same filters used for paged queries."""
        where, parameters = _build_task_filters(
            search=search,
            status=status,
            priority=priority,
            category=category,
            due_date=due_date,
        )
        try:
            with self._connection() as connection:
                row = connection.execute(
                    f"SELECT COUNT(*) FROM tasks {where}", parameters
                ).fetchone()
                return int(row[0])
        except sqlite3.Error:
            logger.exception("Could not count tasks")
            raise

    def list_categories(self) -> list[str]:
        """Return distinct non-empty categories without loading task records."""
        try:
            with self._connection() as connection:
                rows = connection.execute(
                    """
                    SELECT DISTINCT category FROM tasks
                    WHERE category <> ''
                    ORDER BY category COLLATE NOCASE
                    """
                ).fetchall()
                return [str(row[0]) for row in rows]
        except sqlite3.Error:
            logger.exception("Could not list task categories")
            raise

    def iter_tasks(self, batch_size: int = 500) -> Iterator[Task]:
        """Yield tasks in bounded batches for exports."""
        if batch_size < 1:
            raise ValueError("Batch size must be positive.")
        try:
            with self._connection() as connection:
                cursor = connection.execute(
                    """
                    SELECT * FROM tasks
                    ORDER BY CASE status WHEN 'Pending' THEN 0 ELSE 1 END,
                    CASE WHEN due_date IS NULL THEN 1 ELSE 0 END, due_date, id DESC
                    """
                )
                try:
                    while rows := cursor.fetchmany(batch_size):
                        for row in rows:
                            yield self._to_task(row)
                finally:
                    cursor.close()
        except sqlite3.Error:
            logger.exception("Could not stream tasks for export")
            raise

    def update(self, task: Task) -> Task:
        """Persist mutable task fields, raising if the task does not exist."""
        try:
            with self._connection() as connection:
                cursor = connection.execute(
                    """
                    UPDATE tasks
                    SET title = ?, description = ?, priority = ?, category = ?,
                        due_date = ?, status = ?, parent_task_id = ?
                    WHERE id = ?
                    """,
                    (
                        task.title,
                        task.description,
                        task.priority.value,
                        task.category,
                        task.due_date.isoformat() if task.due_date else None,
                        task.status.value,
                        task.parent_task_id,
                        task.id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise LookupError(f"Task {task.id} was not found.")
                row = connection.execute(
                    "SELECT * FROM tasks WHERE id = ?", (task.id,)
                ).fetchone()
                if row is None:
                    raise RuntimeError("Updated task could not be read back.")
                return self._to_task(row)
        except sqlite3.Error:
            logger.exception("Could not update task")
            raise

    def delete(self, task_id: int) -> bool:
        """Delete a task and its subtasks; return whether a row was deleted."""
        try:
            with self._connection() as connection:
                cursor = connection.execute(
                    "DELETE FROM tasks WHERE id = ?", (task_id,)
                )
                return cursor.rowcount > 0
        except sqlite3.Error:
            logger.exception("Could not delete task")
            raise

    def counts(self, today: date) -> dict[str, int]:
        """Return dashboard counts for all tasks."""
        query = """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'Pending' AND due_date < ? THEN 1 ELSE 0 END)
                    AS overdue,
                SUM(CASE WHEN status = 'Pending' AND due_date = ? THEN 1 ELSE 0 END)
                    AS due_today
            FROM tasks
        """
        try:
            with self._connection() as connection:
                row = connection.execute(
                    query, (today.isoformat(), today.isoformat())
                ).fetchone()
                return {key: int(row[key] or 0) for key in row.keys()}
        except sqlite3.Error:
            logger.exception("Could not calculate dashboard counts")
            raise
