# Quick Start

This guide will get you up and running with KYCC in minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker and Docker Compose
- Git

## Option 1: Using Docker (Recommended)

The fastest way to start KYCC is using Docker Compose, which starts all services automatically.

### Step 1: Clone the Repository

```bash
git clone https://github.com/kzauha/KYCC.git
cd KYCC
```

### Step 2: Configure Environment

Create a `.env` file in the `backend/` directory:

```bash
cd backend
cp .env.example .env
```

Default environment variables:

```env
POSTGRES_USER=kycc_user
POSTGRES_PASSWORD=kycc_pass
POSTGRES_DB=kycc_db
POSTGRES_PORT=5433
DATABASE_URL=postgresql://kycc_user:kycc_pass@localhost:5433/kycc_db
```

### Step 3: Start Services

```bash
cd ..
docker compose up -d
```

This starts:

- **PostgreSQL** on port 5433
- **Backend API** on port 8000
- **Dagster UI** on port 3000

### Step 4: Verify Installation

- Backend API: [http://localhost:8000/docs](http://localhost:8000/docs)
- Dagster UI: [http://localhost:3000](http://localhost:3000)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

---

## Option 2: Using PowerShell Script (Windows)

For Windows users, the `run_all.ps1` script automates startup with port conflict detection.

```powershell
.\run_all.ps1
```

This script:

1. Finds available ports for all services
2. Starts the backend with uvicorn
3. Starts the frontend with Vite
4. Monitors logs from all services

---

## Option 3: Manual Setup

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start server
python -m uvicorn main:app --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## First Steps After Installation

### 1. Check System Health

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0"
}
```

### 2. View API Documentation

Open [http://localhost:8000/docs](http://localhost:8000/docs) to see the interactive Swagger UI with all available endpoints.

### 3. Run the Pipeline

Create a batch of synthetic data and score it:

```bash
# Using the API
curl -X POST "http://localhost:8000/api/pipeline/run?batch_size=100"
```

Or use the Dashboard at [http://localhost:5173](http://localhost:5173) and click "Run Pipeline".

### 4. View Scores

After the pipeline completes, view scores through:

- **API**: `GET /api/scoring/history/{party_id}`
- **Dashboard**: Navigate to a party and view their credit score

---

## Common Issues

### Port Already in Use

If port 8000 or 5433 is already in use:

```bash
# Find process using port
netstat -ano | findstr :8000

# Kill process (Windows)
taskkill /PID <PID> /F
```

Or modify ports in `docker-compose.yml` and `.env`.

### Database Connection Failed

If the backend cannot connect to PostgreSQL:

1. Ensure Docker containers are running: `docker compose ps`
2. Check PostgreSQL logs: `docker compose logs postgres`
3. Verify DATABASE_URL in `.env` matches docker-compose configuration

The system will automatically fall back to SQLite if PostgreSQL is unavailable.

### Migration Errors

If Alembic migrations fail:

```bash
cd backend

# Check current state
alembic current

# Force upgrade
alembic upgrade head --sql
```

---

## Next Steps

- [Installation Guide](installation.md) - Detailed installation instructions
- [Configuration](configuration.md) - Environment variables and settings
- [Architecture Overview](../architecture/overview.md) - Understand the system design
