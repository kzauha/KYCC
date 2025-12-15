# Getting Started

## Quick Start Guide

This guide will help you get KYCC up and running on your local machine.

## Prerequisites

- Python 3.11+
- Docker Desktop (for PostgreSQL)
- Node.js 18+ (optional, for React frontend)
- Git

## Installation Steps

### 1. Clone Repository

```powershell
git clone https://github.com/kzauha/KYCC.git
cd KYCC
```

### 2. Set Up Python Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
venv\Scripts\Activate.ps1

# Activate (Windows Git Bash)
source venv/Scripts/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 3. Start PostgreSQL Database

```powershell
docker run -d --name kycc-postgres \
  -e POSTGRES_USER=kycc_user \
  -e POSTGRES_PASSWORD=kycc_pass \
  -e POSTGRES_DB=kycc_db \
  -p 5433:5432 \
  -v kycc_pgdata:/var/lib/postgresql/data \
  postgres:15

# Verify it's running
docker exec kycc-postgres pg_isready -U kycc_user -d kycc_db
```

### 4. Configure Environment

Create `backend/.env`:

```env
DATABASE_URL=postgresql://kycc_user:kycc_pass@localhost:5433/kycc_db
DEV_DATABASE_URL=sqlite:///./dev.db
AUTO_CREATE_TABLES=1
FORCE_SQLITE_FALLBACK=0
```

### 5. Start Backend API

```powershell
cd backend
python -m uvicorn main:app --reload --port 8000

# API will be available at:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

### 6. Start Frontend (Optional)

```powershell
cd frontend
npm install
npm run dev

# Frontend available at http://localhost:5173
```

## Using the Quick Start Script

For automated setup, use the PowerShell script:

```powershell
.\run_all.ps1
```

This script will:
- Find available ports automatically
- Start backend and frontend servers
- Monitor logs in real-time
- Handle port conflicts gracefully

## Verify Installation

1. Open http://localhost:8000/health - Should return `{"status":"healthy"}`
2. Open http://localhost:8000/docs - Should show interactive API documentation
3. Open http://localhost:5173 (if running frontend) - Should show KYCC web interface

## Next Steps

- [Architecture Overview](architecture.md) - Understand the system design
- [API Reference](api/overview.md) - Explore available endpoints
- [Database Schema](database/schema.md) - Learn the data model
- [Scoring Guide](guides/scoring.md) - How credit scoring works

## Troubleshooting

### Python Not Found
Ensure Python is added to your PATH during installation.

### Port Already in Use
The `run_all.ps1` script auto-detects conflicts. Manually specify ports:
```powershell
python -m uvicorn main:app --port 8001
```

### Database Connection Failed
Check if PostgreSQL container is running:
```powershell
docker ps
docker logs kycc-postgres
```

Set `FORCE_SQLITE_FALLBACK=1` in `.env` to use SQLite instead.
