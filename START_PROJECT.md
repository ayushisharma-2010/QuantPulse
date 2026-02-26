# QuantPulse - Complete Startup Guide

This guide will help you run the complete QuantPulse project with Pathway integration locally.

## Prerequisites

- Python 3.13+ installed
- Node.js 18+ installed
- Git installed

## Project Architecture

The project consists of 3 components:
1. **Main Backend** (FastAPI) - Port 3000
2. **Pathway Pipeline** (Streaming) - Port 8090
3. **Frontend** (React + Vite) - Port 5173

## Quick Start (3 Commands)

Open 3 separate terminals and run:

### Terminal 1: Pathway Pipeline
```bash
cd QuantPulse-Backend
python pathway_pipeline.py
```

### Terminal 2: Main Backend
```bash
cd QuantPulse-Backend
python -m uvicorn app.main:app --reload --port 3000
```

### Terminal 3: Frontend
```bash
cd QuantPulse-Frontend
npm run dev
```

## Detailed Setup Instructions

### 1. Backend Setup (First Time Only)

```bash
cd QuantPulse-Backend

# Install Python dependencies
pip install -r requirements.txt

# Verify .env file has API keys
# Make sure these are set:
# - GROQ_API_KEY=your_groq_api_key_here
# - SERPER_API_KEY=your_serper_api_key_here
```

### 2. Frontend Setup (First Time Only)

```bash
cd QuantPulse-Frontend

# Install Node dependencies
npm install
```

### 3. Start All Services

#### Option A: Manual (Recommended for Development)

**Terminal 1 - Pathway Pipeline:**
```bash
cd QuantPulse-Backend
python pathway_pipeline.py
```
Wait for: `Uvicorn running on http://0.0.0.0:8090`

**Terminal 2 - Main Backend:**
```bash
cd QuantPulse-Backend
python -m uvicorn app.main:app --reload --port 3000
```
Wait for: `Uvicorn running on http://127.0.0.1:3000`

**Terminal 3 - Frontend:**
```bash
cd QuantPulse-Frontend
npm run dev
```
Wait for: `Local: http://localhost:5173/`

#### Option B: Using PowerShell Script (Windows)

Create and run `start_all.ps1`:
```powershell
# Start Pathway Pipeline
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd QuantPulse-Backend; python pathway_pipeline.py"

# Wait 5 seconds
Start-Sleep -Seconds 5

# Start Main Backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd QuantPulse-Backend; python -m uvicorn app.main:app --reload --port 3000"

# Wait 5 seconds
Start-Sleep -Seconds 5

# Start Frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd QuantPulse-Frontend; npm run dev"

Write-Host "All services started!"
Write-Host "Pathway Pipeline: http://localhost:8090"
Write-Host "Main Backend: http://localhost:3000"
Write-Host "Frontend: http://localhost:5173"
```

## Verify Everything is Running

### 1. Check Pathway Pipeline
```bash
curl http://localhost:8090/v1/status
```
Should return: `{"status":"running","mode":"demo",...}`

### 2. Check Main Backend
```bash
curl http://localhost:3000/health
```
Should return: `{"status":"healthy"}`

### 3. Check Frontend
Open browser: http://localhost:5173

## Testing the Pathway Integration

### Test Stock Data
```bash
curl http://localhost:8090/v1/ticker/RELIANCE.NS
```

### Test RAG Query
```bash
curl -X POST http://localhost:8090/v1/rag/query \
  -H "Content-Type: application/json" \
  -d "{\"query\":\"What is the latest news about Reliance?\",\"symbols\":[\"RELIANCE.NS\"]}"
```

### Test Green Score
```bash
curl http://localhost:8090/v1/green-score/RELIANCE.NS
```

### Run Comprehensive Tests
```bash
cd QuantPulse-Backend
python test_quick.py
```

## Troubleshooting

### Port Already in Use

**Pathway (8090):**
```bash
# Windows
netstat -ano | findstr :8090
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8090 | xargs kill -9
```

**Backend (3000):**
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:3000 | xargs kill -9
```

**Frontend (5173):**
```bash
# Windows
netstat -ano | findstr :5173
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:5173 | xargs kill -9
```

### Pathway Not Starting

1. Check if Python dependencies are installed:
   ```bash
   pip list | findstr pathway
   ```

2. Check .env file has API keys

3. Check logs for errors

### Backend Not Starting

1. Check if port 3000 is free
2. Verify database is accessible
3. Check .env configuration

### Frontend Not Starting

1. Check if node_modules exists:
   ```bash
   cd QuantPulse-Frontend
   npm install
   ```

2. Check if port 5173 is free

## Features Available

### Pathway Pipeline Features
- ✅ Live stock data ingestion (demo mode)
- ✅ Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- ✅ RAG with Groq LLM
- ✅ ESG/Green scores
- ✅ News document indexing

### Main Backend Features
- ✅ Stock analysis
- ✅ War Room agents
- ✅ User authentication
- ✅ Historical data

### Frontend Features
- ✅ Dashboard
- ✅ Stock analysis
- ✅ War Room
- ✅ Portfolio management

## API Endpoints

### Pathway Pipeline (Port 8090)
- `GET /` - Health check
- `GET /v1/status` - Pipeline status
- `GET /v1/ticker/{symbol}` - Stock data + indicators
- `POST /v1/rag/query` - RAG Q&A
- `GET /v1/green-score/{symbol}` - ESG score

### Main Backend (Port 3000)
- `GET /health` - Health check
- `GET /api/stocks` - Stock list
- `POST /api/analysis` - Stock analysis
- `POST /api/warroom` - War room agents
- `POST /api/auth/login` - User login

## Environment Variables

### Backend (.env)
```env
# Required for Pathway
GROQ_API_KEY=your_groq_api_key_here
SERPER_API_KEY=your_serper_api_key_here
PATHWAY_PORT=8090
PATHWAY_MODE=demo

# Backend
PORT=3000
SECRET_KEY=your-secret-key
```

### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:3000
```

**Note:** The frontend .env file has been created with the correct backend URL.

## Stopping All Services

### Manual
Press `Ctrl+C` in each terminal

### PowerShell
```powershell
# Kill all Python processes (careful!)
Get-Process python | Stop-Process -Force

# Kill all Node processes (careful!)
Get-Process node | Stop-Process -Force
```

## Next Steps

1. Open http://localhost:5173 in your browser
2. Explore the dashboard
3. Try the War Room feature
4. Test the Pathway integration

## Support

For issues:
1. Check logs in each terminal
2. Verify all ports are free
3. Ensure API keys are configured
4. Run test suite: `python test_quick.py`

## Hackathon Demo

For the hackathon demo, make sure to highlight:
1. **Live Data Ingestion** - Show stock data updating
2. **Streaming Transformations** - Show technical indicators
3. **LLM Integration** - Demonstrate RAG queries

All 3 mandatory requirements are implemented and tested! 🎉
