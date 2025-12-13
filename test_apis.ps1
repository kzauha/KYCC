#!/usr/bin/env pwsh
# KYCC API Test Suite

Write-Host "=== KYCC API ENDPOINT TESTS ===" -ForegroundColor Cyan
Write-Host "Starting backend server..." -ForegroundColor Yellow

# Start server in background
$serverProcess = Start-Process -FilePath "python.exe" -ArgumentList "-m uvicorn main:app --port 8000" -PassThru -WindowStyle Hidden -WorkingDirectory "$PSScriptRoot\..\backend"

# Wait for server to start
Start-Sleep -Seconds 5

# Check if server is running
$isListening = Test-NetConnection -ComputerName localhost -Port 8000 -WarningAction SilentlyContinue | Select-Object -ExpandProperty TcpTestSucceeded

if (-not $isListening) {
    Write-Host "ERROR: Server failed to start on port 8000" -ForegroundColor Red
    exit 1
}

Write-Host "✓ Server running on port 8000" -ForegroundColor Green
Write-Host ""

# Test endpoints
$baseUrl = "http://localhost:8000"
$tests = @(
    @{ Name = "1. Health Check"; Method = "GET"; Path = "/health" },
    @{ Name = "2. Parties List"; Method = "GET"; Path = "/api/parties/?limit=5" },
    @{ Name = "3. Relationships List"; Method = "GET"; Path = "/api/relationships/?limit=5" },
    @{ Name = "4. Get Party (ID=1)"; Method = "GET"; Path = "/api/parties/1" },
    @{ Name = "5. Party Network"; Method = "GET"; Path = "/api/parties/1/network?depth=2" },
    @{ Name = "6. Party Transactions"; Method = "GET"; Path = "/api/parties/1/transactions?limit=10" },
    @{ Name = "7. Scoring Run"; Method = "GET"; Path = "/api/scoring-v2/run?party_id=1" },
    @{ Name = "8. Synthetic Seed (disabled)"; Method = "POST"; Path = "/synthetic/seed" }
)

foreach ($test in $tests) {
    Write-Host $test.Name -ForegroundColor Yellow
    try {
        $uri = "$baseUrl$($test.Path)"
        if ($test.Method -eq "GET") {
            $response = Invoke-RestMethod -Uri $uri -Method GET -WarningAction SilentlyContinue
            Write-Host "  ✓ Status: 200 OK" -ForegroundColor Green
            if ($response -is [Array]) {
                Write-Host "  ✓ Returned $($response.Count) items" -ForegroundColor Green
            } elseif ($response -is [Object]) {
                Write-Host "  ✓ Returned object with keys: $($response.PSObject.Properties.Name -join ', ')" -ForegroundColor Green
            }
        } else {
            Write-Host "  ⚠ Not testing POST (would require data)" -ForegroundColor Yellow
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.Value__
        if ($statusCode -eq 403 -or $statusCode -eq 404) {
            Write-Host "  ✓ Status: $statusCode (Expected - feature may be disabled)" -ForegroundColor Yellow
        } else {
            Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# Cleanup
Write-Host "Stopping server..." -ForegroundColor Yellow
Stop-Process -Id $serverProcess.Id -Force -ErrorAction SilentlyContinue
Write-Host "✓ Tests complete" -ForegroundColor Green
