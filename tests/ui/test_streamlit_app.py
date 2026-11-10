"""Smoke and interaction tests for Streamlit task workflows."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from app.config import settings as settings_module
from app.config.settings import Settings


def test_user_can_add_and_search_for_a_task(tmp_path, monkeypatch) -> None:
    """Exercise the create and title-search controls using an isolated DB."""
    project_root = Path(__file__).resolve().parents[2]
    test_settings = Settings(
        database_path=tmp_path / "ui.db",
        openai_api_key=None,
        openai_model="test-model",
        ai_enabled=False,
    )
    monkeypatch.setattr(settings_module, "settings", test_settings)

    app = AppTest.from_file(str(project_root / "app" / "main.py")).run()
    assert not app.exception

    next(widget for widget in app.text_input if widget.label == "Title *").set_value(
        "Review release plan"
    )
    next(
        widget for widget in app.form_submit_button if widget.label == "Add task"
    ).click().run()
    assert not app.exception
    assert any("Review release plan" in item.label for item in app.expander)

    next(widget for widget in app.text_input if widget.label == "Title").set_value(
        "Updated release plan"
    )
    next(
        widget for widget in app.form_submit_button if widget.label == "Save changes"
    ).click().run()
    assert not app.exception
    assert any("Updated release plan" in item.label for item in app.expander)

    search = next(
        widget for widget in app.text_input if widget.label == "Search title"
    )
    search.set_value("does not exist").run()
    assert not app.exception
    assert any("No tasks match" in item.value for item in app.info)
