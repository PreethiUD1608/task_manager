"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings for the application."""

    database_path: Path
    openai_api_key: str | None
    openai_model: str
    ai_enabled: bool

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables and project defaults."""
        raw_database_path = os.getenv(
            "TASK_MANAGER_DB_PATH", str(PROJECT_ROOT / "data" / "tasks.db")
        )
        database_path = Path(raw_database_path).expanduser()
        if not database_path.is_absolute():
            database_path = PROJECT_ROOT / database_path

        api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
        enabled_setting = os.getenv("AI_ENABLED", "true").strip().lower()
        if enabled_setting not in {"true", "false", "1", "0", "yes", "no"}:
            raise ValueError("AI_ENABLED must be true or false.")

        ai_enabled = enabled_setting in {"true", "1", "yes"} and api_key is not None
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        if not model:
            raise ValueError("OPENAI_MODEL cannot be empty.")

        return cls(
            database_path=database_path,
            openai_api_key=api_key,
            openai_model=model,
            ai_enabled=ai_enabled,
        )


settings = Settings.from_env()