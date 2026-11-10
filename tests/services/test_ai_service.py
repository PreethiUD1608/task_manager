"""Deterministic tests for optional AI behavior and response validation."""

import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.models.task import TaskStatus
from app.services.ai_service import (
    AIProviderError,
    AIResponseError,
    AIService,
    AIUnavailableError,
)


def test_missing_api_key_disables_ai_without_affecting_tasks(
    service,
) -> None:
    ai_service = AIService(None, "test-model")
    task = service.create_task("Normal task")

    assert not ai_service.available
    assert "OPENAI_API_KEY" in ai_service.unavailable_message
    with pytest.raises(AIUnavailableError):
        ai_service.prioritize([task])
    assert service.get_task(task.id) is not None


def test_prioritization_validates_ids_and_returns_reason(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    task = service.create_task("Prepare")
    openai_responses.create.return_value = SimpleNamespace(
        output_text=json.dumps(
            {"ranked_tasks": [{"task_id": task.id, "reason": " Due soon "}]}
        )
    )

    assert ai_service.prioritize([task]) == [
        {"task_id": task.id, "reason": "Due soon"}
    ]
    assert openai_responses.create.call_args.kwargs["model"] == "test-model"
    assert openai_responses.create.call_args.kwargs["timeout"] == 30.0
    assert openai_responses.create.call_args.kwargs["max_output_tokens"] == 1500
    assert service.get_task(task.id).status is TaskStatus.PENDING


def test_daily_plan_returns_ordered_suggestions(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    task = service.create_task("Prepare presentation")
    openai_responses.create.return_value = SimpleNamespace(
        output_text=json.dumps(
            {"plan": [{"task_id": task.id, "reason": "Deadline is tomorrow"}]}
        )
    )

    result = ai_service.daily_plan([task], today=date(2026, 11, 10))

    assert result == [
        {"task_id": task.id, "reason": "Deadline is tomorrow"}
    ]
    assert "2026-11-10" in openai_responses.create.call_args.kwargs["input"]


def test_ai_rejects_unknown_task_ids(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    task = service.create_task("Prepare")
    openai_responses.create.return_value = SimpleNamespace(
        output_text=json.dumps(
            {"ranked_tasks": [{"task_id": task.id + 100, "reason": "Urgent"}]}
        )
    )

    with pytest.raises(AIResponseError):
        ai_service.prioritize([task])


@pytest.mark.parametrize(
    ("task_id_kind", "reason"),
    [
        ("boolean", "Boolean is not a valid ID"),
        ("valid", " "),
        ("valid", "x" * 501),
    ],
)
def test_ai_rejects_invalid_suggestion_fields(
    service,
    ai_service: AIService,
    openai_responses: Mock,
    task_id_kind: str,
    reason: str,
) -> None:
    task = service.create_task("Prepare")
    task_id = True if task_id_kind == "boolean" else task.id
    openai_responses.create.return_value = SimpleNamespace(
        output_text=json.dumps(
            {"ranked_tasks": [{"task_id": task_id, "reason": reason}]}
        )
    )

    with pytest.raises(AIResponseError):
        ai_service.prioritize([task])


def test_ai_rejects_duplicate_task_suggestions(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    task = service.create_task("Prepare")
    suggestion = {"task_id": task.id, "reason": "Do this"}
    openai_responses.create.return_value = SimpleNamespace(
        output_text=json.dumps({"ranked_tasks": [suggestion, suggestion]})
    )

    with pytest.raises(AIResponseError):
        ai_service.prioritize([task])


def test_breakdown_returns_only_valid_suggestions(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    task = service.create_task("Write report")
    openai_responses.create.return_value = SimpleNamespace(
        output_text=json.dumps(
            {"subtasks": ["  Research the topic ", "Draft the report"]}
        )
    )

    assert ai_service.breakdown(task) == ["Research the topic", "Draft the report"]


@pytest.mark.parametrize(
    "subtasks",
    [
        ["Only one"],
        ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"],
        ["One", ""],
        ["One", "x" * 201],
        ["One", 2],
    ],
)
def test_breakdown_rejects_invalid_suggestions(
    service, ai_service: AIService, openai_responses: Mock, subtasks
) -> None:
    task = service.create_task("Write report")
    openai_responses.create.return_value = SimpleNamespace(
        output_text=json.dumps({"subtasks": subtasks})
    )

    with pytest.raises(AIResponseError):
        ai_service.breakdown(task)


def test_provider_timeout_is_mapped_to_actionable_error(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    task = service.create_task("Prepare")
    openai_responses.create.side_effect = TimeoutError()

    with pytest.raises(AIProviderError, match="please retry"):
        ai_service.prioritize([task])


def test_unexpected_ai_programming_error_is_not_silently_mapped(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    task = service.create_task("Prepare")
    openai_responses.create.side_effect = RuntimeError("implementation bug")

    with pytest.raises(RuntimeError, match="implementation bug"):
        ai_service.prioritize([task])


@pytest.mark.parametrize("output_text", ["not-json", "[]", ""])
def test_invalid_provider_payloads_are_rejected(
    service, ai_service: AIService, openai_responses: Mock, output_text: str
) -> None:
    task = service.create_task("Prepare")
    openai_responses.create.return_value = SimpleNamespace(
        output_text=output_text
    )

    with pytest.raises(AIResponseError):
        ai_service.prioritize([task])


def test_missing_provider_text_is_rejected(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    task = service.create_task("Prepare")
    openai_responses.create.return_value = SimpleNamespace(output_text=None)

    with pytest.raises(AIResponseError, match="invalid response"):
        ai_service.prioritize([task])


def test_completed_tasks_do_not_trigger_provider_request(
    service, ai_service: AIService, openai_responses: Mock
) -> None:
    completed = service.create_task("Already done")
    service.set_completed(completed.id, True)
    persisted = service.get_task(completed.id)
    assert persisted is not None

    assert ai_service.prioritize([persisted]) == []
    openai_responses.create.assert_not_called()