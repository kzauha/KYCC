# KYCC - Complete Cleanup & Automation Setup

## Summary of Changes

### 1. ✅ Test Files Cleaned
Removed all temporary test files:
- `test_day1.py`
- `test_direct.py`
- `test_crud.py`
- `test_endpoints.py`
- `quick_test.py`
- `full_test.py`
- `comprehensive_test.py`
- `check_duplicates.py`
- `trace_imports.py`
- `start_server.py`
- `view_database.py`
- `run_server.py`
- `crud_cli.py`
- `TEST_REPORT.md`

**Backend now contains only:**
- `main.py` - FastAPI application
- `__init__.py` - Package init
- `app/` - Application modules
- `alembic/` - Database migrations
- `requirements.txt` - Dependencies

### 2. ✅ Frontend API Configuration Fixed
**Fixed in:** `frontend/src/api/client.js`
- Updated from hardcoded `http://127.0.0.1:8000`
- Now dynamic: reads from run script
- Prevents port mismatch errors

### 3. ✅ Master Run Script Created
**File:** `run_all.ps1`

#### Features:
- **Automatic Port Detection**: Finds available ports, no conflicts
- **Single Command Startup**: Activates venv, starts backend + frontend
- **Dynamic Configuration**: Syncs backend port to frontend automatically
- **Process Management**: 
  - Cleans up old processes
  - Monitors service health
  - Graceful shutdown
- **Validation**:
  - Checks environment setup
  - Validates directories
  - Verifies ports are open

#### Usage:
```powershell
# From project root
.\run_all.ps1

# With custom ports
.\run_all.ps1 -BackendPort 9000 -FrontendPort 5174
```

#### What It Does:
1. Finds available ports (defaults: 8001 for backend, 5173 for frontend)
2. Validates project structure & venv
3. Updates `frontend/src/api/client.js` with backend URL
4. Kills any lingering processes on those ports
5. Activates Python venv
6. Starts FastAPI server with auto-reload
7. Starts React dev server
8. Displays summary of URLs
9. Monitors both services continuously

#### Output Example:
```
========================================
  KYCC Startup
========================================

[INFO] Finding available ports...
[OK] Backend port: 8001
[OK] Frontend port: 5173
[OK] Environment validated
[OK] Frontend configured: http://127.0.0.1:8001
[OK] Cleanup complete
[OK] Backend started (PID: 12345)
[OK] Frontend started (PID: 12346)

========================================
  Services Running
========================================

Frontend:  http://localhost:5173
Backend:   http://127.0.0.1:8001
API Docs:  http://127.0.0.1:8001/docs

Database:  PostgreSQL at localhost:5433
           (SQLite fallback enabled)

Press Ctrl+C to stop all services
```

### 4. ✅ Quick Start Documentation
**File:** `QUICKSTART.md`
- Simple one-liner instructions
- Troubleshooting guide
- Manual run commands
- Port customization

## How To Use

### Quickest Start:
```powershell
cd D:\Projects\Modules\KYCC
.\run_all.ps1
```

That's it! Everything else is automatic.

### What Gets Started:
1. **Python venv** - Automatically activated
2. **FastAPI server** - With hot-reload on port 8001
3. **React frontend** - Dev server on port 5173
4. **Dynamic config** - Frontend automatically knows backend URL
5. **Process monitoring** - Keeps services running

### Features:
✅ No hardcoded ports  
✅ No manual config  
✅ One-command startup  
✅ Automatic port conflict resolution  
✅ Environment validation  
✅ Service health monitoring  
✅ Graceful shutdown  
✅ Cross-platform (Windows PowerShell)

## Files Modified/Created:
- Created: `run_all.ps1` - Master startup script
- Created: `QUICKSTART.md` - Quick start guide
- Modified: `frontend/src/api/client.js` - Now uses dynamic backend URL
- Deleted: 14+ test files from backend/
- Cleaned: Removed all temporary test reports

## Database Status:
```
Parties:          10 test records
Relationships:    1 test record
Transactions:     0 (empty)
Features:         68 (auto-extracted from tests)
ModelRegistry:    0 (EMPTY - needs scorecard)
DecisionRules:    0 (EMPTY - needs rules)
```

To activate scoring, insert a scorecard into `model_registry` table.

## Next Steps:
1. Run `.\run_all.ps1` to start everything
2. Open `http://localhost:5173` in browser
3. Create parties or use existing test data
4. Insert scorecard model to enable credit scoring
