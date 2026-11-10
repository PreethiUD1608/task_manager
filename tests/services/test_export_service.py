"""Tests for task CSV export."""

import csv
import io

from app.utils.csv_export import tasks_to_csv


def test_csv_export_escapes_cells_and_prevents_formulas(service) -> None:
    service.create_task('=1+1, "formula"', description="line one\nline two")
    output = io.StringIO(tasks_to_csv(service.list_tasks()))
    rows = list(csv.DictReader(output))

    assert rows[0]["title"] == "'=1+1, \"formula\""
    assert rows[0]["description"] == "line one\nline two"
    assert rows[0]["status"] == "Pending"