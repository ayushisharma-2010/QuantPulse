# Design Document: Pathway Real-Time Streaming RAG Integration

## Overview

This design transforms QuantPulse from a cached API-based stock analytics platform into a real-time streaming analytics system using the Pathway framework. The integration introduces three core capabilities:

1. **Real-Time Data Streaming**: Live stock market data ingestion and processing using Pathway connectors and streaming tables
2. **Streaming Technical Indicators**: Incremental computation of RSI, MACD, Bollinger Bands, and Moving Averages using Pathway window operations
3. **RAG-Powered Financial Intelligence**: Live document indexing with vector search and LLM-powered Q&A using Pathway's Document Store and LLM xPack

The system maintains QuantPulse's existing FastAPI architecture while adding a parallel Pathway streaming pipeline that processes data incrementally, provides WebSocket updates to the frontend, and enables natural language queries over live market data.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Stock Charts │  │ RAG Chatbot  │  │ Anomaly Feed │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                    │ REST API           │ WebSocket
                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  New Pathway Integration Layer                           │   │
│  │  - /api/v1/streaming/* endpoints                         │   │
│  │  - /ws/streaming/* WebSocket handlers                    │   │
│  │  - /api/v1/rag/* endpoints                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Existing Services (stock_service, cache_service, etc.)  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Pathway Streaming Pipeline                    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Ingestion Layer                                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │ Stock Data   │  │ News Feed    │  │ Document     │    │ │
│  │  │ Connector    │  │ Connector    │  │ Watcher      │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Transformation Layer                                      │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │ Technical    │  │ Anomaly      │  │ Document     │    │ │
│  │  │ Indicators   │  │ Detection    │  │ Store        │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Output Layer                                              │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │ Streaming    │  │ Alert        │  │ RAG Query    │    │ │
│  │  │ Tables       │  │ Events       │  │ Engine       │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Data Sources                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ TwelveData   │  │ Finnhub API  │  │ News APIs    │          │
│  │ API          │  │              │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

1. **Data Ingestion**: Pathway connectors poll external APIs (TwelveData/Finnhub) at configurable intervals, creating streaming tables
2. **Incremental Processing**: Pathway applies transformations (joins, filters, window operations) incrementally as new data arrives
3. **FastAPI Integration**: FastAPI endpoints query Pathway tables and subscribe to change notifications
4. **WebSocket Broadcasting**: When Pathway tables update, FastAPI broadcasts changes to connected WebSocket clients
5. **RAG Queries**: User questions trigger retrieval from Document Store, context assembly, and LLM generation


## Components and Interfaces

### 1. Pathway Stock Data Connector

**Purpose**: Ingest live stock market data from TwelveData/Finnhub APIs into Pathway streaming tables.

**Implementation**:
```python
# QuantPulse-Backend/app/services/pathway_connector.py

import pathway as pw
from typing import List, Dict, Any
import requests
import time

class StockDataConnector:
    """Custom Pathway connector for stock market data"""
    
    def __init__(self, symbols: List[str], api_key: str, provider: str = "twelvedata"):
        self.symbols = symbols
        self.api_key = api_key
        self.provider = provider
        self.poll_interval = 5  # seconds
        
    def create_input_table(self) -> pw.Table:
        """Create Pathway input table from stock API"""
        
        @pw.io.python.connector(
            subject=self._fetch_stock_data,
            autocommit_duration_ms=self.poll_interval * 1000
        )
        class StockDataSource:
            symbol: str
            price: float
            volume: int
            timestamp: int
            change_percent: float
            
        return StockDataSource
    
    def _fetch_stock_data(self) -> List[Dict[str, Any]]:
        """Fetch data from stock API"""
        results = []
        for symbol in self.symbols:
            try:
                data = self._call_api(symbol)
                results.append({
                    'symbol': symbol,
                    'price': data['price'],
                    'volume': data['volume'],
                    'timestamp': int(time.time()),
                    'change_percent': data['change_percent']
                })
            except Exception as e:
                # Log error and continue with other symbols
                print(f"Error fetching {symbol}: {e}")
        return results
```

**Interface**:
- Input: List of stock symbols, API credentials
- Output: Pathway Table with columns: symbol, price, volume, timestamp, change_percent
- Configuration: Poll interval, retry logic, rate limiting


### 2. Technical Indicators Service

**Purpose**: Compute streaming technical indicators using Pathway window operations.

**Implementation**:
```python
# QuantPulse-Backend/app/services/pathway_indicators.py

import pathway as pw
from pathway.stdlib.ml.classifiers import knn_classifier

class TechnicalIndicatorsService:
    """Compute technical indicators on streaming stock data"""
    
    def __init__(self, stock_table: pw.Table):
        self.stock_table = stock_table
        
    def compute_rsi(self, period: int = 14) -> pw.Table:
        """Compute Relative Strength Index"""
        # Calculate price changes
        price_changes = self.stock_table.select(
            symbol=self.stock_table.symbol,
            price_change=self.stock_table.price - pw.this.price.lag(1)
        )
        
        # Separate gains and losses
        gains_losses = price_changes.select(
            symbol=price_changes.symbol,
            gain=pw.if_else(price_changes.price_change > 0, price_changes.price_change, 0),
            loss=pw.if_else(price_changes.price_change < 0, -price_changes.price_change, 0)
        )
        
        # Calculate average gains and losses using window
        avg_gain_loss = gains_losses.windowby(
            gains_losses.symbol,
            window=pw.temporal.sliding(duration=period),
            behavior=pw.temporal.exactly_once_behavior()
        ).reduce(
            symbol=gains_losses.symbol,
            avg_gain=pw.reducers.avg(gains_losses.gain),
            avg_loss=pw.reducers.avg(gains_losses.loss)
        )
        
        # Calculate RSI
        rsi = avg_gain_loss.select(
            symbol=avg_gain_loss.symbol,
            rsi=100 - (100 / (1 + (avg_gain_loss.avg_gain / avg_gain_loss.avg_loss)))
        )
        
        return rsi
    
    def compute_moving_average(self, period: int) -> pw.Table:
        """Compute Simple Moving Average"""
        ma = self.stock_table.windowby(
            self.stock_table.symbol,
            window=pw.temporal.sliding(duration=period),
            behavior=pw.temporal.exactly_once_behavior()
        ).reduce(
            symbol=self.stock_table.symbol,
            ma=pw.reducers.avg(self.stock_table.price)
        )
        return ma
    
    def compute_bollinger_bands(self, period: int = 20, std_dev: float = 2.0) -> pw.Table:
        """Compute Bollinger Bands"""
        # Calculate moving average and standard deviation
        stats = self.stock_table.windowby(
            self.stock_table.symbol,
            window=pw.temporal.sliding(duration=period),
            behavior=pw.temporal.exactly_once_behavior()
        ).reduce(
            symbol=self.stock_table.symbol,
            ma=pw.reducers.avg(self.stock_table.price),
            std=pw.reducers.stddev(self.stock_table.price)
        )
        
        # Calculate bands
        bands = stats.select(
            symbol=stats.symbol,
            upper_band=stats.ma + (std_dev * stats.std),
            middle_band=stats.ma,
            lower_band=stats.ma - (std_dev * stats.std)
        )
        
        return bands
```

**Interface**:
- Input: Pathway Table with stock price data
- Output: Pathway Tables with computed indicators (RSI, MA, Bollinger Bands, MACD)
- Configuration: Indicator periods, window sizes


### 3. Pathway Document Store Service

**Purpose**: Index financial documents and news for RAG-powered queries.

**Implementation**:
```python
# QuantPulse-Backend/app/services/pathway_document_store.py

import pathway as pw
from pathway.xpacks.llm import embedders, splitters, parsers
from pathway.xpacks.llm.vector_store import VectorStoreServer

class PathwayDocumentStore:
    """Live document indexing with vector search"""
    
    def __init__(self, embedding_model: str = "openai"):
        self.embedding_model = embedding_model
        self.vector_store = None
        
    def create_document_pipeline(self, document_sources: List[str]) -> pw.Table:
        """Create document ingestion and indexing pipeline"""
        
        # Watch multiple document sources
        documents = pw.io.fs.read(
            *document_sources,
            format="binary",
            mode="streaming",
            with_metadata=True
        )
        
        # Parse documents (PDF, TXT, HTML)
        parsed = documents.select(
            data=parsers.ParseUnstructured(documents.data),
            metadata=documents.metadata
        )
        
        # Split into chunks
        chunked = parsed.select(
            chunks=splitters.TokenCountSplitter(
                max_tokens=400,
                encoding="cl100k_base"
            )(parsed.data)
        ).flatten(pw.this.chunks)
        
        # Generate embeddings
        embedded = chunked.select(
            text=chunked.chunks,
            metadata=chunked.metadata,
            embedding=embedders.OpenAIEmbedder(
                model="text-embedding-ada-002"
            )(chunked.chunks)
        )
        
        return embedded
    
    def create_vector_store(self, embedded_docs: pw.Table) -> VectorStoreServer:
        """Create vector store server for retrieval"""
        self.vector_store = VectorStoreServer(
            embedded_docs,
            embedder=embedders.OpenAIEmbedder(model="text-embedding-ada-002")
        )
        return self.vector_store
    
    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Perform hybrid semantic + BM25 search"""
        # Semantic search using embeddings
        semantic_results = self.vector_store.query(query, k=top_k)
        
        # BM25 keyword search (simplified)
        # In production, combine both results with score fusion
        
        return semantic_results
```

**Interface**:
- Input: Document sources (file paths, URLs), embedding model configuration
- Output: Vector store with indexed documents, search API
- Configuration: Chunk size, embedding model, search parameters


### 4. RAG Query Engine

**Purpose**: Answer natural language questions using LLM with retrieved context.

**Implementation**:
```python
# QuantPulse-Backend/app/services/pathway_rag_engine.py

import pathway as pw
from pathway.xpacks.llm import llms, prompts
from typing import Dict, List, Any

class PathwayRAGEngine:
    """LLM-powered Q&A with live market context"""
    
    def __init__(self, document_store, stock_table: pw.Table, llm_provider: str = "openai"):
        self.document_store = document_store
        self.stock_table = stock_table
        self.llm = self._initialize_llm(llm_provider)
        
    def _initialize_llm(self, provider: str):
        """Initialize LLM client"""
        if provider == "openai":
            return llms.OpenAIChat(model="gpt-4")
        elif provider == "groq":
            return llms.LiteLLMChat(model="groq/llama-3.1-70b-versatile")
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    def query(self, question: str, symbols: List[str] = None) -> Dict[str, Any]:
        """Answer question with retrieved context"""
        
        # 1. Retrieve relevant documents
        doc_context = self.document_store.hybrid_search(question, top_k=5)
        
        # 2. Get current stock data if symbols mentioned
        stock_context = []
        if symbols:
            for symbol in symbols:
                latest = self.stock_table.filter(
                    self.stock_table.symbol == symbol
                ).select(
                    symbol=self.stock_table.symbol,
                    price=self.stock_table.price,
                    change_percent=self.stock_table.change_percent
                ).latest()
                stock_context.append(latest)
        
        # 3. Build prompt with context
        prompt = self._build_prompt(question, doc_context, stock_context)
        
        # 4. Generate response
        response = self.llm.generate(prompt)
        
        # 5. Extract citations
        citations = self._extract_citations(doc_context)
        
        return {
            "answer": response,
            "citations": citations,
            "stock_data": stock_context,
            "timestamp": int(time.time())
        }
    
    def _build_prompt(self, question: str, docs: List, stocks: List) -> str:
        """Build LLM prompt with context"""
        context_parts = []
        
        # Add document context
        if docs:
            doc_text = "\n\n".join([d['text'] for d in docs])
            context_parts.append(f"Relevant Financial Documents:\n{doc_text}")
        
        # Add stock data context
        if stocks:
            stock_text = "\n".join([
                f"{s['symbol']}: ${s['price']} ({s['change_percent']:+.2f}%)"
                for s in stocks
            ])
            context_parts.append(f"Current Market Data:\n{stock_text}")
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""You are a financial analyst assistant. Answer the user's question using the provided context.
        
Context:
{context}

Question: {question}

Provide a clear, concise answer with specific data points and citations where applicable."""
        
        return prompt
    
    def _extract_citations(self, docs: List) -> List[Dict]:
        """Extract source citations from retrieved documents"""
        return [
            {
                "source": doc.get('metadata', {}).get('source', 'Unknown'),
                "timestamp": doc.get('metadata', {}).get('timestamp'),
                "excerpt": doc['text'][:200] + "..."
            }
            for doc in docs
        ]
```

**Interface**:
- Input: Natural language question, optional stock symbols
- Output: Answer text, citations, relevant stock data
- Configuration: LLM model, retrieval parameters, prompt templates


### 5. Anomaly Detection Service

**Purpose**: Detect unusual market patterns in real-time.

**Implementation**:
```python
# QuantPulse-Backend/app/services/pathway_anomaly_detector.py

import pathway as pw
from typing import Dict, Any

class PathwayAnomalyDetector:
    """Real-time market anomaly detection"""
    
    def __init__(self, stock_table: pw.Table, indicators_table: pw.Table):
        self.stock_table = stock_table
        self.indicators_table = indicators_table
        
    def detect_price_spikes(self, threshold_percent: float = 5.0) -> pw.Table:
        """Detect sudden price movements"""
        
        # Calculate 5-minute price change
        price_changes = self.stock_table.windowby(
            self.stock_table.symbol,
            window=pw.temporal.sliding(duration=300),  # 5 minutes
            behavior=pw.temporal.exactly_once_behavior()
        ).reduce(
            symbol=self.stock_table.symbol,
            start_price=pw.reducers.first(self.stock_table.price),
            end_price=pw.reducers.last(self.stock_table.price),
            timestamp=pw.reducers.last(self.stock_table.timestamp)
        )
        
        # Calculate percent change
        changes_with_pct = price_changes.select(
            symbol=price_changes.symbol,
            change_percent=((price_changes.end_price - price_changes.start_price) 
                           / price_changes.start_price * 100),
            timestamp=price_changes.timestamp
        )
        
        # Filter for anomalies
        anomalies = changes_with_pct.filter(
            pw.this.change_percent.abs() > threshold_percent
        ).select(
            symbol=pw.this.symbol,
            anomaly_type="price_spike",
            severity=pw.if_else(
                pw.this.change_percent.abs() > 10, "high",
                pw.if_else(pw.this.change_percent.abs() > 7, "medium", "low")
            ),
            change_percent=pw.this.change_percent,
            timestamp=pw.this.timestamp
        )
        
        return anomalies
    
    def detect_volume_spikes(self, multiplier: float = 3.0) -> pw.Table:
        """Detect unusual volume activity"""
        
        # Calculate 20-period average volume
        avg_volume = self.stock_table.windowby(
            self.stock_table.symbol,
            window=pw.temporal.sliding(duration=20),
            behavior=pw.temporal.exactly_once_behavior()
        ).reduce(
            symbol=self.stock_table.symbol,
            avg_volume=pw.reducers.avg(self.stock_table.volume),
            current_volume=pw.reducers.last(self.stock_table.volume),
            timestamp=pw.reducers.last(self.stock_table.timestamp)
        )
        
        # Detect spikes
        volume_anomalies = avg_volume.filter(
            pw.this.current_volume > (pw.this.avg_volume * multiplier)
        ).select(
            symbol=pw.this.symbol,
            anomaly_type="volume_spike",
            severity="medium",
            volume_ratio=pw.this.current_volume / pw.this.avg_volume,
            timestamp=pw.this.timestamp
        )
        
        return volume_anomalies
    
    def generate_alert_with_explanation(self, anomaly: Dict, rag_engine) -> Dict[str, Any]:
        """Generate LLM explanation for anomaly"""
        
        question = f"Why is {anomaly['symbol']} experiencing a {anomaly['anomaly_type']}? " \
                   f"The {anomaly['anomaly_type']} is {anomaly.get('change_percent', anomaly.get('volume_ratio'))}."
        
        explanation = rag_engine.query(question, symbols=[anomaly['symbol']])
        
        return {
            "anomaly": anomaly,
            "explanation": explanation['answer'],
            "citations": explanation['citations']
        }
```

**Interface**:
- Input: Stock table, indicators table
- Output: Anomaly events with severity classification
- Configuration: Thresholds, detection windows, alert deduplication



### 6. FastAPI Integration Layer

**Purpose**: Bridge Pathway streaming pipeline with REST API and WebSocket endpoints.

**Implementation**:
```python
# QuantPulse-Backend/app/routers/streaming.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import List, Dict, Any
import asyncio

router = APIRouter(prefix="/api/v1/streaming", tags=["streaming"])

class PathwayBridge:
    """Bridge between Pathway and FastAPI"""
    
    def __init__(self, pathway_pipeline):
        self.pipeline = pathway_pipeline
        self.websocket_manager = WebSocketManager()
        
    async def get_live_stock_data(self, symbol: str) -> Dict[str, Any]:
        """Get current streaming data for a symbol"""
        result = self.pipeline.stock_table.filter(
            self.pipeline.stock_table.symbol == symbol
        ).select(
            symbol=self.pipeline.stock_table.symbol,
            price=self.pipeline.stock_table.price,
            volume=self.pipeline.stock_table.volume,
            change_percent=self.pipeline.stock_table.change_percent,
            timestamp=self.pipeline.stock_table.timestamp
        )
        
        # Convert Pathway table to dict
        return self._pathway_to_dict(result)
    
    async def get_indicators(self, symbol: str) -> Dict[str, Any]:
        """Get computed technical indicators"""
        indicators = {}
        
        # Get RSI
        rsi_result = self.pipeline.rsi_table.filter(
            self.pipeline.rsi_table.symbol == symbol
        )
        indicators['rsi'] = self._pathway_to_dict(rsi_result)
        
        # Get Bollinger Bands
        bb_result = self.pipeline.bollinger_table.filter(
            self.pipeline.bollinger_table.symbol == symbol
        )
        indicators['bollinger_bands'] = self._pathway_to_dict(bb_result)
        
        return indicators

@router.get("/stocks/{symbol}/live")
async def get_live_stock(symbol: str):
    """Get current streaming data for a stock"""
    data = await pathway_bridge.get_live_stock_data(symbol.upper())
    if not data:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return data

@router.get("/indicators/{symbol}")
async def get_indicators(symbol: str):
    """Get technical indicators for a stock"""
    indicators = await pathway_bridge.get_indicators(symbol.upper())
    return indicators

@router.websocket("/ws/streaming/stocks")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Receive subscription requests
            data = await websocket.receive_json()
            symbols = data.get('symbols', [])
            
            # Subscribe to updates
            for symbol in symbols:
                await websocket_manager.subscribe(websocket, symbol)
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)

class WebSocketManager:
    """Manage WebSocket connections and subscriptions"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscriptions: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        # Clean up subscriptions
        for symbol in list(self.subscriptions.keys()):
            if websocket in self.subscriptions[symbol]:
                self.subscriptions[symbol].remove(websocket)
                
    async def subscribe(self, websocket: WebSocket, symbol: str):
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []
        self.subscriptions[symbol].append(websocket)
        
    async def broadcast_update(self, symbol: str, data: Dict):
        """Broadcast update to all subscribers"""
        if symbol in self.subscriptions:
            for websocket in self.subscriptions[symbol]:
                try:
                    await websocket.send_json(data)
                except:
                    # Handle disconnected clients
                    self.disconnect(websocket)
```

**Interface**:
- Input: HTTP requests, WebSocket connections
- Output: JSON responses, WebSocket messages
- Configuration: CORS settings, rate limiting, authentication


### 7. Pathway Pipeline Orchestrator

**Purpose**: Initialize and coordinate all Pathway components.

**Implementation**:
```python
# QuantPulse-Backend/app/services/pathway_pipeline.py

import pathway as pw
from typing import List
import os

class PathwayPipeline:
    """Main Pathway streaming pipeline orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mode = config.get('mode', 'demo')  # live, demo, hybrid
        
        # Initialize components
        self.stock_connector = None
        self.stock_table = None
        self.indicators_service = None
        self.document_store = None
        self.rag_engine = None
        self.anomaly_detector = None
        
    def initialize(self):
        """Initialize the complete pipeline"""
        
        # 1. Set up data ingestion
        self._setup_ingestion()
        
        # 2. Set up transformations
        self._setup_transformations()
        
        # 3. Set up document store and RAG
        self._setup_rag()
        
        # 4. Set up anomaly detection
        self._setup_anomaly_detection()
        
        # 5. Set up outputs
        self._setup_outputs()
        
    def _setup_ingestion(self):
        """Initialize data connectors"""
        symbols = self.config.get('symbols', ['RELIANCE.NS', 'TCS.NS', 'INFY.NS'])
        
        if self.mode == 'live':
            self.stock_connector = StockDataConnector(
                symbols=symbols,
                api_key=os.getenv('STOCK_API_KEY'),
                provider=self.config.get('provider', 'twelvedata')
            )
            self.stock_table = self.stock_connector.create_input_table()
            
        elif self.mode == 'demo':
            # Use Pathway demo module for simulated data
            self.stock_table = self._create_demo_table(symbols)
            
    def _setup_transformations(self):
        """Initialize technical indicators"""
        self.indicators_service = TechnicalIndicatorsService(self.stock_table)
        
        # Compute all indicators
        self.rsi_table = self.indicators_service.compute_rsi(period=14)
        self.ma_20_table = self.indicators_service.compute_moving_average(period=20)
        self.ma_50_table = self.indicators_service.compute_moving_average(period=50)
        self.bollinger_table = self.indicators_service.compute_bollinger_bands()
        
    def _setup_rag(self):
        """Initialize document store and RAG engine"""
        document_sources = self.config.get('document_sources', ['./data/news/', './data/reports/'])
        
        self.document_store = PathwayDocumentStore(
            embedding_model=self.config.get('embedding_model', 'openai')
        )
        
        embedded_docs = self.document_store.create_document_pipeline(document_sources)
        self.document_store.create_vector_store(embedded_docs)
        
        self.rag_engine = PathwayRAGEngine(
            document_store=self.document_store,
            stock_table=self.stock_table,
            llm_provider=self.config.get('llm_provider', 'openai')
        )
        
    def _setup_anomaly_detection(self):
        """Initialize anomaly detection"""
        self.anomaly_detector = PathwayAnomalyDetector(
            stock_table=self.stock_table,
            indicators_table=self.rsi_table
        )
        
        self.price_anomalies = self.anomaly_detector.detect_price_spikes(threshold_percent=5.0)
        self.volume_anomalies = self.anomaly_detector.detect_volume_spikes(multiplier=3.0)
        
    def _setup_outputs(self):
        """Set up output sinks"""
        # Output streaming tables to REST API
        pw.io.subscribe(self.stock_table, self._on_stock_update)
        pw.io.subscribe(self.price_anomalies, self._on_anomaly_detected)
        
    def _on_stock_update(self, key, row, time, is_addition):
        """Callback for stock data updates"""
        # Notify WebSocket subscribers
        pass
        
    def _on_anomaly_detected(self, key, row, time, is_addition):
        """Callback for anomaly alerts"""
        # Generate LLM explanation and broadcast
        pass
        
    def run(self):
        """Start the pipeline"""
        pw.run()
```

**Interface**:
- Input: Configuration dict with mode, symbols, API keys
- Output: Running Pathway pipeline with all components
- Configuration: Mode selection, component parameters


## Data Models

### Stock Data Model

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class StockData(BaseModel):
    """Real-time stock data point"""
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE.NS)")
    price: float = Field(..., gt=0, description="Current price")
    volume: int = Field(..., ge=0, description="Trading volume")
    change_percent: float = Field(..., description="Percentage change")
    timestamp: int = Field(..., description="Unix timestamp")
    
class TechnicalIndicators(BaseModel):
    """Computed technical indicators"""
    symbol: str
    rsi: Optional[float] = Field(None, ge=0, le=100, description="RSI value")
    ma_20: Optional[float] = Field(None, description="20-period moving average")
    ma_50: Optional[float] = Field(None, description="50-period moving average")
    ma_200: Optional[float] = Field(None, description="200-period moving average")
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    timestamp: int
```

### Anomaly Model

```python
class AnomalyAlert(BaseModel):
    """Market anomaly alert"""
    symbol: str
    anomaly_type: str = Field(..., description="Type: price_spike, volume_spike, volatility_change")
    severity: str = Field(..., description="Severity: low, medium, high")
    value: float = Field(..., description="Anomaly magnitude")
    timestamp: int
    explanation: Optional[str] = Field(None, description="LLM-generated explanation")
    citations: Optional[List[Dict]] = Field(None, description="Source citations")
```

### RAG Query Model

```python
class RAGQuery(BaseModel):
    """Natural language query request"""
    question: str = Field(..., min_length=1, max_length=500)
    symbols: Optional[List[str]] = Field(None, description="Specific stocks to focus on")
    include_news: bool = Field(True, description="Include news context")
    include_market_data: bool = Field(True, description="Include live market data")
    
class RAGResponse(BaseModel):
    """RAG query response"""
    answer: str
    citations: List[Dict]
    stock_data: Optional[List[StockData]] = None
    timestamp: int
    processing_time_ms: int
```

### Configuration Model

```python
class PipelineConfig(BaseModel):
    """Pathway pipeline configuration"""
    mode: str = Field("demo", description="Mode: live, demo, hybrid")
    symbols: List[str] = Field(default_factory=lambda: ['RELIANCE.NS', 'TCS.NS', 'INFY.NS'])
    provider: str = Field("twelvedata", description="Stock data provider")
    poll_interval: int = Field(5, ge=1, le=60, description="Polling interval in seconds")
    document_sources: List[str] = Field(default_factory=list)
    embedding_model: str = Field("openai")
    llm_provider: str = Field("openai")
    anomaly_thresholds: Dict[str, float] = Field(default_factory=dict)
```

### Pathway Table Schemas

```python
# Stock data streaming table
stock_schema = {
    'symbol': str,
    'price': float,
    'volume': int,
    'timestamp': int,
    'change_percent': float
}

# Technical indicators table
indicators_schema = {
    'symbol': str,
    'rsi': float,
    'ma': float,
    'timestamp': int
}

# Document chunks table
document_schema = {
    'text': str,
    'embedding': list,  # Vector embedding
    'metadata': dict,   # Source, timestamp, etc.
    'doc_id': str
}

# Anomaly alerts table
anomaly_schema = {
    'symbol': str,
    'anomaly_type': str,
    'severity': str,
    'value': float,
    'timestamp': int
}
```


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.


### Property Reflection

After analyzing all acceptance criteria, I've identified the following consolidations to eliminate redundancy:

**Consolidated Properties:**
- Properties 1.1, 1.4, and 2.5 all test latency/timing - can be combined into comprehensive latency property
- Properties 2.1-2.4 all test technical indicator calculations - each is unique and valuable
- Properties 3.1 and 3.2 both test document indexing - can be combined into multi-format indexing property
- Properties 5.1, 5.2, 5.3 test different anomaly types - each is unique and should remain separate
- Properties 6.1-6.5 are all API endpoint examples - will be tested as examples, not properties
- Properties 7.2, 7.4, 7.7 test WebSocket behavior - can be combined into comprehensive WebSocket property
- Properties 9.1 and 9.2 test retry logic - can be combined into single retry property

**Properties to Keep Separate:**
- Each technical indicator (RSI, MACD, Bollinger, MA) has unique calculation logic - keep separate
- Each anomaly type (price, volume, volatility) has different detection logic - keep separate
- Document indexing, retrieval, and RAG query properties are distinct workflows - keep separate
- Error handling properties for different components test different failure modes - keep separate

### Core Properties

**Property 1: Data Ingestion Completeness**
*For any* configured list of stock symbols, when the Pathway connector fetches data, all symbols should appear in the streaming table within the configured poll interval (or be logged as errors if API fails).
**Validates: Requirements 1.1, 1.3, 1.6**

**Property 2: Fallback Mode Activation**
*For any* API failure scenario, when live data becomes unavailable, the system should automatically switch to demo mode and continue producing streaming data without pipeline failure.
**Validates: Requirements 1.2**

**Property 3: Data Retention Window**
*For any* streaming data point, if its timestamp is older than 24 hours, it should not be returned in query results, and data within the last 24 hours should be accessible.
**Validates: Requirements 1.7**

**Property 4: RSI Calculation Correctness**
*For any* sequence of price data with at least 14 periods, the computed RSI value should match the standard RSI formula: RSI = 100 - (100 / (1 + (avg_gain / avg_loss))).
**Validates: Requirements 2.1**

**Property 5: Moving Average Calculation Correctness**
*For any* price sequence and period N, the computed moving average should equal the arithmetic mean of the last N prices.
**Validates: Requirements 2.4**

**Property 6: Bollinger Bands Calculation Correctness**
*For any* price sequence with at least 20 periods, the Bollinger Bands should satisfy: upper_band = MA + (2 * stddev), middle_band = MA, lower_band = MA - (2 * stddev).
**Validates: Requirements 2.3**

**Property 7: MACD Calculation Correctness**
*For any* price sequence with sufficient data, MACD should equal the difference between 12-period EMA and 26-period EMA.
**Validates: Requirements 2.2**

**Property 8: Indicator Update Latency**
*For any* new price data point, all technical indicators (RSI, MA, Bollinger, MACD) should be updated and available within 1 second of the price data appearing in the streaming table.
**Validates: Requirements 2.5**

**Property 9: Multi-Format Document Indexing**
*For any* document in supported formats (PDF, TXT, HTML), when added to monitored directories, the document should be parsed, chunked, embedded, and searchable within 30 seconds.
**Validates: Requirements 3.1, 3.2, 3.3**

**Property 10: Incremental Index Updates**
*For any* new document added after initial indexing, the document should become searchable without requiring reindexing of existing documents.
**Validates: Requirements 3.5**

**Property 11: Metadata Extraction Completeness**
*For any* indexed document, the document's metadata should include timestamp, source path, and any stock symbols mentioned in the text.
**Validates: Requirements 3.6**

**Property 12: Query Filtering Correctness**
*For any* search query with filters (date range, symbol, document type), all returned results should satisfy the filter criteria.
**Validates: Requirements 3.7**

**Property 13: Retrieval Result Count**
*For any* search query, the number of returned document chunks should be at most 5 (or fewer if less than 5 relevant documents exist).
**Validates: Requirements 3.8**

**Property 14: Hybrid Search Contribution**
*For any* search query, the results should include documents matching both semantic similarity (embeddings) and keyword relevance (BM25), demonstrating both retrieval methods contribute.
**Validates: Requirements 3.4**

**Property 15: RAG Context Assembly**
*For any* natural language query, the RAG engine should retrieve relevant documents from the Document Store AND include current streaming data if stock symbols are mentioned.
**Validates: Requirements 4.1, 4.4**

**Property 16: Citation Generation**
*For any* RAG response, the response should include citations with source document references and timestamps for all retrieved context used.
**Validates: Requirements 4.3**

**Property 17: RAG Response Latency**
*For any* batch of 100 RAG queries, at least 95 queries should receive responses within 5 seconds.
**Validates: Requirements 4.7**

**Property 18: Conversation Context Preservation**
*For any* follow-up question in a session, the RAG engine should have access to previous questions and answers in that session.
**Validates: Requirements 4.8**

**Property 19: Price Spike Detection**
*For any* 5-minute window of price data, if the price change exceeds 5%, an anomaly alert should be generated with type "price_spike" and appropriate severity.
**Validates: Requirements 5.1**

**Property 20: Volume Spike Detection**
*For any* current volume that exceeds 3x the 20-period average volume, an anomaly alert should be generated with type "volume_spike".
**Validates: Requirements 5.2**

**Property 21: Volatility Anomaly Detection**
*For any* price sequence where standard deviation exceeds 2x the 50-period average standard deviation, an anomaly alert should be generated with type "volatility_change".
**Validates: Requirements 5.3**

**Property 22: Anomaly Alert Latency**
*For any* detected anomaly, an alert event should be generated and available within 2 seconds of detection.
**Validates: Requirements 5.4**

**Property 23: Anomaly Explanation Generation**
*For any* anomaly alert, an LLM-generated explanation should be created that includes relevant market data and news context.
**Validates: Requirements 5.5**

**Property 24: Alert Deduplication**
*For any* anomaly of the same type and symbol, if an alert was generated within the last 15 minutes, no duplicate alert should be generated.
**Validates: Requirements 5.6**

**Property 25: Severity Classification**
*For any* price spike anomaly, severity should be "high" if change > 10%, "medium" if change > 7%, "low" otherwise.
**Validates: Requirements 5.7**

**Property 26: API Response Data Completeness**
*For any* streaming data API request, the response should include all required fields: symbol, price, volume, change_percent, timestamp, and metadata.
**Validates: Requirements 6.6**

**Property 27: Input Validation**
*For any* API request with invalid data (wrong types, missing required fields, out-of-range values), the API should return 400 status with descriptive error message.
**Validates: Requirements 6.7**

**Property 28: HTTP Status Code Correctness**
*For any* API request, the response status code should be: 200 for success, 400 for invalid input, 404 for not found, 500 for server errors.
**Validates: Requirements 6.8**

**Property 29: WebSocket Update Broadcasting**
*For any* stock symbol subscription via WebSocket, when the Pathway table for that symbol updates, all subscribed clients should receive the update within 1 second.
**Validates: Requirements 7.2, 7.4**

**Property 30: WebSocket Concurrent Connections**
*For any* number of WebSocket clients up to 100, all clients should successfully connect and receive updates for their subscribed symbols.
**Validates: Requirements 7.3**

**Property 31: WebSocket Heartbeat Timing**
*For any* active WebSocket connection, heartbeat messages should be sent every 30 seconds (±2 seconds tolerance).
**Validates: Requirements 7.5**

**Property 32: WebSocket Cleanup on Disconnect**
*For any* WebSocket connection that disconnects, all associated subscriptions should be removed and resources cleaned up.
**Validates: Requirements 7.6**

**Property 33: Multi-Symbol WebSocket Subscription**
*For any* WebSocket client subscribed to multiple symbols, the client should receive updates for all subscribed symbols on the same connection.
**Validates: Requirements 7.7**

**Property 34: WebSocket Message Schema Versioning**
*For any* WebSocket message sent to clients, the message should include a schema_version field for backward compatibility.
**Validates: Requirements 7.8**

**Property 35: Mode-Specific Behavior**
*For any* pipeline configuration mode (live, demo, hybrid), the pipeline should operate according to that mode's specifications: live uses real APIs, demo uses simulated data, hybrid falls back on errors.
**Validates: Requirements 8.2**

**Property 36: Graceful Shutdown**
*For any* in-flight requests when shutdown is triggered, all requests should complete before the pipeline terminates.
**Validates: Requirements 8.6**

**Property 37: Retry with Exponential Backoff**
*For any* failed API call, the connector should retry up to 3 times with exponentially increasing delays (e.g., 1s, 2s, 4s), and if all retries fail, log the error and continue with other symbols.
**Validates: Requirements 9.1, 9.2**

**Property 38: Document Indexing Error Recovery**
*For any* document that causes an indexing error, the error should be logged, the document should be skipped, and indexing should continue for other documents.
**Validates: Requirements 9.3**

**Property 39: LLM Fallback Response**
*For any* RAG query when the LLM API is unavailable, the system should return a fallback response indicating the service is temporarily unavailable.
**Validates: Requirements 9.4**

**Property 40: Circuit Breaker Behavior**
*For any* external API that fails repeatedly, after a threshold of failures, the circuit breaker should open and prevent further calls for 5 minutes, then allow a test call.
**Validates: Requirements 9.5**

**Property 41: State Persistence Interval**
*For any* 5-minute period of pipeline operation, critical state should be persisted to disk at least once.
**Validates: Requirements 9.7**

**Property 42: Multi-Symbol Processing Latency**
*For any* configuration with up to 50 stock symbols, the pipeline should process updates for all symbols with sub-second latency per symbol.
**Validates: Requirements 10.1**

**Property 43: Document Indexing Throughput**
*For any* 1-minute period, the Document Store should successfully index at least 1000 documents without performance degradation.
**Validates: Requirements 10.2**

**Property 44: Vector Search Latency**
*For any* batch of 100 vector search queries, at least 95 queries should complete within 200ms.
**Validates: Requirements 10.3**

**Property 45: Incremental Computation Efficiency**
*For any* data update, only the affected computations should be reprocessed, not the entire dataset.
**Validates: Requirements 10.4**

**Property 46: Backpressure Handling**
*For any* scenario where data ingestion rate exceeds processing capacity, the pipeline should apply backpressure (queue or throttle) without dropping data or crashing.
**Validates: Requirements 10.5**


## Error Handling

### Error Categories and Strategies

**1. External API Failures**
- Strategy: Retry with exponential backoff (3 attempts)
- Fallback: Switch to demo mode or skip symbol
- Circuit breaker: Open after 5 consecutive failures, 5-minute cooldown
- Logging: Log all API errors with timestamp, symbol, error message

**2. Document Parsing Errors**
- Strategy: Skip problematic document, continue with others
- Logging: Log document path, error type, stack trace
- Monitoring: Track parsing error rate
- Recovery: Manual review of failed documents

**3. LLM API Errors**
- Strategy: Return fallback response to user
- Fallback message: "I'm temporarily unable to process your question. Please try again in a moment."
- Retry: Single retry after 2-second delay
- Circuit breaker: Open after 10 failures in 1 minute

**4. WebSocket Connection Errors**
- Strategy: Clean up subscriptions, log disconnection
- Client handling: Clients should implement reconnection logic
- Server handling: Remove from active connections list
- Resource cleanup: Release memory, close file handles

**5. Memory Pressure**
- Strategy: Trigger garbage collection at 80% memory usage
- Monitoring: Log memory warnings
- Backpressure: Slow down ingestion if memory critical
- Alerting: Send alerts if memory stays high for 5+ minutes

**6. Data Validation Errors**
- Strategy: Reject invalid requests with 400 status
- Response: Include specific validation error messages
- Logging: Log validation failures for monitoring
- Examples: Missing required fields, wrong data types, out-of-range values

### Error Response Formats

**REST API Errors:**
```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "Stock symbol 'XYZ' not found in configured symbols",
    "details": {
      "symbol": "XYZ",
      "available_symbols": ["RELIANCE.NS", "TCS.NS", ...]
    },
    "timestamp": 1234567890
  }
}
```

**WebSocket Errors:**
```json
{
  "type": "error",
  "error_code": "SUBSCRIPTION_FAILED",
  "message": "Failed to subscribe to symbol INVALID",
  "timestamp": 1234567890
}
```

### Logging Strategy

**Log Levels:**
- ERROR: API failures, parsing errors, LLM errors, crashes
- WARN: Memory pressure, slow queries, retry attempts
- INFO: Pipeline startup, mode changes, configuration
- DEBUG: Individual data updates, detailed processing steps

**Structured Logging Format:**
```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "component": "StockDataConnector",
  "message": "API call failed for symbol RELIANCE.NS",
  "context": {
    "symbol": "RELIANCE.NS",
    "provider": "twelvedata",
    "error": "Rate limit exceeded",
    "retry_attempt": 2
  }
}
```


## Testing Strategy

### Dual Testing Approach

This system requires both unit tests and property-based tests for comprehensive coverage:

**Unit Tests** focus on:
- Specific API endpoint examples (GET /api/v1/streaming/stocks/RELIANCE.NS/live)
- Edge cases (insufficient data for indicators, empty query results)
- Error conditions (invalid input, API failures, malformed documents)
- Integration points (FastAPI ↔ Pathway, WebSocket connections)
- Configuration loading and validation

**Property-Based Tests** focus on:
- Universal correctness properties across all inputs
- Technical indicator calculations with generated price sequences
- Document indexing and retrieval with generated documents
- Anomaly detection with generated market data patterns
- WebSocket behavior with generated client connections
- Error handling with generated failure scenarios

Both approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across the input space.

### Property-Based Testing Configuration

**Framework**: Use `hypothesis` for Python property-based testing

**Test Configuration:**
- Minimum 100 iterations per property test (due to randomization)
- Seed for reproducibility: Use fixed seed in CI, random in development
- Shrinking: Enable automatic test case minimization on failure
- Timeout: 60 seconds per property test

**Test Tagging Format:**
Each property test must include a comment referencing the design property:
```python
# Feature: pathway-realtime-rag-integration, Property 4: RSI Calculation Correctness
@given(price_sequence=st.lists(st.floats(min_value=1.0, max_value=1000.0), min_size=15, max_size=100))
def test_rsi_calculation_correctness(price_sequence):
    """For any sequence of price data with at least 14 periods, 
    the computed RSI should match the standard RSI formula"""
    # Test implementation
```

### Test Organization

**Directory Structure:**
```
tests/
├── unit/
│   ├── test_api_endpoints.py          # REST API endpoint tests
│   ├── test_websocket.py              # WebSocket connection tests
│   ├── test_configuration.py          # Config loading tests
│   └── test_error_handling.py         # Error scenario tests
├── property/
│   ├── test_technical_indicators.py   # Properties 4-8
│   ├── test_document_store.py         # Properties 9-14
│   ├── test_rag_engine.py             # Properties 15-18
│   ├── test_anomaly_detection.py      # Properties 19-25
│   └── test_streaming_pipeline.py     # Properties 1-3, 42-46
├── integration/
│   ├── test_end_to_end.py             # Full pipeline tests
│   └── test_pathway_fastapi.py        # Pathway ↔ FastAPI integration
└── load/
    └── test_performance.py            # Load and performance tests
```

### Key Property Test Examples

**Technical Indicators:**
```python
# Feature: pathway-realtime-rag-integration, Property 5: Moving Average Calculation Correctness
@given(
    prices=st.lists(st.floats(min_value=1.0, max_value=1000.0), min_size=20, max_size=100),
    period=st.integers(min_value=5, max_value=50)
)
def test_moving_average_correctness(prices, period):
    """For any price sequence and period N, MA should equal arithmetic mean of last N prices"""
    assume(len(prices) >= period)
    
    # Compute MA using Pathway
    pathway_ma = compute_moving_average(prices, period)
    
    # Compute expected MA
    expected_ma = sum(prices[-period:]) / period
    
    assert abs(pathway_ma - expected_ma) < 0.01  # Allow small floating point error
```

**Document Indexing:**
```python
# Feature: pathway-realtime-rag-integration, Property 9: Multi-Format Document Indexing
@given(
    documents=st.lists(
        st.tuples(
            st.text(min_size=100, max_size=1000),  # Document content
            st.sampled_from(['pdf', 'txt', 'html'])  # Format
        ),
        min_size=1,
        max_size=10
    )
)
def test_multi_format_indexing(documents):
    """For any documents in supported formats, all should be indexed within 30 seconds"""
    start_time = time.time()
    
    # Add documents to monitored directory
    doc_ids = add_documents_to_store(documents)
    
    # Wait for indexing
    time.sleep(30)
    
    # Verify all documents are searchable
    for doc_id in doc_ids:
        assert is_document_searchable(doc_id)
    
    assert time.time() - start_time <= 30
```

**Anomaly Detection:**
```python
# Feature: pathway-realtime-rag-integration, Property 19: Price Spike Detection
@given(
    base_price=st.floats(min_value=100.0, max_value=1000.0),
    spike_percent=st.floats(min_value=5.1, max_value=20.0),
    direction=st.sampled_from(['up', 'down'])
)
def test_price_spike_detection(base_price, spike_percent, direction):
    """For any 5-minute window with price change > 5%, anomaly should be detected"""
    # Generate price sequence with spike
    prices = generate_price_spike(base_price, spike_percent, direction)
    
    # Run anomaly detection
    anomalies = detect_anomalies(prices)
    
    # Verify spike was detected
    assert len(anomalies) > 0
    assert anomalies[0]['anomaly_type'] == 'price_spike'
    assert abs(anomalies[0]['change_percent']) >= 5.0
```

### Integration Testing

**End-to-End Flow:**
1. Start Pathway pipeline in demo mode
2. Verify streaming data appears in tables
3. Verify technical indicators are computed
4. Add test documents to monitored directory
5. Verify documents are indexed
6. Submit RAG query via API
7. Verify response includes citations and data
8. Trigger anomaly condition
9. Verify anomaly alert is generated
10. Verify WebSocket clients receive alert

**Mocking Strategy:**
- Mock external APIs (TwelveData, Finnhub) for deterministic tests
- Mock LLM API for RAG tests (use fixed responses)
- Use Pathway demo module for streaming data tests
- Use in-memory document store for fast tests

### Performance Testing

**Load Test Scenarios:**
1. 50 concurrent stock symbols streaming at 5-second intervals
2. 100 concurrent WebSocket clients receiving updates
3. 1000 documents indexed per minute
4. 100 RAG queries per minute
5. Mixed load: All above scenarios simultaneously

**Performance Metrics:**
- Data ingestion latency: < 2 seconds (p95)
- Indicator computation latency: < 1 second (p95)
- Document indexing latency: < 30 seconds (p95)
- Vector search latency: < 200ms (p95)
- RAG query latency: < 5 seconds (p95)
- WebSocket broadcast latency: < 1 second (p95)

**Performance Test Tools:**
- `locust` for load testing REST APIs
- Custom WebSocket load generator
- `pytest-benchmark` for micro-benchmarks
- Prometheus + Grafana for monitoring

### Continuous Integration

**CI Pipeline:**
1. Lint and format check (black, flake8, mypy)
2. Unit tests (fast, no external dependencies)
3. Property tests (100 iterations, fixed seed)
4. Integration tests (with mocked external services)
5. Load tests (reduced scale for CI)
6. Coverage report (minimum 80% for core logic)

**Test Execution Time Targets:**
- Unit tests: < 2 minutes
- Property tests: < 10 minutes
- Integration tests: < 5 minutes
- Load tests: < 15 minutes
- Total CI time: < 30 minutes
