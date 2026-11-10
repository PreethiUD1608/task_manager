"""Tests for task input validation."""

from datetime import date, datetime, timezone

import pytest

from app.models.task import Priority
from app.utils.validators import (
    validate_category,
    validate_description,
    validate_due_date,
    validate_priority,
    validate_title,
)


def test_title_is_trimmed() -> None:
    assert validate_title("  Finish report  ") == "Finish report"


@pytest.mark.parametrize("title", ["", "  ", "x" * 201])
def test_invalid_title_is_rejected(title: str) -> None:
    with pytest.raises(ValueError):
        validate_title(title)


def test_title_accepts_maximum_length() -> None:
    title = "x" * 200
    assert validate_title(title) == title


def test_description_is_trimmed_and_empty_is_allowed() -> None:
    assert validate_description("  Details  ") == "Details"
    assert validate_description(None) == ""


def test_description_accepts_maximum_length() -> None:
    description = "x" * 5000
    assert validate_description(description) == description


def test_description_over_maximum_length_is_rejected() -> None:
    with pytest.raises(ValueError, match="5000"):
        validate_description("x" * 5001)


def test_priority_is_case_normalized() -> None:
    assert validate_priority("high") is Priority.HIGH


@pytest.mark.parametrize("priority", ["urgent", "", "low-priority"])
def test_invalid_priority_is_rejected(priority: str) -> None:
    with pytest.raises(ValueError, match="Priority"):
        validate_priority(priority)


def test_empty_category_is_allowed() -> None:
    assert validate_category("  ") == ""


def test_category_is_trimmed_and_accepts_maximum_length() -> None:
    category = "x" * 100
    assert validate_category(f"  {category}  ") == category


def test_category_over_maximum_length_is_rejected() -> None:
    with pytest.raises(ValueError, match="100"):
        validate_category("x" * 101)


def test_valid_due_date_is_parsed() -> None:
    assert validate_due_date("2026-02-28") == date(2026, 2, 28)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        (date(2026, 2, 28), date(2026, 2, 28)),
        ("2024-02-29", date(2024, 2, 29)),
    ],
)
def test_valid_due_date_inputs(value, expected) -> None:
    assert validate_due_date(value) == expected


@pytest.mark.parametrize("value", ["2026-02-30", "20260228", "28-02-2026"])
def test_invalid_due_date_is_rejected(value: str) -> None:
    with pytest.raises(ValueError):
        validate_due_date(value)


def test_datetime_is_not_accepted_as_due_date() -> None:
    with pytest.raises(ValueError, match="not a datetime"):
        validate_due_date(datetime(2026, 2, 28, tzinfo=timezone.utc))