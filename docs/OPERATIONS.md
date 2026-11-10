# Operations Guide

## Local and remote access

The checked-in `.streamlit/config.toml` binds the app to `127.0.0.1`. Keep that
setting for local use. Do not expose Streamlit directly to an untrusted
network: it does not provide this app with user-level authentication or
authorization. For remote use, place Streamlit behind an authenticated reverse
proxy, terminate TLS at the proxy, and restrict upstream access to that proxy.

## Database backups and retention

The application takes and integrity-checks a backup before applying a pending
schema migration. For scheduled backups, run the following command daily from
the project root:

```text
python -m app.utils.database_backup --retention-days 30
```

By default, backups go to `data/backups`. That location is ignored by Git and
is suitable only for local development. For production, pass `--directory` to
an access-controlled durable location on a separate volume or host. The backup
command creates a unique SQLite backup, runs `PRAGMA quick_check`, then prunes
only expired files matching the application's generated backup name. Retention
is 30 days by default; configure a longer period if required by the recovery
policy.

### Windows Task Scheduler

Create a daily task with:

- **Program:** `<project>\.venv\Scripts\python.exe`
- **Arguments:** `-m app.utils.database_backup --retention-days 30 --directory "<protected-backup-directory>"`
- **Start in:** `<project>`

Use the task's service account with permission only to read the database and
write to the protected backup directory. Enable task history and alert on
non-zero exit status.

### Linux or macOS cron

Add a daily schedule, replacing the project, interpreter, and destination
paths. The destination must be writable only by the application operator.

```cron
0 2 * * * cd /path/to/task_manager && /path/to/task_manager/.venv/bin/python -m app.utils.database_backup --retention-days 30 --directory /protected/backups
```

Monitor the scheduler's exit status and logs. A scheduled job is not proven
until its output is checked and a restore drill succeeds.

## Restore drill

1. Stop the application so no process is writing to the database.
2. Select a backup and verify it:

   ```powershell
   .\.venv\Scripts\python.exe -c "from app.utils.database_backup import verify_database; verify_database(r'C:\protected\backups\task-manager-backup-....db')"
   ```

   ```bash
   .venv/bin/python -c "from app.utils.database_backup import verify_database; verify_database('/protected/backups/task-manager-backup-....db')"
   ```

3. Copy the backup to a separate test database path; do not overwrite the
   original production database during a drill.
4. Start a test app using that copied file via `TASK_MANAGER_DB_PATH` and
   confirm tasks and filters are available.
5. Record the restore duration and data loss window. Keep production backups
   encrypted at rest and restrict access to authorized operators.
