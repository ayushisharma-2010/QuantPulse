# QuantPulse - Quick Start Guide

## 🚀 Start the Project in 3 Steps

### Step 1: Start Pathway Pipeline
Open a new terminal and run:
```bash
cd QuantPulse-Backend
python pathway_pipeline.py
```
✅ On **Linux/WSL**: Wait for `Starting Pathway engine (pw.run)...` — stock data streams automatically every 60s
✅ On **Windows**: Falls back to standalone mode — `Uvicorn running on http://0.0.0.0:8090`

### Step 2: Start Main Backend
Open a **second** terminal and run:
```bash
cd QuantPulse-Backend
python -m uvicorn app.main:app --reload --port 3000
```
✅ Wait for: `Uvicorn running on http://127.0.0.1:3000`

### Step 3: Start Frontend
Open a **third** terminal and run:
```bash
cd QuantPulse-Frontend
npm run dev
```
✅ Wait for: `Local: http://localhost:5173/`

## 🌐 Access the Application

Open your browser and go to: **http://localhost:5173**

## ✅ Verify Everything Works

### Quick Test
```bash
cd QuantPulse-Backend
python test_quick.py
```

Should show: `Total: 5/5 tests passed (100%)`

### Manual Tests

**Test Pathway:**
```bash
curl http://localhost:8090/v1/status
```

**Test Backend:**
```bash
curl http://localhost:3000/health
```

**Test Frontend:**
Open http://localhost:5173 in browser

## 🛑 Stop All Services

Press `Ctrl+C` in each of the 3 terminals

## 📊 What's Running?

| Service | Port | URL |
|---------|------|-----|
| Pathway Pipeline | 8090 | http://localhost:8090 |
| Main Backend | 3000 | http://localhost:3000 |
| Frontend | 5173 | http://localhost:5173 |

## 🎯 Key Features

### Pathway Pipeline (Port 8090)
- ✅ Live stock data (Reliance: ~₹1,400)
- ✅ Technical indicators (RSI, MACD, Bollinger Bands)
- ✅ RAG with Groq LLM
- ✅ ESG/Green scores

### Main Backend (Port 3000)
- ✅ Stock analysis
- ✅ War Room agents
- ✅ User authentication

### Frontend (Port 5173)
- ✅ Dashboard
- ✅ Stock analysis
- ✅ War Room
- ✅ Portfolio management

## 🐛 Troubleshooting

### Port Already in Use?

**Kill process on port 8090:**
```bash
netstat -ano | findstr :8090
taskkill /PID <PID> /F
```

**Kill process on port 3000:**
```bash
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**Kill process on port 5173:**
```bash
netstat -ano | findstr :5173
taskkill /PID <PID> /F
```

### Pathway Not Starting?

1. Check Python version: `python --version` (need 3.13+)
2. Install dependencies: `pip install -r requirements.txt`
3. Check .env file has API keys

### Backend Not Starting?

1. Check if port 3000 is free
2. Verify .env configuration
3. Check database connection

### Frontend Not Starting?

1. Install dependencies: `npm install`
2. Check if port 5173 is free
3. Verify .env has `VITE_API_BASE_URL=http://localhost:3000`

## 🎉 Hackathon Demo

All 3 mandatory requirements are implemented:
1. ✅ **Live Data Ingestion** - Stock connector with 60s polling
2. ✅ **Streaming Transformations** - Technical indicators computation
3. ✅ **LLM Integration** - RAG with Groq

Test results: **11/11 tests passing (100%)**

## 📝 API Endpoints

### Pathway Pipeline
- `GET /v1/status` - Pipeline status
- `GET /v1/ticker/RELIANCE.NS` - Stock data
- `POST /v1/rag/query` - RAG Q&A
- `GET /v1/green-score/RELIANCE.NS` - ESG score

### Main Backend
- `GET /health` - Health check
- `GET /api/stocks` - Stock list
- `POST /api/analysis` - Stock analysis
- `POST /api/warroom` - War room agents

## 🔑 Environment Variables

Already configured in `.env` files:
- ✅ GROQ_API_KEY (for RAG)
- ✅ SERPER_API_KEY (for search)
- ✅ PATHWAY_PORT=8090
- ✅ PATHWAY_MODE=demo

## 📚 More Information

- Full guide: `START_PROJECT.md`
- Pathway status: `QuantPulse-Backend/PATHWAY_STATUS.md`
- Pathway README: `QuantPulse-Backend/PATHWAY_README.md`
