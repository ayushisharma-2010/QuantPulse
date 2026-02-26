# Test Pathway Pipeline API Endpoints

Write-Host "Testing Pathway Pipeline API..." -ForegroundColor Green
Write-Host ""

# Test 1: Health Check
Write-Host "1. Health Check:" -ForegroundColor Yellow
curl http://localhost:8090/
Write-Host ""

# Test 2: Pipeline Status
Write-Host "2. Pipeline Status:" -ForegroundColor Yellow
curl http://localhost:8090/v1/status
Write-Host ""

# Test 3: Stock Data
Write-Host "3. Stock Data (RELIANCE.NS):" -ForegroundColor Yellow
curl http://localhost:8090/v1/ticker/RELIANCE.NS
Write-Host ""

# Test 4: Stock Data (TCS.NS)
Write-Host "4. Stock Data (TCS.NS):" -ForegroundColor Yellow
curl http://localhost:8090/v1/ticker/TCS.NS
Write-Host ""

# Test 5: Green Score
Write-Host "5. Green Score (RELIANCE.NS):" -ForegroundColor Yellow
curl http://localhost:8090/v1/green-score/RELIANCE.NS
Write-Host ""

# Test 6: RAG Query
Write-Host "6. RAG Query:" -ForegroundColor Yellow
$body = @{
    query = "What is the latest news about TCS?"
    symbols = @("TCS.NS")
    include_news = $true
    include_esg = $false
} | ConvertTo-Json

curl -X POST http://localhost:8090/v1/rag/query `
    -H "Content-Type: application/json" `
    -d $body
Write-Host ""

Write-Host "Tests complete!" -ForegroundColor Green
