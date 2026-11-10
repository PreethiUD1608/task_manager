"""Streamlit user interface for Personal Task Manager."""

from __future__ import annotations

import logging
import sqlite3
import sys
from datetime import date
from functools import lru_cache
from pathlib import Path

import streamlit as st

# Streamlit may launch this script with the app directory as the working
# directory. Add the project root so package imports work from either location.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config.settings import settings
from app.models.task import Priority, Task, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.services.ai_service import AIService, AIServiceError
from app.services.task_service import TaskService
from app.utils.csv_export import tasks_to_csv
from app.utils.logging_config import configure_logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_task_service() -> TaskService:
    """Create the process-level service; repository connections are per operation."""
    return TaskService(TaskRepository(settings.database_path))


@lru_cache(maxsize=1)
def get_ai_service() -> AIService:
    """Create the optional AI service without requiring an API key."""
    return AIService(
        settings.openai_api_key,
        settings.openai_model,
        enabled=settings.ai_enabled,
    )


def _show_storage_error(action: str, error: sqlite3.Error) -> None:
    """Log a safe database error and show an actionable UI message."""
    logger.error(
        "Task operation failed action=%s error_type=%s",
        action,
        type(error).__name__,
    )
    st.error("Could not save this change. Your existing task data is unchanged.")


def _show_task_editor(task_service: TaskService, task: Task) -> None:
    """Render task status, edit, delete, and task-breakdown controls."""
    with st.expander(f"{task.title} · {task.priority.value} · {task.status.value}"):
        st.caption(
            f"Category: {task.category or 'Uncategorized'} · "
            f"Due: {task.due_date.isoformat() if task.due_date else 'No due date'} · "
            f"Created: {task.created_at.astimezone().strftime('%Y-%m-%d %H:%M')}"
        )
        if task.description:
            st.write(task.description)

        with st.form(f"edit-task-{task.id}"):
            title = st.text_input("Title", value=task.title, max_chars=200)
            description = st.text_area(
                "Description", value=task.description, max_chars=5000
            )
            priority = st.selectbox(
                "Priority",
                [item.value for item in Priority],
                index=[item.value for item in Priority].index(task.priority.value),
            )
            category = st.text_input(
                "Category", value=task.category, max_chars=100
            )
            due_date = st.date_input(
                "Due date", value=task.due_date, format="YYYY-MM-DD"
            )
            save_edit = st.form_submit_button("Save changes")
        if save_edit:
            try:
                task_service.update_task(
                    task.id,
                    title=title,
                    description=description,
                    priority=priority,
                    category=category,
                    due_date=due_date,
                )
                st.success("Task updated.")
                st.rerun()
            except (ValueError, LookupError) as exc:
                st.error(str(exc))
            except sqlite3.Error as exc:
                _show_storage_error("edit", exc)

        action_col, delete_col = st.columns(2)
        with action_col:
            new_completed = st.checkbox(
                "Completed",
                value=task.is_completed,
                key=f"completed-{task.id}",
            )
            if new_completed != task.is_completed and st.button(
                "Save status", key=f"save-status-{task.id}"
            ):
                try:
                    task_service.set_completed(task.id, new_completed)
                    st.rerun()
                except LookupError as exc:
                    st.error(str(exc))
                except sqlite3.Error as exc:
                    _show_storage_error("completion update", exc)
        with delete_col:
            if st.button("Delete task", key=f"delete-{task.id}", type="secondary"):
                st.session_state[f"confirm-delete-{task.id}"] = True
            if st.session_state.get(f"confirm-delete-{task.id}", False):
                st.warning("Deleting this task also deletes its subtasks.")
                confirm_col, cancel_col = st.columns(2)
                if confirm_col.button("Confirm delete", key=f"confirm-{task.id}"):
                    try:
                        task_service.delete_task(task.id)
                        st.session_state.pop(f"confirm-delete-{task.id}", None)
                        st.rerun()
                    except sqlite3.Error as exc:
                        _show_storage_error("delete", exc)
                if cancel_col.button("Cancel", key=f"cancel-{task.id}"):
                    st.session_state.pop(f"confirm-delete-{task.id}", None)
                    st.rerun()

        ai_service = get_ai_service()
        if ai_service.available and task.parent_task_id is None:
            if st.button("Break down into subtasks", key=f"breakdown-{task.id}"):
                try:
                    st.session_state[f"breakdown-{task.id}"] = ai_service.breakdown(
                        task
                    )
                except AIServiceError as exc:
                    st.error(str(exc))
            suggestions = st.session_state.get(f"breakdown-{task.id}", [])
            for index, suggestion in enumerate(suggestions):
                st.write(f"- {suggestion}")
                if st.button(
                    "Add subtask",
                    key=f"add-subtask-{task.id}-{index}",
                ):
                    try:
                        task_service.create_task(
                            title=suggestion,
                            priority=task.priority,
                            category=task.category,
                            due_date=task.due_date,
                            parent_task_id=task.id,
                        )
                        st.success("Subtask added.")
                        st.rerun()
                    except (ValueError, LookupError) as exc:
                        st.error(str(exc))
                    except sqlite3.Error as exc:
                        _show_storage_error("add subtask", exc)


def render_app() -> None:
    """Render the task manager UI and handle user actions."""
    configure_logging()
    st.set_page_config(
        page_title="Personal Task Manager", page_icon="✅", layout="wide"
    )
    st.title("Personal Task Manager")
    st.caption(
        "Organize your work, stay on top of deadlines, and focus on what matters."
    )

    task_service = get_task_service()
    ai_service = get_ai_service()
    if not ai_service.available:
        st.info(
            f"{ai_service.unavailable_message} All task management features work "
            "without AI."
        )

    counts = task_service.dashboard(date.today())
    metric_columns = st.columns(5)
    for column, label, key in zip(
        metric_columns,
        ("Total", "Pending", "Completed", "Overdue", "Due today"),
        ("total", "pending", "completed", "overdue", "due_today"),
    ):
        column.metric(label, counts[key])

    with st.expander("Add a task", expanded=counts["total"] == 0):
        with st.form("create-task", clear_on_submit=True):
            title = st.text_input("Title *", max_chars=200)
            description = st.text_area("Description", max_chars=5000)
            col1, col2, col3 = st.columns(3)
            priority = col1.selectbox("Priority", [item.value for item in Priority])
            category = col2.text_input("Category", max_chars=100)
            due_date = col3.date_input(
                "Due date (optional)", value=None, format="YYYY-MM-DD"
            )
            submitted = st.form_submit_button("Add task", type="primary")
        if submitted:
            try:
                task_service.create_task(
                    title=title,
                    description=description,
                    priority=priority,
                    category=category,
                    due_date=due_date,
                )
                st.success("Task added.")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
            except sqlite3.Error as exc:
                _show_storage_error("create", exc)

    categories = task_service.list_categories()
    st.subheader("Tasks")
    filter_columns = st.columns(5)
    search = filter_columns[0].text_input("Search title")
    status_filter = filter_columns[1].selectbox(
        "Status", ["All", *(status.value for status in TaskStatus)]
    )
    priority_filter = filter_columns[2].selectbox(
        "Priority", ["All", *(priority.value for priority in Priority)]
    )
    category_filter = filter_columns[3].selectbox(
        "Category", ["All", *categories]
    )
    due_filter = filter_columns[4].date_input(
        "Due date", value=None, format="YYYY-MM-DD"
    )
    task_filters = dict(
        search=search,
        status=None if status_filter == "All" else status_filter,
        priority=None if priority_filter == "All" else priority_filter,
        category=None if category_filter == "All" else category_filter,
        due_date=due_filter,
    )
    matching_tasks = task_service.count_tasks(**task_filters)
    page_size = st.selectbox("Tasks per page", (25, 50, 100), index=1)
    page_count = max(1, (matching_tasks + page_size - 1) // page_size)
    current_page = st.session_state.get("task_page", 1)
    if current_page > page_count:
        st.session_state["task_page"] = page_count
    page_number = st.number_input(
        "Page",
        min_value=1,
        max_value=page_count,
        step=1,
        key="task_page",
    )
    st.caption(
        f"Showing {min((page_number - 1) * page_size + 1, matching_tasks)}–"
        f"{min(page_number * page_size, matching_tasks)} of {matching_tasks} tasks"
    )
    filtered_tasks = task_service.list_tasks(
        **task_filters,
        limit=page_size,
        offset=(page_number - 1) * page_size,
    )

    if filtered_tasks:
        for task in filtered_tasks:
            if (
                task.status is TaskStatus.PENDING
                and task.due_date is not None
                and task.due_date < date.today()
            ):
                st.error(f"Overdue · {task.title}")
            _show_task_editor(task_service, task)
    else:
        st.info("No tasks match these filters. Add a task or adjust your filters.")

    export_csv = tasks_to_csv(task_service.iter_tasks())
    st.download_button(
        "Export all tasks as CSV",
        data=export_csv,
        file_name="personal_tasks.csv",
        mime="text/csv",
    )

    if ai_service.available:
        st.subheader("AI planning")
        st.caption(
            "When you select an AI action, the relevant task titles, descriptions, "
            "priorities, categories, and due dates are sent to OpenAI for processing. "
            "AI suggestions are not saved unless you explicitly add them."
        )
        if st.button("Prioritize pending tasks"):
            try:
                pending_tasks = task_service.list_tasks(
                    status=TaskStatus.PENDING, limit=40
                )
                suggestions = ai_service.prioritize(pending_tasks)
                st.session_state["priority_suggestions"] = suggestions
                if not suggestions:
                    st.info("There are no pending tasks to prioritize.")
            except AIServiceError as exc:
                st.error(str(exc))
        for suggestion in st.session_state.get("priority_suggestions", []):
            task = task_service.get_task(suggestion["task_id"])
            if task:
                st.write(f"**{task.title}** — {suggestion['reason']}")

        if st.button("Generate today's plan"):
            try:
                pending_tasks = task_service.list_tasks(
                    status=TaskStatus.PENDING, limit=40
                )
                plan = ai_service.daily_plan(pending_tasks, date.today())
                st.session_state["daily_plan"] = plan
                if not plan:
                    st.info("There are no pending tasks to plan.")
            except AIServiceError as exc:
                st.error(str(exc))
        for suggestion in st.session_state.get("daily_plan", []):
            task = task_service.get_task(suggestion["task_id"])
            if task:
                st.write(f"**{task.title}** — {suggestion['reason']}")


if __name__ == "__main__":
    try:
        render_app()
    except (sqlite3.Error, OSError) as exc:
        logger.error("Application request failed error_type=%s", type(exc).__name__)
        st.error(
            "The application could not access its database or files. "
            "Please retry or contact the operator."
        )