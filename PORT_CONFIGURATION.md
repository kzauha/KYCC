# KYCC Port Configuration

This document ensures all ports are consistent across the entire KYCC stack.

## Fixed Ports

| Service | Port | Configuration | Reference |
|---------|------|---------------|-----------|
| **Backend API** | `8000` | `backend/.env` → Not hardcoded (uses default 8000) | `run_all.ps1` line 3 |
| **Frontend** | `5173` | `frontend/vite.config.js` | `run_all.ps1` line 4 |
| **PostgreSQL** | `5433` | `backend/.env` → `DATABASE_URL` | Docker mapping 5432→5433 |

## How to Start Services

### Option 1: Using run_all.ps1 (Recommended)
```powershell
cd D:\Projects\Modules\KYCC
powershell -File .\run_all.ps1
# Automatically starts:
# - Backend on 8000
# - Frontend on 5173
# - Checks PostgreSQL on 5433
```

### Option 2: Manual Start (All ports guaranteed)
```powershell
# Terminal 1: Backend (port 8000)
cd D:\Projects\Modules\KYCC\backend
.\venv\Scripts\python.exe -m uvicorn main:app --port 8000

# Terminal 2: Frontend (port 5173)
cd D:\Projects\Modules\KYCC\frontend
npm run dev
# Vite automatically uses port 5173

# Terminal 3: PostgreSQL (port 5433)
docker ps  # Should show kycc-postgres mapping 0.0.0.0:5433->5432/tcp
```

## Configuration Files

### Backend
- **Database Port**: `backend/.env` line 3 → `DATABASE_URL=postgresql://kycc_user:kycc_pass@localhost:5433/kycc_db`
- **API Port**: Hardcoded 8000 in `run_all.ps1` and manual startup commands

### Frontend
- **Server Port**: `frontend/vite.config.js` → `server.port: 5173`
- **API URL**: `frontend/.env.local` → `VITE_API_URL=http://localhost:8000`

### PostgreSQL
- **Container Port Mapping**: Docker running on `0.0.0.0:5433->5432/tcp`

## Verification

To verify all ports are running:
```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in @(8000, 5173, 5433) }
```

All three ports should appear in the output.

## Why These Ports?

- **8000**: FastAPI/Uvicorn standard development port
- **5173**: Vite default development server port
- **5433**: PostgreSQL in Docker (mapped from internal 5432 to avoid conflicts with local Postgres)
