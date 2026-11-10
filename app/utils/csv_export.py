"""CSV serialization for task exports."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from app.models.task import Task

CSV_HEADERS = (
    "id",
    "title",
    "description",
    "priority",
    "category",
    "due_date",
    "status",
    "created_at",
    "parent_task_id",
)


def _spreadsheet_safe(value: str) -> str:
    """Neutralize spreadsheet formula prefixes in exported cell content."""
    if value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def tasks_to_csv(tasks: Iterable[Task]) -> str:
    """Serialize tasks as CSV text with formula mitigation."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_HEADERS)
    for task in tasks:
        writer.writerow(
            (
                task.id,
                _spreadsheet_safe(task.title),
                _spreadsheet_safe(task.description),
                task.priority.value,
                _spreadsheet_safe(task.category),
                task.due_date.isoformat() if task.due_date else "",
                task.status.value,
                task.created_at.isoformat(),
                task.parent_task_id if task.parent_task_id is not None else "",
            )
        )
    return output.getvalue()