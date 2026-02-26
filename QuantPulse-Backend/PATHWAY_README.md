# Pathway Real-Time Streaming Pipeline

This document explains how to run and test the Pathway streaming pipeline for QuantPulse.

## Overview

The Pathway pipeline provides:
- **Real-time stock data ingestion** from yfinance (or demo mode)
- **Streaming technical indicators** (RSI, MACD, Bollinger Bands, SMA, EMA, Volatility)
- **Document Store** for news and ESG documents with live indexing
- **RAG-powered Q&A** using LLM with retrieved context
- **Green Score calculation** from ESG data
- **REST API** on port 8090 for all features

## Quick Start

### 1. Install Dependencies

```bash
cd QuantPulse-Backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Edit `.env` file:

```bash
# Pathway Configuration
PATHWAY_MODE=demo          # Use 'demo' for testing without API keys
PATHWAY_PORT=8090
PATHWAY_POLL_INTERVAL=60

# Optional: For live mode and RAG
OPENAI_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
```

### 3. Seed Sample Data

```bash
# Seed ESG data (run once)
python pathway_data/seed_esg.py

# Seed news data (run once or continuously)
python pathway_data/seed_news.py --once
```

### 4. Start Pathway Pipeline

```bash
python pathway_pipeline.py
```

The pipeline will start on `http://localhost:8090`

## API Endpoints

### Health Check
```bash
curl http://localhost:8090/
```

### Get Stock Data with Indicators
```bash
curl http://localhost:8090/v1/ticker/RELIANCE.NS
```

Response:
```json
{
  "symbol": "RELIANCE.NS",
  "price": 2456.75,
  "volume": 5234567,
  "change_percent": 1.23,
  "timestamp": "2024-01-15T10:30:00",
  "indicators": {
    "rsi_14": 65.4,
    "sma_20": 2450.30,
    "sma_50": 2420.15,
    "macd": 12.45,
    "bb_upper": 2480.50,
    "bb_middle": 2450.30,
    "bb_lower": 2420.10,
    "volatility": 0.25
  }
}
```

### RAG Query
```bash
curl -X POST http://localhost:8090/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the latest news about RELIANCE?",
    "symbols": ["RELIANCE.NS"],
    "include_news": true,
    "include_esg": false
  }'
```

Response:
```json
{
  "answer": "Based on recent news articles, RELIANCE has...",
  "citations": [
    {
      "title": "RELIANCE Reports Strong Q4 Earnings",
      "source": "news",
      "url": "https://example.com/...",
      "excerpt": "..."
    }
  ],
  "timestamp": "2024-01-15T10:30:00"
}
```

### Get Green Score
```bash
curl http://localhost:8090/v1/green-score/RELIANCE.NS
```

Response:
```json
{
  "symbol": "RELIANCE.NS",
  "score": 75.3,
  "category": "high",
  "breakdown": {
    "carbon_emissions": 72.5,
    "water_usage": 78.2,
    "board_diversity": 68.9,
    "governance": 81.5
  },
  "timestamp": "2024-01-15T10:30:00"
}
```

### Pipeline Status
```bash
curl http://localhost:8090/v1/status
```

## Testing the Pipeline

### Test 1: Stock Data Ingestion
```bash
# Wait 10 seconds after starting pipeline
sleep 10

# Fetch stock data
curl http://localhost:8090/v1/ticker/TCS.NS

# Should return stock data with indicators
```

### Test 2: Document Indexing
```bash
# Seed some news
python pathway_data/seed_news.py --once

# Wait 30 seconds for indexing
sleep 30

# Query RAG
curl -X POST http://localhost:8090/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about TCS stock"}'
```

### Test 3: Green Score
```bash
# Seed ESG data
python pathway_data/seed_esg.py

# Wait 30 seconds
sleep 30

# Get green score
curl http://localhost:8090/v1/green-score/INFY.NS
```

## Running in Different Modes

### Demo Mode (No API Keys Required)
```bash
# In .env
PATHWAY_MODE=demo

# Start pipeline
python pathway_pipeline.py
```

Demo mode generates simulated stock data and works without any API keys.

### Live Mode (Requires API Keys)
```bash
# In .env
PATHWAY_MODE=live
OPENAI_API_KEY=your_key_here

# Start pipeline
python pathway_pipeline.py
```

Live mode fetches real data from yfinance and uses OpenAI for RAG.

## Continuous News Seeding

For demo purposes, run news seeding in the background:

```bash
# Terminal 1: Start Pathway pipeline
python pathway_pipeline.py

# Terminal 2: Start continuous news seeding
python pathway_data/seed_news.py
```

News will be added every 2 minutes and automatically indexed by Pathway.

## Troubleshooting

### Pipeline won't start
- Check if port 8090 is available
- Verify Python dependencies are installed
- Check `.env` file configuration

### No stock data returned
- Wait at least 60 seconds after starting (first poll interval)
- Check logs for errors
- Try demo mode first

### RAG queries return no results
- Ensure documents are seeded (`seed_news.py`, `seed_esg.py`)
- Wait 30 seconds after seeding for indexing
- Check `pathway_data/news/` and `pathway_data/esg/` directories have files

### Indicators are null
- Indicators require historical data (at least 14-200 data points)
- In demo mode, wait for multiple poll cycles
- Check that stock aggregator is receiving data

## Architecture

```
┌─────────────────────────────────────────┐
│     Pathway Pipeline (:8090)            │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │  Stock Data Connector           │   │
│  │  (yfinance / demo)              │   │
│  └─────────────────────────────────┘   │
│              ↓                          │
│  ┌─────────────────────────────────┐   │
│  │  Technical Indicators           │   │
│  │  (RSI, MACD, BB, SMA, EMA)      │   │
│  └─────────────────────────────────┘   │
│              ↓                          │
│  ┌─────────────────────────────────┐   │
│  │  Document Stores                │   │
│  │  - News (pathway_data/news/)    │   │
│  │  - ESG (pathway_data/esg/)      │   │
│  └─────────────────────────────────┘   │
│              ↓                          │
│  ┌─────────────────────────────────┐   │
│  │  RAG Engine + Green Score       │   │
│  └─────────────────────────────────┘   │
│              ↓                          │
│  ┌─────────────────────────────────┐   │
│  │  REST API Endpoints             │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## Next Steps

1. **Integrate with FastAPI Backend**: Create proxy endpoints in main backend
2. **Add Frontend Components**: Build UI for live streaming and RAG chat
3. **Deploy**: Configure for production deployment
4. **Optimize**: Add caching, connection pooling, error recovery

## Hackathon Demo

For the hackathon demo:

1. Start pipeline in demo mode
2. Seed news and ESG data
3. Show live stock data with indicators
4. Demonstrate RAG queries
5. Show green scores
6. Highlight real-time updates

All three Pathway requirements are met:
✅ Live data ingestion (stock connector)
✅ Streaming transformations (technical indicators)
✅ LLM integration (RAG with Document Store)
