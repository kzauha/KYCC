KYCC — Minimal KYCC Database Service

Overview
========
This repository contains a small, self-contained Python project that models KYC/KYCC concepts (Parties, Relationships, Transactions, CreditScores), persists them in a relational database using SQLAlchemy (PostgreSQL by default), and includes simple scripts to exercise and inspect the data.

This codebase is intentionally organized in a way that is ready to be extended into a FastAPI service or other application, therefore the structure includes clear separation of concerns (models, DB layer, schemas, and CRUD helpers) rather than being a single short script.

- Safe session handling and DB configuration for different environments.
- python-dotenv: loads `.env` into environment variables for local development.
- `app/models/models.py` — SQLAlchemy models (Party, Relationship, Transaction, Feature, ScoreRequest, Account)


# API: http://localhost:8000 | Docs: http://localhost:8000/docs
Running with Docker (recommended)
--------------------------------
```powershell
# from repo root
docker compose logs -f postgres
# API: http://localhost:8000/docs
# Postgres: localhost:5433
```
- Uses `backend/.env` for `POSTGRES_*` and other settings.
- Data persists in the `kycc_pgdata` named volume.
- Backend connects via `DATABASE_URL=postgresql://kycc_user:kycc_pass@postgres:5432/kycc_db` inside the compose network.

Logs / stop:
```powershell
docker compose down
```

```

Local dev (host) without Dockerizing backend
-------------------------------------------
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
If you only want Postgres (and will run uvicorn locally):
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- Host `DATABASE_URL` points to `localhost:5433` from `backend/.env`.
- If Postgres is unavailable, the app can fall back to SQLite (`DEV_DATABASE_URL`) when allowed.

Migrations
----------
```powershell
cd backend
alembic revision --autogenerate -m "desc"
alembic upgrade head
```
```powershell
docker compose up -d postgres
```

**Run manually without Compose (legacy flow)**

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

# Generate synthetic test data
python -m scripts.seed_synthetic_profiles --batch-id BATCH_001 --count 100 --scenario balanced --out data/synthetic_profiles.json

# Load data into database
python ingest_data.py

# Inspect database contents
python inspect_db.py

# Run API server
python -m uvicorn main:app --reload --port 8001

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