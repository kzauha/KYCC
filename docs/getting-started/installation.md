# Installation

This guide provides detailed installation instructions for all KYCC components.

## System Requirements

### Minimum Requirements

| Component | Requirement |
|-----------|-------------|
| CPU | 2 cores |
| RAM | 4 GB |
| Disk | 10 GB free space |
| OS | Windows 10+, Ubuntu 20.04+, macOS 12+ |

### Software Dependencies

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend build |
| PostgreSQL | 15+ | Primary database |
| Docker | 24+ | Containerization |
| Git | 2.40+ | Version control |

---

## Backend Installation

### 1. Clone Repository

```bash
git clone https://github.com/kzauha/KYCC.git
cd KYCC/backend
```

### 2. Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Windows CMD)
.\venv\Scripts\activate.bat

# Activate (Linux/macOS)
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Key dependencies:

| Package | Purpose |
|---------|---------|
| fastapi | Web framework |
| uvicorn | ASGI server |
| sqlalchemy | ORM |
| psycopg2-binary | PostgreSQL driver |
| pydantic | Data validation |
| dagster | Pipeline orchestration |
| scikit-learn | Machine learning |
| pandas | Data manipulation |
| numpy | Numerical computing |
| joblib | Model serialization |
| simpleeval | Safe expression evaluation |

### 4. Configure Environment

Create `backend/.env`:

```env
# Database
DATABASE_URL=postgresql://kycc_user:kycc_pass@localhost:5433/kycc_db
POSTGRES_USER=kycc_user
POSTGRES_PASSWORD=kycc_pass
POSTGRES_DB=kycc_db
POSTGRES_PORT=5433

# Application
AUTO_CREATE_TABLES=1
LOG_LEVEL=INFO

# Dagster
DAGSTER_HOME=/path/to/backend/dagster_instance
```

### 5. Initialize Database

```bash
# Run Alembic migrations
alembic upgrade head

# Or auto-create tables (development only)
python -c "from app.db.database import init_db; init_db()"
```

### 6. Start Backend Server

```bash
# Development mode with auto-reload
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Frontend Installation

### 1. Navigate to Frontend

```bash
cd frontend
```

### 2. Install Node Dependencies

```bash
npm install
```

Key dependencies:

| Package | Purpose |
|---------|---------|
| react | UI framework |
| react-router-dom | Client-side routing |
| axios | HTTP client |
| recharts | Chart visualization |
| reactflow | Network graph visualization |
| bootstrap | CSS framework |

### 3. Configure API Endpoint

The frontend connects to the backend at `http://localhost:8000` by default. To change this, modify the API base URL in:

- `src/pages/Dashboard.jsx`
- `src/pages/MLDashboard.jsx`
- `src/api/` files

### 4. Start Development Server

```bash
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173).

### 5. Build for Production

```bash
npm run build
```

Built files will be in `frontend/dist/`.

---

## Database Installation

### Option 1: Docker (Recommended)

```bash
docker run -d \
  --name kycc-postgres \
  -e POSTGRES_USER=kycc_user \
  -e POSTGRES_PASSWORD=kycc_pass \
  -e POSTGRES_DB=kycc_db \
  -p 5433:5432 \
  -v kycc_pgdata:/var/lib/postgresql/data \
  postgres:15-alpine
```

### Option 2: Local PostgreSQL

1. Install PostgreSQL 15
2. Create database and user:

```sql
CREATE USER kycc_user WITH PASSWORD 'kycc_pass';
CREATE DATABASE kycc_db OWNER kycc_user;
GRANT ALL PRIVILEGES ON DATABASE kycc_db TO kycc_user;
```

### Option 3: SQLite Fallback

KYCC automatically falls back to SQLite if PostgreSQL is unavailable. This is useful for development and testing but not recommended for production.

The fallback creates `backend/kycc_local.db`.

---

## Dagster Installation

Dagster provides pipeline orchestration for the ML workflow.

### 1. Configure Dagster Home

Create `backend/dagster_instance/dagster.yaml`:

```yaml
storage:
  sqlite:
    base_dir: ./dagster_instance/history

run_launcher:
  module: dagster.core.launcher
  class: DefaultRunLauncher

run_coordinator:
  module: dagster.core.run_coordinator
  class: DefaultRunCoordinator
```

### 2. Start Dagster Webserver

```bash
cd backend
export DAGSTER_HOME=$(pwd)/dagster_instance
export PYTHONPATH=$(pwd)

dagster-webserver -h 0.0.0.0 -p 3000 --workspace dagster_home/workspace.yaml
```

### 3. Start Dagster Daemon (Optional)

For scheduled runs and sensors:

```bash
dagster-daemon run
```

---

## Docker Compose Installation

The easiest way to run all services together.

### 1. Review docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:15
    ports:
      - "5433:5432"
    volumes:
      - kycc_pgdata:/var/lib/postgresql/data

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  dagster:
    build: ./backend
    ports:
      - "3000:3000"
    depends_on:
      - postgres
```

### 2. Build and Start

```bash
# Build images
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

---

## Verification

### Check All Services

```bash
# Backend health
curl http://localhost:8000/health

# Database connection
curl http://localhost:8000/api/stats

# Dagster UI
curl http://localhost:3000
```

### Run Test Suite

```bash
cd backend
pytest
```

All tests should pass before proceeding.

---

## Troubleshooting

### Python Package Conflicts

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --force-reinstall
```

### Node Module Issues

```bash
rm -rf node_modules package-lock.json
npm install
```

### Docker Network Issues

```bash
docker network prune
docker compose down -v
docker compose up -d
```

### Permission Errors (Linux)

```bash
sudo chown -R $USER:$USER .
chmod +x scripts/*.sh
```
