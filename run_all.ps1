# KYCC Master Run Script
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

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

function Find-AvailablePort {
    param([int]$StartPort)
    $port = $StartPort
    $maxAttempts = 10
    $attempts = 0
    
    while ((Test-PortInUse -Port $port) -and $attempts -lt $maxAttempts) {
        Write-Host "[WARN] Port $port in use, trying $($port + 1)..."
        $port++
        $attempts++
    }
    
    return $port
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

# Find available ports
Write-Host ""
Write-Host "========================================"
Write-Host "  KYCC Startup"
Write-Host "========================================"
Write-Host ""
Write-Host "[INFO] Finding available ports..."

$BackendPort = Find-AvailablePort -StartPort $BackendPort
$FrontendPort = Find-AvailablePort -StartPort $FrontendPort

Write-Host "[OK] Backend port: $BackendPort"
Write-Host "[OK] Frontend port: $FrontendPort"

# Validate
Write-Host "[INFO] Validating environment..."
if (-not (Test-Path "backend/main.py")) {
    Write-Host "[FAIL] Not in KYCC root directory!"
    exit 1
}
if (-not (Test-Path "backend/venv")) {
    Write-Host "[FAIL] Virtual environment not found!"
    exit 1
}
Write-Host "[OK] Environment validated"

# Update frontend config
Write-Host "[INFO] Updating frontend API config..."
$apiUrl = "http://127.0.0.1:$BackendPort"
$configContent = @"
import axios from "axios";

const apiClient = axios.create({
  baseURL: "$apiUrl",
  headers: {
    "Content-Type": "application/json",
  },
});

export default apiClient;
"@
Set-Content -Path "frontend/src/api/client.js" -Value $configContent
Write-Host "[OK] Frontend configured: $apiUrl"

# Cleanup
Write-Host "[INFO] Cleaning up old processes..."
Kill-ProcessOnPort -Port $BackendPort
Kill-ProcessOnPort -Port $FrontendPort
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*uvicorn*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Cleanup complete"

# Start backend
Write-Host "[INFO] Starting backend on port $BackendPort..."
$backendScript = @"
Set-Location backend
`$env:FORCE_SQLITE_FALLBACK = "1"
.\venv\Scripts\Activate.ps1
python -m uvicorn main:app --host 127.0.0.1 --port $BackendPort --reload
"@
$backendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendScript -PassThru
Write-Host "[OK] Backend started (PID: $($backendProcess.Id))"
Start-Sleep -Seconds 3

# Start frontend
Write-Host "[INFO] Starting frontend on port $FrontendPort..."
$frontendScript = @"
Set-Location frontend
npm install --silent
npm run dev -- --port $FrontendPort
"@
$frontendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendScript -PassThru
Write-Host "[OK] Frontend started (PID: $($frontendProcess.Id))"
Start-Sleep -Seconds 3

# Summary
Write-Host ""
Write-Host "========================================"
Write-Host "  Services Running"
Write-Host "========================================"
Write-Host ""
Write-Host "Frontend:  http://localhost:$FrontendPort"
Write-Host "Backend:   http://127.0.0.1:$BackendPort"
Write-Host "API Docs:  http://127.0.0.1:$BackendPort/docs"
Write-Host ""
Write-Host "Database:  PostgreSQL at localhost:5433"
Write-Host "           (SQLite fallback enabled)"
Write-Host ""
Write-Host "Press Ctrl+C to stop all services"
Write-Host ""

# Monitor
while ($true) {
    Start-Sleep -Seconds 30
    if (-not (Get-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue)) {
        Write-Host "[FAIL] Backend crashed"
        break
    }
}

$backendProcess | Stop-Process -Force -ErrorAction SilentlyContinue
$frontendProcess | Stop-Process -Force -ErrorAction SilentlyContinue
Write-Host "[OK] Services stopped"
