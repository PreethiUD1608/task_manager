CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL CHECK (length(trim(title)) BETWEEN 1 AND 200),
    description TEXT NOT NULL DEFAULT '',
    priority TEXT NOT NULL CHECK (priority IN ('Low', 'Medium', 'High')),
    category TEXT NOT NULL DEFAULT '',
    due_date TEXT,
    status TEXT NOT NULL CHECK (status IN ('Pending', 'Completed')),
    created_at TEXT NOT NULL,
    parent_task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tasks_status_due_date
    ON tasks(status, due_date);
CREATE INDEX IF NOT EXISTS idx_tasks_category ON tasks(category);
