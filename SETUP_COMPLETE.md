# KYCC Setup (Backend + Frontend) — Docker-first

## Prerequisites
- Docker Desktop running
- Node.js 18+ (for frontend dev) — optional if you only need the API
- Python 3.11 (only needed if you run the backend outside Docker)

---

## 1) Clone repository
```powershell
git clone <repo-url>
cd KYCC
```

## 2) Environment files
Copy the example files to create your local environment:

```powershell
# Root env (used by Docker Compose)
cp .env.example .env

# Backend env (used by backend service and host runs)
cp backend/.env.example backend/.env

# Frontend env (optional, for React dev)
cp frontend/.env.example frontend/.env
```

Default values in `.env.example` files are ready to use—no changes needed unless you want different ports/credentials.

## 3) Run the full stack with Docker (recommended)
From repo root:
```powershell
docker compose up -d
```
**First run** takes ~2-3 minutes to build the backend image.

**What's running:**
- Backend API: http://localhost:8000/docs (FastAPI + Swagger)
- Postgres: localhost:5433 (credentials from `.env`)

**Common commands:**
```powershell
docker compose logs -f backend   # tail API logs
docker compose logs -f postgres  # tail DB logs
docker compose down              # stop stack (keeps data volume)
docker compose down -v           # stop + DELETE volume (⚠️ loses all data)
```

**Notes:**
## 5) Frontend (optional (`AUTO_CREATE_TABLES=1`)

## 4) Seed synthetic data
Load 100 sample companies with transactions and relationships:

```powershell
docker compose exec backend python ingest_data.py
```

**Output:**
- 100 parties (suppliers/manufacturers/distributors/retailers)
- 100 accounts (NRS currency)
- ~10,000 transactions
- ~650 relationships

Verify:
```powershell
docker compose exec postgres psql -U kycc_user -d kycc_db -c "SELECT COUNT(*) FROM parties;"
```

---

## 3) Frontend (host dev server)
In a separate terminal:
```powershell
cd frontend
npm install
npm run dev
# App: http://localhost:5173 (proxies calls to http://localhost:8000/api)
```

---

## 4) Optional: run backend on host (venv path)
Only needed if you don’t want Docker for the API:
```Alternative: R
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Ensure Postgres is up: docker compose up -d postgres
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- If Postgres isn’t reachable, the app can fall back to SQLite (`dev.db`) if `FORCE_SQLITE_FALLBACK=1`.
- Tests always use SQLite (`tests/conftest.py`).

---

## 5) Database tips
- Check DB health: `docker compose exec postgres pg_isready -U kycc_user -d kycc_db`
- p shell: `docker compose exec -it postgres psql -U kycc_user -d kycc_db`
- Migrations (when running backend on host or in a container exec):  
  ```powershell
  cd backend
  alembic revision --autogenerate -m "desc"
  alembic upgrade head
  ```

---

## 6) Data seeding (optional)
```powershell
cd : `docker compose down`
- Backend logs: `docker compose logs -f backend`
- Frontend dev: `npm run dev` (from `frontend/`)
- API docs: `http://localhost:8000/docs`