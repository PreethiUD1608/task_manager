"""Tests for environment-backed application settings."""

import pytest

from app.config.settings import Settings


def test_ai_is_disabled_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AI_ENABLED", "true")

    settings = Settings.from_env()

    assert settings.openai_api_key is None
    assert not settings.ai_enabled


def test_ai_can_be_explicitly_disabled_with_a_configured_key(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("AI_ENABLED", "false")

    settings = Settings.from_env()

    assert settings.openai_api_key == "test-key"
    assert not settings.ai_enabled


def test_invalid_ai_enabled_setting_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("AI_ENABLED", "sometimes")

    with pytest.raises(ValueError, match="AI_ENABLED"):
        Settings.from_env()
