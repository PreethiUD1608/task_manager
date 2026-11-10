"""Centralized logging configuration."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    """Format application events as one structured JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize safe event fields and an optional exception traceback."""
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(
                record.created, timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("action", "operation", "error_type", "duration_ms", "status"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    """Configure structured app logs without changing Streamlit's log handlers."""
    app_logger = logging.getLogger("app")
    app_logger.setLevel(logging.INFO)
    app_logger.propagate = False
    if any(
        getattr(handler, "_task_manager_handler", False)
        for handler in app_logger.handlers
    ):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    setattr(handler, "_task_manager_handler", True)
    app_logger.addHandler(handler)