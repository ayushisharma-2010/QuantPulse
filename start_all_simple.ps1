# QuantPulse - Simple Startup Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  QuantPulse - Starting All Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Pathway Pipeline
Write-Host "[1/3] Starting Pathway Pipeline (Port 8090)..." -ForegroundColor Cyan
$pathwayCmd = "cd '$PWD\QuantPulse-Backend'; Write-Host 'Pathway Pipeline Running' -ForegroundColor Green; python pathway_pipeline.py"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $pathwayCmd

Start-Sleep -Seconds 8

# Start Main Backend
Write-Host "[2/3] Starting Main Backend (Port 3000)..." -ForegroundColor Cyan
$backendCmd = "cd '$PWD\QuantPulse-Backend'; Write-Host 'Main Backend Running' -ForegroundColor Green; python -m uvicorn app.main:app --reload --port 3000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

Start-Sleep -Seconds 5

# Start Frontend
Write-Host "[3/3] Starting Frontend (Port 5173)..." -ForegroundColor Cyan
$frontendCmd = "cd '$PWD\QuantPulse-Frontend'; Write-Host 'Frontend Running' -ForegroundColor Green; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Services:" -ForegroundColor Cyan
Write-Host "  Pathway Pipeline: http://localhost:8090" -ForegroundColor White
Write-Host "  Main Backend:     http://localhost:3000" -ForegroundColor White
Write-Host "  Frontend:         http://localhost:5173" -ForegroundColor White
Write-Host ""
Write-Host "Open http://localhost:5173 in your browser!" -ForegroundColor Yellow
Write-Host ""
