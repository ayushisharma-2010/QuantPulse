# QuantPulse - Complete Startup Script
# This script starts all 3 components of the QuantPulse project

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  QuantPulse - Starting All Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "QuantPulse-Backend") -or -not (Test-Path "QuantPulse-Frontend")) {
    Write-Host "Error: Please run this script from the project root directory" -ForegroundColor Red
    Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
    exit 1
}

# Function to check if port is in use
function Test-Port {
    param($Port)
    $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet
    return $connection
}

# Check if ports are available
Write-Host "Checking ports..." -ForegroundColor Yellow

$ports = @{
    "8090" = "Pathway Pipeline"
    "3000" = "Main Backend"
    "5173" = "Frontend"
}

$portsInUse = @()
foreach ($port in $ports.Keys) {
    if (Test-Port $port) {
        Write-Host "  Port $port ($($ports[$port])) is already in use!" -ForegroundColor Red
        $portsInUse += $port
    } else {
        Write-Host "  Port $port ($($ports[$port])) is available" -ForegroundColor Green
    }
}

if ($portsInUse.Count -gt 0) {
    Write-Host ""
    Write-Host "Warning: Some ports are in use. Do you want to continue anyway? (y/n)" -ForegroundColor Yellow
    $response = Read-Host
    if ($response -ne "y") {
        Write-Host "Startup cancelled." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Starting services..." -ForegroundColor Yellow
Write-Host ""

# Start Pathway Pipeline
Write-Host "[1/3] Starting Pathway Pipeline (Port 8090)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host 'Pathway Pipeline' -ForegroundColor Green; " +
    "cd '$PWD\QuantPulse-Backend'; " +
    "python pathway_pipeline.py"

Write-Host "  Waiting 8 seconds for Pathway to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 8

# Start Main Backend
Write-Host "[2/3] Starting Main Backend (Port 3000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host 'Main Backend' -ForegroundColor Green; " +
    "cd '$PWD\QuantPulse-Backend'; " +
    "python -m uvicorn app.main:app --reload --port 3000"

Write-Host "  Waiting 5 seconds for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Start Frontend
Write-Host "[3/3] Starting Frontend (Port 5173)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Write-Host 'Frontend' -ForegroundColor Green; " +
    "cd '$PWD\QuantPulse-Frontend'; " +
    "npm run dev"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All Services Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  Pathway Pipeline: http://localhost:8090" -ForegroundColor White
Write-Host "  Main Backend:     http://localhost:3000" -ForegroundColor White
Write-Host "  Frontend:         http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Testing endpoints..." -ForegroundColor Yellow

# Wait a bit more for services to fully start
Start-Sleep -Seconds 3

# Test Pathway
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8090/" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "  Pathway Pipeline: OK" -ForegroundColor Green
    }
} catch {
    Write-Host "  Pathway Pipeline: Not responding yet (may need more time)" -ForegroundColor Yellow
}

# Test Backend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000/health" -UseBasicParsing -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "  Main Backend: OK" -ForegroundColor Green
    }
} catch {
    Write-Host "  Main Backend: Not responding yet (may need more time)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "  1. Open http://localhost:5173 in your browser" -ForegroundColor White
Write-Host "  2. Check the 3 terminal windows for logs" -ForegroundColor White
Write-Host "  3. Run tests: cd QuantPulse-Backend; python test_quick.py" -ForegroundColor White
Write-Host ""
Write-Host "To stop all services, close the 3 terminal windows" -ForegroundColor Gray
Write-Host ""
