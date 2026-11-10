"""Tests for structured application log formatting."""

import json
import logging

from app.utils.logging_config import JsonFormatter


def test_json_formatter_emits_structured_safe_fields() -> None:
    record = logging.LogRecord(
        name="app.services.task_service",
        level=logging.ERROR,
        pathname="task_service.py",
        lineno=1,
        msg="Task operation failed action=%s error_type=%s",
        args=("create", "OperationalError"),
        exc_info=None,
    )

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "ERROR"
    assert payload["logger"] == "app.services.task_service"
    assert payload["message"].endswith("action=create error_type=OperationalError")
