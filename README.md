# Personal Task Manager

A local-first task management application built with Streamlit, Python, and
SQLite. Organize work, track due dates, review progress, and optionally use
OpenAI-powered suggestions to prioritize tasks and plan your day.

## Overview

The application is intended for individual use by students, working
professionals, freelancers, and faculty members. Tasks are stored in a local
SQLite database. AI features are optional; task management works when AI is
disabled or no OpenAI API key is configured.

## Features

- Create, edit, complete, reopen, and delete tasks.
- Store task title, description, priority, category, due date, status, and
  creation time.
- Search by title and filter tasks by status, priority, category, and due date.
- View dashboard totals, including pending, completed, overdue, and due today.
- Create subtasks and remove them with their parent task.
- Export tasks to CSV.
- Optionally request AI task prioritization, a daily plan, or task breakdowns.
- Use pagination for task lists and schema migrations for SQLite.
- Create verified SQLite backups using the included backup utility.

## Architecture

```text
Streamlit UI (app/main.py)
    ├── TaskService (validation and task workflows)
    │     └── TaskRepository (parameterized SQLite access)
    ├── AIService (optional OpenAI integration)
    │     └── Prompt builders
    └── CSV export and logging utilities

SQLite database (local file)     OpenAI API (optional)
```

The repository layer owns SQLite operations and migrations. The service layer
validates inputs and coordinates task workflows. The UI does not issue SQL
directly. Tests use isolated in-memory SQLite databases for repository and
service coverage, and mock the OpenAI client.

## Installation

### Prerequisites

- Python 3.10 or later.
- Git, if cloning the project.

Clone the repository and move into its root directory:

```bash
git clone <repository-url>
cd task_manager
```

PowerShell equivalent after cloning:

```powershell
git clone <repository-url>
Set-Location task_manager
```

### Windows (PowerShell)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents activating the virtual environment, you can invoke its
Python directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Debian/Ubuntu, if `venv` support is missing, install the distribution's
Python venv package (for example `python3-venv`) and retry.

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Setup

Copy the example environment file to `.env` in the project root.

### Windows (PowerShell)

```powershell
Copy-Item .env.example .env
```

### Linux

```bash
cp .env.example .env
```

### macOS

```bash
cp .env.example .env
```

Edit `.env` to configure the app. You can leave the OpenAI key empty; core task
management will still work.

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | Empty | OpenAI API key. Required only for AI features. |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model name passed to the OpenAI Responses API. |
| `AI_ENABLED` | `true` | Enable AI when a key is also configured. Accepts `true`, `false`, `1`, `0`, `yes`, or `no`. |
| `TASK_MANAGER_DB_PATH` | `data/tasks.db` under the project root | SQLite database path. Relative paths resolve from the project root. |

Example `.env` without AI:

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
AI_ENABLED=false
TASK_MANAGER_DB_PATH=data/tasks.db
```

Do not commit `.env` or put API keys in source code. The `.env` file and
database files are ignored by Git.

## Running Application

Run commands from the project root with the virtual environment activated.

### Windows

```powershell
streamlit run app\main.py
```

### Linux

```bash
streamlit run app/main.py
```

### macOS

```bash
streamlit run app/main.py
```

Streamlit prints a local URL in the terminal and opens the application in a
browser. By default, the app binds to `127.0.0.1`. The SQLite database is
created at the configured path when the application initializes.

## Running Tests

Run from the project root. The `pytest.ini` configures the project root on
Python's import path, so the console command can import the `app` package.

### Windows

```powershell
pytest -v --cov=app
```

### Linux

```bash
pytest -v --cov=app
```

### macOS

```bash
pytest -v --cov=app
```

To run tests without coverage:

```text
python -m pytest -v
```

The test suite does not require an API key or internet access. OpenAI requests
are mocked, dates are fixed where time affects results, and repository/service
tests use isolated in-memory databases.

## Git Workflow

Run these commands from the project root. Replace `<USERNAME>` with your
GitHub account name. Create an empty GitHub repository first (do not initialize
it with a README, license, or `.gitignore` if you are pushing this existing
project).

### Initialize and create the first commit

```bash
git init -b main
git add .
git status
git commit -m "chore: initialize personal task manager"
```

Inspect `git status` before committing and confirm `.env`, `.venv`, database
files, and other local data are not staged.

### Connect to GitHub

If you initialized locally, add the URL of the empty GitHub repository before
pushing:

```bash
git remote add origin https://github.com/<USERNAME>/personal-task-manager.git
git push -u origin main
```

### Create a feature branch and push it

```bash
git switch -c feature/task-reminders
# Implement and test the feature, then stage and commit it:
git add .
git commit -m "feat: add task reminders"
git push -u origin feature/task-reminders
```

Open a pull request from `feature/task-reminders` to `main`. The pull request
template is in `.github/PULL_REQUEST_TEMPLATE.md`; GitHub Actions runs the test
suite on pushes and pull requests.

### Merge and publish a release

Prefer merging the reviewed pull request on GitHub. To merge locally instead,
first fetch and make sure `main` is current:

```bash
git switch main
git pull --ff-only origin main
git merge --no-ff feature/task-reminders
pytest -v --cov=app
git push origin main
```

After confirming the release commit is on `main`, create and push an annotated
version tag:

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

### Branching strategy

- `main` contains reviewed, release-ready code.
- Create short-lived branches named `feature/<name>`, `fix/<name>`, or
  `docs/<name>` from `main`.
- Open a pull request for changes; wait for review and passing CI before
  merging.
- Tag releases on `main` using semantic versions such as `v1.0.0`.

### Commit message standards

Use Conventional Commit prefixes and an imperative, concise description:

```text
<type>(optional-scope): <short imperative summary>
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, and `ci`.
Examples: `feat: add task reminders`, `fix(ui): handle empty due dates`, and
`test: cover overdue task boundaries`. Keep unrelated changes in separate
commits.

## Troubleshooting

### `ModuleNotFoundError: No module named 'app'` during pytest startup

- Run pytest from the project root, not from inside `tests` or `app`.
- Ensure `pytest.ini` exists in the root and contains `pythonpath = .`.
- Activate the project's `.venv` and verify it is selected by VS Code.
- As an alternative, run `python -m pytest -v --cov=app`.

### `streamlit` or `pytest` command is not recognized

Activate the virtual environment and install requirements. Alternatively, call
the executable directly:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app\main.py
.\.venv\Scripts\python.exe -m pytest -v --cov=app
```

```bash
.venv/bin/python -m streamlit run app/main.py
.venv/bin/python -m pytest -v --cov=app
```

### AI options are unavailable

Set a valid `OPENAI_API_KEY` in `.env` and ensure `AI_ENABLED=true`. Restart the
Streamlit process after changing environment settings. Without a key, AI
features are intentionally disabled while task features remain available.

### Database cannot be opened

- Check that the configured database directory exists or is writable.
- Check that another process is not holding a conflicting lock.
- Ensure the path in `TASK_MANAGER_DB_PATH` is correct. Relative paths resolve
  from the project root.
- Before manual recovery or migration work, preserve a copy of the database.
  See [docs/OPERATIONS.md](docs/OPERATIONS.md) for backup and restore guidance.

## Security Guidelines

- Keep API keys in `.env` or a managed secret store; never commit them.
- Treat task titles and descriptions as personal data.
- AI features send pending task titles, descriptions (truncated by the
  application), priorities, categories, and due dates to the configured OpenAI
  service when requesting suggestions. Do not send sensitive information
  unless you have reviewed the provider's terms and your privacy obligations.
- AI suggestions are advisory and are not automatically saved as task changes.
- Keep Streamlit bound to loopback for local use. Do not expose it directly to
  an untrusted network; remote deployments require an authenticated reverse
  proxy, TLS, and restricted upstream access.
- Protect the SQLite database and backups with appropriate filesystem
  permissions. Use a separate protected location for production backups.
- The repository uses parameterized SQL statements. Keep user input validated
  and avoid logging task contents, credentials, or raw provider errors.
- Review and update dependencies regularly.

## Future Enhancements

- User accounts and authorization for multi-user deployments.
- Shared or synchronized task storage with a production database backend.
- Calendar integrations, reminders, and configurable recurring tasks.
- Additional dashboard trends and configurable productivity reports.
- More granular privacy controls for AI context and per-feature opt-out.
- Automated dependency auditing and CI across supported operating systems.
