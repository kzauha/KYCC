KYCC — Minimal KYCC Database Service

Overview
========
This repository contains a small, self-contained Python project that models KYC/KYCC concepts (Parties, Relationships, Transactions, CreditScores), persists them in a relational database using SQLAlchemy (PostgreSQL by default), and includes simple scripts to exercise and inspect the data.

This codebase is intentionally organized in a way that is ready to be extended into a FastAPI service or other application, therefore the structure includes clear separation of concerns (models, DB layer, schemas, and CRUD helpers) rather than being a single short script.

Why there is more code than a "one-off script"
------------------------------------------------
A minimal script to insert a row might be 10 lines. This project provides a maintainable foundation:
- `app/models/models.py` — SQLAlchemy ORM models and relationships.
- `app/db/database.py` — engine/session configuration and environment-driven DB URLs.
- `app/db/crud.py` — reusable data-access functions (create, list, get-by-id, get-by-tax-id).
- `app/schemas/schemas.py` — Pydantic models for validation and serialization.
- `test_day1.py`, `test_crud.py`, `view_database.py` — small runnable scripts that exercise the codebase.

The extra code gives you:
- Clear places to add validation, business logic, API endpoints, and tests.
- Safe session handling and DB configuration for different environments.
- Explicit relationships and enums in models so ORM queries behave predictably.

Key libraries used and why
--------------------------
- Python 3.11+ (recommended)
- SQLAlchemy: ORM for database models and queries.
- psycopg2-binary: PostgreSQL DB driver used by SQLAlchemy.
- Pydantic: data validation and model ↔ dict conversion (useful for APIs).
- python-dotenv: loads `.env` into environment variables for local development.
- Docker: optional container runtime to run an isolated Postgres server.

Project layout (important files)
--------------------------------
- `app/models/models.py` — SQLAlchemy models (Party, Relationship, Transaction, CreditScore) and their relationships.
- `app/schemas/schemas.py` — Pydantic models used by scripts and potential APIs.
- `app/db/database.py` — creates SQLAlchemy engine and `SessionLocal`, reads `DATABASE_URL` from `.env`.
- `app/db/crud.py` — functions like `create_party`, `get_party`, `get_parties`, `get_party_by_tax_id`.
- `test_day1.py` — a minimal smoke test that creates a party and reads it back.
- `test_crud.py` — a slightly bigger CRUD test that creates two parties and lists them.
- `view_database.py` — prints the current rows from `parties`, `relationships`, `transactions`, `credit_scores`.
- `.env` — (developer local) contains `DATABASE_URL`, `DEV_DATABASE_URL` and `AUTO_CREATE_TABLES`.

How the app works (high-level)
-------------------------------
1. `app/db/database.py` loads `DATABASE_URL` from environment and constructs an SQLAlchemy `engine` and `SessionLocal` factory.
2. Models in `app/models/models.py` declare the table schema. SQLAlchemy maps Python classes to DB tables.
3. CRUD helpers in `app/db/crud.py` accept a `Session` and operate on model classes.
4. Pydantic schemas in `app/schemas/schemas.py` define the shape of data the code expects and return values (useful for APIs and for safer scripts).
5. The test scripts import the DB/session, call CRUD helpers, and commit changes.

Database configuration
----------------------
- Primary: PostgreSQL (via `DATABASE_URL`) — recommended for development and production.
- Fallback (developer convenience): SQLite file (`DEV_DATABASE_URL`) if `psycopg2` is not available or you prefer not to run Postgres.

.environment variables (.env)
- `DATABASE_URL` — primary DB connection string (example used in repo):
  `postgresql://kycc_user:kycc_pass@localhost:5433/kycc_db`
- `DEV_DATABASE_URL` — fallback SQLite URL: `sqlite:///./dev.db`
- `AUTO_CREATE_TABLES` — when set (default `1` in repo), the app will call `Base.metadata.create_all()` at import time for convenience in dev. For production you should use Alembic migrations instead and set this to `0`.

Runtime Postgres check & SQLite fallback
----------------------------------------

The code now performs a lightweight runtime check when creating the SQLAlchemy engine to verify that the `DATABASE_URL` (Postgres by default) is reachable. Behavior is:

- **Connectivity test**: the app runs a simple `SELECT 1` against the configured `DATABASE_URL` to confirm Postgres is reachable.
- **Docker auto-start**: if Postgres is not reachable and Docker is installed, the app will attempt `docker start kycc-postgres` (the container name used in this repo). If that starts the container and the DB becomes reachable, the app continues against Postgres.
- **Interactive fallback**: if the DB remains unreachable and the process is running interactively, the app will prompt whether to fall back to the SQLite dev DB (from `DEV_DATABASE_URL` or `sqlite:///./dev.db`).
- **Non-interactive / CI**: to allow non-interactive automatic fallback to SQLite set the env var `FORCE_SQLITE_FALLBACK=1`. If this is not set and Postgres is unreachable, the app raises an error instead of silently falling back.
- **Missing Postgres driver**: if the Postgres Python driver (e.g. `psycopg2`) is not installed, the app falls back to SQLite with a warning, as before.

Notes and recommendations:

- **Container name**: the auto-start step uses the container name `kycc-postgres`. If you created the container with a different name, either rename it or start it manually (or set up Docker Compose). You can also disable the interactive fallback and explicitly use SQLite in CI by setting `FORCE_SQLITE_FALLBACK=1`.
- **Non-destructive**: the README `docker run` example (which creates a `kycc-postgres` container) is still recommended for a reproducible Postgres environment; the runtime check only helps when the container exists but is stopped or when the Postgres server is temporarily unreachable.
- **Extending behavior**: if you'd prefer the code to attempt `docker run` to create a container automatically when none exists, we can add that behavior; currently the code only tries to start an existing `kycc-postgres` container.

Testing, CI, and runtime notes
-----------------------------

- **Non-interactive environments (CI)**: the DB detection runs at import time and may prompt. To avoid prompts in CI and allow automatic fallback to SQLite, set the environment variable:

```powershell
$env:FORCE_SQLITE_FALLBACK = "1"
```

- **Run tests safely**: to run the test suite without touching your Postgres instance, point `DATABASE_URL` at a fresh local SQLite file and enable auto-create tables:

```powershell
Remove-Item -Force .\test_run.db -ErrorAction SilentlyContinue
$env:DATABASE_URL = "sqlite:///./test_run.db"
$env:AUTO_CREATE_TABLES = "1"
python -m pytest -q
```

- **Run the API (dev)**: to start the FastAPI app locally use `uvicorn` from the `backend/` folder:

```powershell
# from backend/
uvicorn main:app --reload --port 8000
```

- **Network endpoints require Postgres for full functionality**: the `/api/parties/{id}/network` endpoints use a Postgres recursive CTE for efficient graph traversal. If you run the service on the SQLite fallback these endpoints will fail. For development, run the `kycc-postgres` container (see `docker run` example above) to ensure network queries work.

- **Health endpoint behavior**: `/health` currently provides a basic status. It may show `database: connected` even when falling back to SQLite; consider using the `SELECT 1` DB check or the `FORCE_SQLITE_FALLBACK` env var to control behavior in scripts/CI.

Running the project locally (recommended flow)
---------------------------------------------
Prerequisites:
- Docker Desktop installed and running (or a local Postgres server)
- Python 3.11+ installed
- A virtual environment (`venv`) for Python dependencies

1) Start Docker Desktop (Windows) if not running.
2) Create and/or activate a Python virtual environment (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt  # if you create it; otherwise use pip install <packages>
```

If you haven't created `requirements.txt`, the minimal packages you need are:
```powershell
pip install sqlalchemy psycopg2-binary pydantic python-dotenv
```

3) Start Postgres in Docker (the repository uses `kycc_postgres` credentials in `.env`):

```powershell
# recommended: with a named volume so data persists
docker run -d --name kycc-postgres `
  -e POSTGRES_USER=kycc_user `
  -e POSTGRES_PASSWORD=kycc_pass `
  -e POSTGRES_DB=kycc_db `
  -p 5433:5432 `
  -v kycc_pgdata:/var/lib/postgresql/data `
  postgres:15
```

The repo `.env` included the connection string that points to `localhost:5433` with the credentials above. Keep those values in `.env`.

4) Verify Postgres is ready (optional):
```powershell
docker logs -f kycc-postgres --tail 50
# or inside container
docker exec kycc-postgres pg_isready -U kycc_user -d kycc_db
```

5) Run the example scripts (from repository root):
```powershell
python test_day1.py
python test_crud.py
python view_database.py
```

These scripts use `SessionLocal()` from `app/db/database.py` to get sessions and run simple operations.

How Docker + Postgres relate to the app
--------------------------------------
- The running Postgres container provides a standard PostgreSQL server that the Python app connects to using the `psycopg2` driver and SQLAlchemy.
- The container exposes Postgres on a host port (`5433` in this repo) so `DATABASE_URL` can be `postgresql://user:pass@localhost:5433/dbname`.
- Data persistence: if you want the DB to persist after removing a container, run Postgres with a named volume (example above uses `-v kycc_pgdata`). Without a named volume, removing the container will remove the data.

What to do after a fresh computer boot
--------------------------------------
1) Start Docker Desktop (if not already configured to start automatically).
2) Start the existing Postgres container:
```powershell
# if you previously created the container and want to start it
docker start kycc-postgres
```
If the container does not exist, run the `docker run` command from the previous section to create it.

3) Activate Python venv and install deps (if not already done):
```powershell
.\.venv\Scripts\Activate.ps1
venv\Scripts\Activate
pip install -r requirements.txt
```
4) Ensure `.env` contains the correct `DATABASE_URL` and credentials.
5) Run the scripts or the app entrypoint:
```powershell
python test_day1.py
```

Graceful shutdown / closing the program
---------------------------------------
- Stop Python programs with Ctrl+C (SIGINT);
- The code uses `try/finally` to close DB sessions, but if you kill the process forcibly the OS and Docker will clean up resources.
- Stop the Postgres container when you don’t need it:
```powershell
docker stop kycc-postgres
```
- Remove the container (if you want to delete it and its data, only if not using a named volume):
```powershell
docker rm -f kycc-postgres
```
If you used a named volume and want to delete the data:
```powershell
docker volume rm kycc_pgdata
```

Why Docker and `venv` are helpful
--------------------------------
- Docker: isolates and standardizes the database environment (same Postgres version, no host DB config required). Good for reproducible development and CI.
- `venv`: isolates Python dependencies per project to avoid conflicts between projects and the system Python.

Notes about data safety and production readiness
-----------------------------------------------
- For development convenience the project currently contains a fallback path to create an SQLite DB when `psycopg2` is missing and may auto-create tables. This is handy for running the quick scripts but not recommended for production.
- For a production deployment:
  - Use a managed Postgres or a properly configured Postgres server (not Docker unless orchestrated and backed by persistent storage).
  - Use Alembic migrations rather than `Base.metadata.create_all()` to modify schema in a controlled manner.
  - Configure secrets properly (do not store DB passwords in plaintext `.env` files checked into source control).

Troubleshooting common issues
-----------------------------
- "ModuleNotFoundError: No module named 'psycopg2'": install it into the venv with `pip install psycopg2-binary`.
- "fe_sendauth: no password supplied" or similar connection error: check `DATABASE_URL` in `.env` and confirm the DB credentials and port match a running Postgres server.
- "no such table: parties" (SQLite): means the DB file was empty and migrations were not run; in dev mode the app attempts to auto-create tables, but ensure `AUTO_CREATE_TABLES=1` in `.env` or run migrations.

Commands summary (PowerShell)
----------------------------
```powershell
# Create and activate venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install sqlalchemy psycopg2-binary pydantic python-dotenv

# Run Postgres in Docker (persistence)
docker run -d --name kycc-postgres `
  -e POSTGRES_USER=kycc_user `
  -e POSTGRES_PASSWORD=kycc_pass `
  -e POSTGRES_DB=kycc_db `
  -p 5433:5432 `
  -v kycc_pgdata:/var/lib/postgresql/data `
  postgres:15

# Verify readiness
docker exec kycc-postgres pg_isready -U kycc_user -d kycc_db

# Run scripts
python test_day1.py
python test_crud.py
python view_database.py

# Stop container
docker stop kycc-postgres
# Remove container
docker rm -f kycc-postgres
# Remove volume (if you want to delete data)
docker volume rm kycc_pgdata
```

Suggested next improvements
---------------------------
- Add a `requirements.txt` or `pyproject.toml` to pin dependencies.
- Add `docker-compose.yml` so starting Postgres (and future services like pgAdmin) is a single command.
- Add Alembic-based migrations and an initial migration.
- Add unit tests for `app/db/crud.py` and integration tests that run against a transient Postgres container (use `pytest` + `testcontainers` or Docker Compose).
- Replace SQLite fallback with an explicit dev mode flag to avoid surprises.

If you want, I can:
- Commit a `README.md` (this file) into the repo (I already added it).
- Add `docker-compose.yml` and `requirements.txt` for an easier developer experience.
- Replace the SQLite fallback with a clear dev-mode config and add Alembic scaffolding.

If you want a shorter quick-reference or a diagram, tell me which format you prefer (one-page quickstart, checklist, or a diagram PNG/SVG).