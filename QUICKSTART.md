# KYCC Quick Start

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
