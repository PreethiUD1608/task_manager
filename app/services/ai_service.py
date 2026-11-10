"""Optional OpenAI-backed task planning features."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any, Protocol

from app.models.task import Task
from app.prompts.task_prompts import (
    breakdown_prompt,
    daily_plan_prompt,
    prioritization_prompt,
)

logger = logging.getLogger(__name__)

MAX_AI_TASKS = 40
MAX_SUBTASKS = 8
MAX_REASON_LENGTH = 500
MAX_SUBTASK_LENGTH = 200


class ResponsesClient(Protocol):
    """Minimal protocol for the OpenAI Responses API used by this service."""

    def create(self, **kwargs: Any) -> Any:
        """Create a text-generation response."""


class AIServiceError(RuntimeError):
    """Base class for expected, user-displayable AI failures."""


class AIUnavailableError(AIServiceError):
    """Raised when AI is disabled or not configured."""


class AIProviderError(AIServiceError):
    """Raised when the AI provider cannot complete a request."""


class AIResponseError(AIServiceError):
    """Raised when the AI response does not match the expected schema."""


class AIService:
    """Generate reviewable task suggestions without persisting AI output."""

    def __init__(
        self,
        api_key: str | None,
        model: str,
        *,
        enabled: bool = True,
        client: ResponsesClient | None = None,
    ) -> None:
        """Configure the optional provider; no key means no SDK initialization."""
        self.model = model
        self._client = client
        self._provider_exception_types: tuple[type[Exception], ...] = (
            TimeoutError,
            ConnectionError,
        )
        self._unavailable_reason = "AI features are disabled."
        if not enabled:
            return
        if client is not None:
            self._unavailable_reason = ""
            return
        if not api_key:
            self._unavailable_reason = (
                "AI features are disabled because OPENAI_API_KEY is not configured."
            )
            return
        try:
            from openai import OpenAI, OpenAIError

            self._provider_exception_types += (OpenAIError,)
            openai_client = OpenAI(api_key=api_key, timeout=30.0, max_retries=1)
            self._client = openai_client.responses
            self._unavailable_reason = ""
        except ImportError:
            logger.warning("AI disabled because the OpenAI package is unavailable")
            self._unavailable_reason = (
                "AI features are unavailable because the OpenAI package "
                "is not installed."
            )

    @property
    def available(self) -> bool:
        """Return whether an AI provider is configured."""
        return self._client is not None

    @property
    def unavailable_message(self) -> str:
        """Return a safe explanation when AI features are unavailable."""
        return self._unavailable_reason

    def prioritize(self, tasks: list[Task]) -> list[dict[str, Any]]:
        """Rank pending tasks with a short reason for each suggestion."""
        pending = [task for task in tasks if not task.is_completed][:MAX_AI_TASKS]
        if not pending:
            return []
        payload = [self._task_payload(task) for task in pending]
        response = self._request_json(prioritization_prompt(payload), "prioritization")
        return self._validate_task_suggestions(
            response, "ranked_tasks", {task.id for task in pending}
        )

    def daily_plan(
        self, tasks: list[Task], today: date | None = None
    ) -> list[dict[str, Any]]:
        """Generate an ordered, reviewable plan for pending tasks."""
        plan_date = today or date.today()
        pending = [task for task in tasks if not task.is_completed][:MAX_AI_TASKS]
        if not pending:
            return []
        response = self._request_json(
            daily_plan_prompt(
                [self._task_payload(task) for task in pending],
                plan_date.isoformat(),
            ),
            "daily_plan",
        )
        return self._validate_task_suggestions(
            response, "plan", {task.id for task in pending}
        )

    def breakdown(self, task: Task) -> list[str]:
        """Suggest actionable subtasks for a task without saving them."""
        response = self._request_json(
            breakdown_prompt(task.title, task.description), "task_breakdown"
        )
        items = response.get("subtasks")
        if (
            not isinstance(items, list)
            or not 2 <= len(items) <= MAX_SUBTASKS
            or any(
                not isinstance(item, str)
                or not item.strip()
                or len(item.strip()) > MAX_SUBTASK_LENGTH
                for item in items
            )
        ):
            raise AIResponseError("The AI returned an invalid task breakdown.")
        return [item.strip() for item in items]

    @staticmethod
    def _task_payload(task: Task) -> dict[str, Any]:
        """Select the minimum task context required for planning."""
        return {
            "task_id": task.id,
            "title": task.title,
            "description": task.description[:1000],
            "priority": task.priority.value,
            "category": task.category,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }

    @staticmethod
    def _validate_task_suggestions(
        response: dict[str, Any], key: str, valid_ids: set[int]
    ) -> list[dict[str, Any]]:
        """Validate suggested IDs and rationale before returning them."""
        items = response.get(key)
        if not isinstance(items, list) or len(items) > MAX_AI_TASKS:
            raise AIResponseError("The AI returned an invalid task plan.")
        validated: list[dict[str, Any]] = []
        seen: set[int] = set()
        for item in items:
            if not isinstance(item, dict):
                raise AIResponseError("The AI returned an invalid task plan.")
            task_id = item.get("task_id")
            reason = item.get("reason")
            if (
                not isinstance(task_id, int)
                or isinstance(task_id, bool)
                or task_id not in valid_ids
                or task_id in seen
                or not isinstance(reason, str)
                or not reason.strip()
                or len(reason.strip()) > MAX_REASON_LENGTH
            ):
                raise AIResponseError("The AI returned an invalid task plan.")
            seen.add(task_id)
            validated.append({"task_id": task_id, "reason": reason.strip()})
        return validated

    def _request_json(self, prompt: str, operation: str) -> dict[str, Any]:
        """Call the provider with a bounded response and parse JSON."""
        if self._client is None:
            raise AIUnavailableError(self._unavailable_reason)
        try:
            result = self._client.create(
                model=self.model,
                input=prompt,
                max_output_tokens=1500,
                timeout=30.0,
            )
        except self._provider_exception_types as exc:
            logger.warning(
                "AI provider request failed operation=%s error_type=%s",
                operation,
                type(exc).__name__,
            )
            raise AIProviderError(
                "The AI request failed. Your saved tasks have not changed; "
                "please retry."
            ) from exc
        output_text = getattr(result, "output_text", None)
        if not isinstance(output_text, str):
            raise AIResponseError("The AI returned an invalid response.")
        text = output_text.strip()
        if text.startswith("```"):
            text = (
                text.removeprefix("```json")
                .removeprefix("```")
                .removesuffix("```")
                .strip()
            )
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("AI returned invalid JSON operation=%s", operation)
            raise AIResponseError(
                "The AI returned an unreadable response. Please retry."
            ) from exc
        if not isinstance(parsed, dict):
            raise AIResponseError("The AI returned an invalid response.")
        return parsed