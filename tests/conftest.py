"""Shared fixtures for application tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import Mock

import pytest

from app.repositories.task_repository import TaskRepository
from app.services.ai_service import AIService
from app.services.task_service import TaskService


@pytest.fixture
def repository() -> Iterator[TaskRepository]:
    """Provide an isolated shared in-memory SQLite repository."""
    instance = TaskRepository(":memory:")
    try:
        yield instance
    finally:
        instance.close()


@pytest.fixture
def file_repository(tmp_path) -> Iterator[TaskRepository]:
    """Provide a file-backed repository for backup and migration tests."""
    instance = TaskRepository(tmp_path / "test_tasks.db")
    try:
        yield instance
    finally:
        instance.close()


@pytest.fixture
def fixed_now() -> datetime:
    """Provide a stable UTC instant for task creation."""
    return datetime(2026, 11, 10, 8, 0, tzinfo=timezone.utc)


@pytest.fixture
def service(repository: TaskRepository, fixed_now: datetime) -> TaskService:
    """Provide a task service with a deterministic UTC clock."""
    return TaskService(repository, clock=lambda: fixed_now)


@pytest.fixture
def file_service(file_repository: TaskRepository, fixed_now: datetime) -> TaskService:
    """Provide a deterministic service backed by a temporary database file."""
    return TaskService(file_repository, clock=lambda: fixed_now)


@pytest.fixture
def openai_responses() -> Mock:
    """Provide a mock Responses API endpoint that never performs network I/O."""
    responses = Mock()
    responses.create.return_value = SimpleNamespace(output_text="{}")
    return responses


@pytest.fixture
def ai_service(openai_responses: Mock) -> AIService:
    """Provide an AI service backed only by the mocked provider endpoint."""
    return AIService(None, "test-model", client=openai_responses)