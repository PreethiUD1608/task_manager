"""Tests for task management use cases."""

from datetime import date

import pytest

from app.models.task import Priority, TaskStatus


def test_create_update_complete_reopen_and_delete(service) -> None:
    task = service.create_task(
        " Write tests ",
        "Unit tests",
        "high",
        "Engineering",
        "2026-11-11",
    )
    assert task.id > 0
    assert task.title == "Write tests"
    assert task.priority is Priority.HIGH
    assert task.created_at.isoformat() == "2026-11-10T08:00:00+00:00"

    updated = service.update_task(
        task.id,
        title="Write better tests",
        description="Cover edge cases",
        priority="Medium",
        category="Quality",
        due_date=None,
    )
    assert updated.title == "Write better tests"
    assert updated.status is TaskStatus.PENDING

    completed = service.set_completed(task.id, True)
    assert completed.status is TaskStatus.COMPLETED
    assert service.set_completed(task.id, False).status is TaskStatus.PENDING
    assert service.delete_task(task.id)
    assert service.get_task(task.id) is None


def test_filters_search_only_title_and_combine(service) -> None:
    pending = service.create_task("Prepare slides", priority="High", category="Work")
    service.create_task("Read chapter", description="slides", category="Study")

    results = service.list_tasks(search="SLIDES", priority="High", category="Work")
    assert [task.title for task in results] == ["Prepare slides"]
    assert [task.title for task in service.list_tasks(search="slides")] == [
        "Prepare slides"
    ]
    service.set_completed(pending.id, True)
    assert [
        task.title
        for task in service.list_tasks(status=TaskStatus.COMPLETED)
    ] == ["Prepare slides"]


def test_dashboard_counts_pending_due_today_and_overdue(service) -> None:
    overdue = service.create_task("Overdue", due_date="2026-11-09")
    service.create_task("Today", due_date="2026-11-10")
    service.create_task("Future", due_date="2026-11-11")
    service.set_completed(overdue.id, True)

    counts = service.dashboard(date(2026, 11, 10))
    assert counts == {
        "total": 3,
        "pending": 2,
        "completed": 1,
        "overdue": 0,
        "due_today": 1,
    }


def test_overdue_count_excludes_completed_and_includes_pending(service) -> None:
    service.create_task("Past due", due_date="2026-11-09")
    counts = service.dashboard(date(2026, 11, 10))
    assert counts["overdue"] == 1


def test_subtasks_are_persisted_and_deleted_with_parent(service) -> None:
    parent = service.create_task("Write report")
    child = service.create_task("Research", parent_task_id=parent.id)

    assert child.parent_task_id == parent.id
    assert service.delete_task(parent.id)
    assert service.get_task(child.id) is None


def test_invalid_task_inputs_do_not_persist(service) -> None:
    with pytest.raises(ValueError, match="required"):
        service.create_task(" ")
    with pytest.raises(ValueError, match="valid calendar"):
        service.create_task("Invalid date", due_date="2026-02-30")
    assert service.list_tasks() == []


@pytest.mark.parametrize(
    "values",
    [
        {"title": "   "},
        {"title": "x" * 201},
        {"title": "Valid", "description": "x" * 5001},
        {"title": "Valid", "category": "x" * 101},
        {"title": "Valid", "priority": "Urgent"},
        {"title": "Valid", "due_date": "2026-13-01"},
    ],
)
def test_create_validation_failures_do_not_persist(service, values) -> None:
    with pytest.raises(ValueError):
        service.create_task(**values)
    assert service.list_tasks() == []


def test_missing_parent_and_nested_subtasks_are_rejected(service) -> None:
    with pytest.raises(LookupError, match="Parent task"):
        service.create_task("Orphan", parent_task_id=999)

    parent = service.create_task("Parent")
    child = service.create_task("Child", parent_task_id=parent.id)
    with pytest.raises(ValueError, match="nested"):
        service.create_task("Grandchild", parent_task_id=child.id)
    assert {task.id for task in service.list_tasks()} == {parent.id, child.id}


def test_missing_task_updates_and_completion_raise_lookup_error(service) -> None:
    with pytest.raises(LookupError, match="was not found"):
        service.update_task(
            999,
            title="Missing",
            description="",
            priority="Low",
            category="",
            due_date=None,
        )
    with pytest.raises(LookupError, match="was not found"):
        service.set_completed(999, True)
    assert service.delete_task(999) is False


@pytest.mark.parametrize("status", ["Done", "pending"])
def test_invalid_status_filter_is_rejected(service, status) -> None:
    with pytest.raises(ValueError, match="status"):
        service.list_tasks(status=status)