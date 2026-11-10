"""Reusable validation for task input."""

from __future__ import annotations

import re
from datetime import date, datetime

from app.models.task import Priority

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5000
MAX_CATEGORY_LENGTH = 100


def validate_title(value: str) -> str:
    """Trim and validate a task title."""
    title = value.strip()
    if not title:
        raise ValueError("Task title is required.")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValueError(f"Task title must be {MAX_TITLE_LENGTH} characters or fewer.")
    return title


def validate_description(value: str | None) -> str:
    """Normalize and validate a task description."""
    description = (value or "").strip()
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise ValueError(
            f"Description must be {MAX_DESCRIPTION_LENGTH} characters or fewer."
        )
    return description


def validate_priority(value: Priority | str) -> Priority:
    """Normalize a user-supplied priority."""
    try:
        return value if isinstance(value, Priority) else Priority(value.title())
    except (AttributeError, ValueError) as exc:
        choices = ", ".join(priority.value for priority in Priority)
        raise ValueError(f"Priority must be one of: {choices}.") from exc


def validate_category(value: str | None) -> str:
    """Trim and validate a category name."""
    category = (value or "").strip()
    if len(category) > MAX_CATEGORY_LENGTH:
        raise ValueError(
            f"Category must be {MAX_CATEGORY_LENGTH} characters or fewer."
        )
    return category


def validate_due_date(value: date | str | None) -> date | None:
    """Parse a date or ISO date string, rejecting invalid calendar dates."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        raise ValueError("Due date must be a date, not a datetime.")
    if isinstance(value, date):
        return value
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Due date must use YYYY-MM-DD format.")
    try:
        parsed_date = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Due date must be a valid calendar date.") from exc
    if parsed_date.isoformat() != value:
        raise ValueError("Due date must use YYYY-MM-DD format.")
    return parsed_date