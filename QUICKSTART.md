# KYCC Quick Start

## Prerequisites

**Before starting**, ensure you have:
- ✅ Python 3.11+ with virtual environment (`backend/venv`)
- ✅ Node.js 18+ with dependencies installed (`frontend/node_modules`)
- ✅ PostgreSQL 15 running (or SQLite fallback enabled)

## One-Command Startup

```powershell
# From project root directory
.\run_all.ps1
```

This script automatically:
- ✅ Finds available ports (avoiding conflicts)
- ✅ Validates virtual environment
- ✅ Checks PostgreSQL connection
- ✅ Updates frontend API configuration dynamically
- ✅ Starts FastAPI backend (with auto-reload)
- ✅ Starts React frontend
- ✅ Displays all connection URLs
- ✅ Monitors and logs services

## Generate Test Data (First Time Setup)

```powershell
# Generate 100 synthetic companies with supply chain relationships
cd backend
python -m scripts.seed_synthetic_profiles --batch-id BATCH_001 --count 100 --scenario balanced --out data/synthetic_profiles.json

# Load into database
python ingest_data.py
```

This creates:
- 100 parties (15 excellent, 35 good, 35 fair, 15 poor)
- 100 accounts (in NRS currency)
- ~10,000 transactions
- ~650 supply chain relationships

See [SYNTHETIC_DATA.md](SYNTHETIC_DATA.md) for detailed documentation.

## Expected Output

```
╔════════════════════════════════════════════════════════╗
║          KYCC - Master Startup Script                ║
╚════════════════════════════════════════════════════════╝

✓ Finding available ports...
✓ Backend: 127.0.0.1:8001
✓ Frontend: 127.0.0.1:5173

✓ Frontend:  http://localhost:5173
✓ Backend:   http://127.0.0.1:8001
✓ API Docs:  http://127.0.0.1:8001/docs
```

## Manual Control

If you prefer to run components separately:

### Backend Only
```powershell
cd backend
.\venv\Scripts\Activate.ps1
$env:FORCE_SQLITE_FALLBACK = "1"
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

### Frontend Only
```powershell
cd frontend
npm install
npm run dev -- --port 5173
```

## Customizing Ports

```powershell
# Use custom ports
.\run_all.ps1 -BackendPort 9000 -FrontendPort 5174
```

## Troubleshooting

**Port already in use?**
- Script automatically finds available ports
- Or manually specify: `.\run_all.ps1 -BackendPort 9000`

**Frontend can't reach backend?**
- Script automatically syncs URLs
- Check `frontend/src/api/client.js` baseURL matches backend port

**Database connection error?**
- Script enables SQLite fallback automatically
- Or start PostgreSQL: `docker ps` should show `kycc-postgres`

**npm dependencies missing?**
- Script runs `npm install` automatically
- Manual: `cd frontend && npm install`
