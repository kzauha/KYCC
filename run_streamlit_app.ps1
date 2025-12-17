# KYCC Streamlit App Launcher
# Starts both the Backend and the Streamlit Frontend

$ErrorActionPreference = "Stop"

function Test-PortInUse {
    param([int]$Port)
    try {
        $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
        return $null -ne $connection
    }
    catch {
        return $false
    }
}

function Kill-ProcessOnPort {
    param([int]$Port)
    $process = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | 
               ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
    
    if ($process) {
        Write-Host "[WARN] Killing process on port $Port..."
        $process | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  KYCC Streamlit App Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Cleanup Ports
Write-Host "[INFO] Checking ports..."
Kill-ProcessOnPort -Port 8000
Kill-ProcessOnPort -Port 8501

# 2. Start Backend
Write-Host "[INFO] Starting Backend (Port 8000)..." -ForegroundColor Yellow
$backendScript = @"
Set-Location backend
`$env:FORCE_SQLITE_FALLBACK = "1"
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
"@
$backendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript -PassThru
Write-Host "[OK] Backend started (PID: $($backendProcess.Id))" -ForegroundColor Green
Start-Sleep -Seconds 5

# 3. Start Streamlit
Write-Host "[INFO] Starting Streamlit (Port 8501)..." -ForegroundColor Yellow
$frontendScript = @"
Set-Location frontend_streamlit
.\streamlit_venv\Scripts\Activate.ps1
streamlit run app.py --server.port 8501
"@
$frontendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript -PassThru
Write-Host "[OK] Streamlit started (PID: $($frontendProcess.Id))" -ForegroundColor Green

Write-Host ""
Write-Host "App is running at: http://localhost:8501" -ForegroundColor Cyan
Write-Host "Press Ctrl+C in this window to exit (you'll need to close the popped up windows manually)"
