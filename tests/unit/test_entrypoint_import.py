"""Tests for launching the Streamlit entry point outside the project root."""

import subprocess
import sys
from pathlib import Path


def test_entrypoint_imports_when_started_from_app_directory() -> None:
    """The entry point should resolve app.* imports when cwd is app/."""
    project_root = Path(__file__).resolve().parents[2]
    entry_point = project_root / "app" / "main.py"
    code = (
        "import runpy; "
        f"runpy.run_path({str(entry_point)!r}, run_name='streamlit_script')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=entry_point.parent,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
