# Personal Task Manager: Implemented Project Structure

## Folder structure

```text
task_manager/
├── .streamlit/
│   └── config.toml
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── task.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── task_repository.py
│   │   └── migrations/
│   │       ├── __init__.py
│   │       └── 0001_initial.sql
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   └── task_service.py
│   ├── prompts/
│   │   └── task_prompts.py
│   └── utils/
│       ├── __init__.py
│       ├── csv_export.py
│       ├── database_backup.py
│       ├── logging_config.py
│       └── validators.py
├── tests/
│   ├── conftest.py
│   ├── repositories/
│   │   ├── test_migrations.py
│   │   └── test_sqlite_task_repository.py
│   ├── services/
│   │   ├── test_ai_service.py
│   │   ├── test_export_service.py
│   │   └── test_task_service.py
│   ├── ui/
│   │   └── test_streamlit_app.py
│   └── unit/
│       ├── test_database_backup.py
│       ├── test_entrypoint_import.py
│       ├── test_logging_config.py
│       ├── test_models.py
│       ├── test_settings.py
│       └── test_validators.py
├── docs/
│   ├── OPERATIONS.md
│   └── PROJECT_STRUCTURE.md
├── .env.example
├── .gitignore
├── ARCHITECTURE.md
├── PRD.md
└── requirements.txt
```

## Files and responsibilities

| File | Purpose |
|---|---|
| `app/main.py` | Streamlit UI, page composition, user actions, and dependency construction. |
| `app/config/settings.py` | Loads `.env` and environment configuration; resolves database location and optional OpenAI settings. |
| `app/models/task.py` | Typed task dataclass and priority/status enums. |
| `app/repositories/task_repository.py` | SQLite schema, per-operation connections, parameterized CRUD, search/filter queries, and dashboard aggregation. |
| `app/repositories/migrations/0001_initial.sql` | Initial versioned schema; `PRAGMA user_version` tracks which migrations have run. |
| `app/services/task_service.py` | Validates and coordinates task lifecycle, filters, subtasks, and dashboard use cases. |
| `app/services/ai_service.py` | Optional OpenAI Responses API integration, output validation, and review-only prioritization, plan, and breakdown suggestions. |
| `app/prompts/task_prompts.py` | Builds prompts for the three AI actions, treating task text as untrusted data. |
| `app/utils/validators.py` | Validates required titles, field lengths, priorities, categories, and strict ISO due dates. |
| `app/utils/csv_export.py` | Writes correctly quoted CSV and neutralizes spreadsheet formula prefixes. |
| `app/utils/database_backup.py` | Creates SQLite-consistent backups, verifies integrity, and applies retention to generated backups only. |
| `.streamlit/config.toml` | Binds Streamlit to loopback by default; remote deployment requires a protected reverse proxy. |
| `app/utils/logging_config.py` | Configures application logging. |
| `app/config/__init__.py`, `app/models/__init__.py`, `app/repositories/__init__.py`, `app/services/__init__.py`, `app/utils/__init__.py` | Python package markers. |
| `tests/conftest.py` | Shared in-memory SQLite, fixed-clock, file-backed backup, and mocked OpenAI fixtures. |
| `tests/unit/` | Domain model and validation tests. |
| `tests/unit/test_settings.py` | Verifies optional AI configuration and invalid settings behavior. |
| `tests/unit/test_logging_config.py` | Verifies structured log output uses safe fields. |
| `tests/unit/test_entrypoint_import.py` | Regression test that imports the Streamlit entry point when launched with `app/` as the working directory. |
| `tests/services/` | Task use-case, optional AI, dashboard counts, and CSV export behavior tests. |
| `tests/repositories/` | SQLite persistence, constraints, and filter integration tests. |
| `tests/repositories/test_migrations.py` | Verifies that an existing unversioned database is upgraded without losing task data. |
| `tests/ui/test_streamlit_app.py` | Exercises task creation, editing, search, and empty results in Streamlit. |
| `tests/unit/test_database_backup.py` | Verifies backup integrity, overwrite protection, and retention. |
| `.env.example` | Safe local configuration template; copy to `.env` and supply a key only if AI is wanted. |

## Dependency relationships

```text
Streamlit UI (main.py)
    ├── Settings (config/settings.py)
    ├── TaskService (services/task_service.py)
    │     ├── Task model and validators
    │     └── TaskRepository (repositories/task_repository.py) ── SQLite
    ├── AIService (services/ai_service.py)
    │     └── Prompt builders (prompts/task_prompts.py) ── OpenAI (optional)
    └── CSV serializer (utils/csv_export.py)

Tests ── application modules; temporary test database and fake AI client
```

The UI calls services rather than executing SQL. Services validate user input and coordinate repository operations. The task model does not depend on Streamlit or OpenAI. AI is initialized only when enabled and configured; task CRUD and export do not depend on it. Service and repository tests use isolated shared in-memory SQLite databases; migration and backup tests use temporary files where filesystem behavior is part of the test. OpenAI calls are mocked, API keys are omitted, and dates use a fixed clock or explicit date arguments.

## Create the folders and empty source files

The following commands are retained for bootstrapping a fresh copy. Run from the repository root. In this working project, these files have already been created and implemented.

### Windows PowerShell

```powershell
$dirs = @(
  'app\config', 'app\models', 'app\repositories', 'app\services',
  'app\prompts', 'app\utils', 'app\repositories\migrations',
  'tests\unit', 'tests\services', 'tests\repositories', 'tests\ui', 'docs',
  '.streamlit'
)
$files = @(
  'app\__init__.py', 'app\main.py',
  'app\config\__init__.py', 'app\config\settings.py',
  'app\models\__init__.py', 'app\models\task.py',
  'app\repositories\__init__.py', 'app\repositories\task_repository.py',
  'app\repositories\migrations\__init__.py',
  'app\repositories\migrations\0001_initial.sql',
  'app\services\__init__.py', 'app\services\task_service.py',
  'app\services\ai_service.py', 'app\prompts\task_prompts.py',
  'app\utils\__init__.py', 'app\utils\csv_export.py',
  'app\utils\database_backup.py',
  'app\utils\logging_config.py', 'app\utils\validators.py',
  'tests\conftest.py', 'tests\unit\test_entrypoint_import.py',
  'tests\unit\test_models.py',
  'tests\unit\test_settings.py', 'tests\unit\test_validators.py',
  'tests\services\test_task_service.py',
  'tests\services\test_export_service.py', 'tests\services\test_ai_service.py',
  'tests\repositories\test_sqlite_task_repository.py',
  'tests\repositories\test_migrations.py',
  'tests\ui\test_streamlit_app.py', 'tests\unit\test_database_backup.py',
  'tests\unit\test_logging_config.py',
  'docs\OPERATIONS.md', 'docs\PROJECT_STRUCTURE.md',
  '.streamlit\config.toml'
)
$dirs | ForEach-Object { New-Item -ItemType Directory -Force -Path $_ | Out-Null }
$files | ForEach-Object {
  if (-not (Test-Path $_)) { New-Item -ItemType File -Path $_ | Out-Null }
}
```

### Linux and macOS (Bash)

```bash
mkdir -p \
  app/config app/models app/repositories app/services app/prompts app/utils \
  app/repositories/migrations tests/unit tests/services tests/repositories \
  tests/ui docs .streamlit

files=(
  app/__init__.py app/main.py
  app/config/__init__.py app/config/settings.py
  app/models/__init__.py app/models/task.py
  app/repositories/__init__.py app/repositories/task_repository.py
  app/services/__init__.py app/services/task_service.py app/services/ai_service.py
  app/prompts/task_prompts.py
  app/utils/__init__.py app/utils/csv_export.py
  app/utils/logging_config.py app/utils/validators.py
  app/repositories/migrations/__init__.py
  app/repositories/migrations/0001_initial.sql
  app/utils/database_backup.py
  tests/conftest.py tests/unit/test_database_backup.py
  tests/unit/test_logging_config.py
  tests/unit/test_entrypoint_import.py
  tests/unit/test_models.py tests/unit/test_settings.py
  tests/unit/test_validators.py
  tests/services/test_task_service.py tests/services/test_export_service.py
  tests/services/test_ai_service.py
  tests/repositories/test_sqlite_task_repository.py
  tests/repositories/test_migrations.py tests/ui/test_streamlit_app.py
  .streamlit/config.toml docs/OPERATIONS.md docs/PROJECT_STRUCTURE.md
)
for file in "${files[@]}"; do
  test -e "$file" || touch "$file"
done
```
