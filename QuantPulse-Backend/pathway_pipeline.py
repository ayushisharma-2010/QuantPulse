"""
Pathway Real-Time Streaming Pipeline for QuantPulse
====================================================

This module implements the core Pathway streaming pipeline that:
1. Ingests live stock data from yfinance via Pathway ConnectorSubject
2. Streams data into pw.Table for real-time processing
3. Computes technical indicators as streaming transformations
4. Indexes news and ESG documents for RAG queries
5. Exposes REST API endpoints on port 8090

Architecture (Linux/WSL with Pathway):
    StockDataSubject (ConnectorSubject)
        -> pw.io.python.read() -> pw.Table (stock_table)
        -> pw.apply() transformations (RSI, MACD, Bollinger Bands)
        -> pw.io.python.write() -> in-memory cache
        -> FastAPI REST API serves from cache
        -> pw.run() drives the streaming engine

Fallback (Windows without Pathway):
    Vanilla FastAPI + on-demand yfinance fetch (no streaming)

Usage:
    python pathway_pipeline.py

Environment Variables:
    PATHWAY_PORT: REST API port (default: 8090)
    GROQ_API_KEY: Groq API key for RAG LLM
    PATHWAY_MODE: 'live' or 'demo' (default: live)
    PATHWAY_POLL_INTERVAL: Stock polling interval in seconds (default: 60)
"""

import os
import sys
import logging
import threading
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import glob

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if Pathway is installed
try:
    import pathway as pw
    PATHWAY_AVAILABLE = True
    logger.info("✅ Pathway is available — using real streaming engine")
except (ImportError, AttributeError) as e:
    PATHWAY_AVAILABLE = False
    logger.warning("⚠️ Pathway is not available. Running in standalone/fallback mode.")
    logger.warning("For full Pathway streaming, run on Linux/WSL.")

# Import other dependencies
try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError as e:
    logger.error(f"Missing dependency: {e}")
    sys.exit(1)


# ============================================================================
# Configuration
# ============================================================================

class PipelineConfig:
    """Configuration for Pathway pipeline"""
    
    # Server configuration
    PORT = int(os.getenv('PATHWAY_PORT', 8090))
    HOST = os.getenv('PATHWAY_HOST', '0.0.0.0')
    
    # Pipeline mode — default to 'live' for real yfinance data
    MODE = os.getenv('PATHWAY_MODE', 'live')
    
    # Stock configuration
    POLL_INTERVAL = int(os.getenv('PATHWAY_POLL_INTERVAL', 60))  # seconds
    WATCHLIST = [
        'RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS',
        'ICICIBANK.NS', 'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS',
        'BHARTIARTL.NS', 'KOTAKBANK.NS'
    ]
    
    # Document paths
    NEWS_DIR = os.path.join(os.path.dirname(__file__), 'pathway_data', 'news')
    ESG_DIR = os.path.join(os.path.dirname(__file__), 'pathway_data', 'esg')
    
    # LLM configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'text-embedding-ada-002')
    LLM_MODEL = os.getenv('LLM_MODEL', 'gpt-4')
    
    # Feature engineering parameters
    RSI_PERIOD = 14
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    BB_PERIOD = 20
    BB_STD = 2.0


# ============================================================================
# Pydantic Models for API
# ============================================================================

class StockDataResponse(BaseModel):
    """Response model for stock data"""
    symbol: str
    price: float
    volume: int
    change_percent: float
    timestamp: str
    indicators: Optional[Dict[str, Any]] = None


class RAGQueryRequest(BaseModel):
    """Request model for RAG queries"""
    query: str
    symbols: Optional[List[str]] = None
    include_news: bool = True
    include_esg: bool = True


class RAGQueryResponse(BaseModel):
    """Response model for RAG queries"""
    answer: str
    citations: List[Dict[str, Any]]
    stock_data: Optional[List[Dict[str, Any]]] = None
    timestamp: str


class GreenScoreResponse(BaseModel):
    """Response model for green/ESG score"""
    symbol: str
    score: float
    category: str  # 'high', 'medium', 'low'
    breakdown: Dict[str, float]
    timestamp: str


class StatusResponse(BaseModel):
    """Response model for pipeline status"""
    status: str
    mode: str
    pathway_active: bool
    uptime_seconds: float
    stocks_tracked: int
    documents_indexed: int
    last_update: str
    updates_count: int


# ============================================================================
# Technical Indicators Calculator
# ============================================================================

class TechnicalIndicators:
    """Calculate technical indicators for stock data"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index (RSI)"""
        if len(prices) < period + 1:
            return None
        
        deltas = np.diff(prices[-period-1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi)
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average (SMA)"""
        if len(prices) < period:
            return None
        return float(np.mean(prices[-period:]))
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average (EMA)"""
        if len(prices) < period:
            return None
        
        prices_array = np.array(prices[-period:])
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        
        ema = np.convolve(prices_array, weights, mode='valid')[-1]
        return float(ema)
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, float]]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < slow + signal:
            return None
        
        fast_ema = TechnicalIndicators.calculate_ema(prices, fast)
        slow_ema = TechnicalIndicators.calculate_ema(prices, slow)
        
        if fast_ema is None or slow_ema is None:
            return None
        
        macd_line = fast_ema - slow_ema
        signal_line = macd_line
        histogram = macd_line - signal_line
        
        return {
            'macd': float(macd_line),
            'signal': float(signal_line),
            'histogram': float(histogram)
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None
        
        recent_prices = prices[-period:]
        middle_band = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)
        
        current_price = prices[-1]
        if upper_band != lower_band:
            percent_b = (current_price - lower_band) / (upper_band - lower_band)
        else:
            percent_b = 0.5
        
        return {
            'upper': float(upper_band),
            'middle': float(middle_band),
            'lower': float(lower_band),
            'percent_b': float(percent_b)
        }
    
    @staticmethod
    def calculate_volatility(prices: List[float], period: int = 20) -> Optional[float]:
        """Calculate price volatility (annualized standard deviation)"""
        if len(prices) < period:
            return None
        
        recent_prices = prices[-period:]
        returns = np.diff(recent_prices) / recent_prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)
        return float(volatility)


class StockDataAggregator:
    """Aggregate and maintain historical stock data for indicator calculation"""
    
    def __init__(self, max_history: int = 200):
        self.max_history = max_history
        self.price_history = {}
        self.volume_history = {}
        self.timestamp_history = {}
        logger.info(f"StockDataAggregator initialized with max_history={max_history}")
    
    def add_data_point(self, symbol: str, price: float, volume: int, timestamp: str):
        """Add a new data point for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []
            self.timestamp_history[symbol] = []
        
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
        self.timestamp_history[symbol].append(timestamp)
        
        if len(self.price_history[symbol]) > self.max_history:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history:]
            self.volume_history[symbol] = self.volume_history[symbol][-self.max_history:]
            self.timestamp_history[symbol] = self.timestamp_history[symbol][-self.max_history:]
    
    def get_prices(self, symbol: str) -> List[float]:
        return self.price_history.get(symbol, [])
    
    def calculate_all_indicators(self, symbol: str) -> Dict[str, Any]:
        """Calculate all technical indicators for a symbol"""
        prices = self.get_prices(symbol)
        if not prices:
            return {}
        
        indicators = {
            'rsi_14': TechnicalIndicators.calculate_rsi(prices, 14),
            'sma_20': TechnicalIndicators.calculate_sma(prices, 20),
            'sma_50': TechnicalIndicators.calculate_sma(prices, 50),
            'sma_200': TechnicalIndicators.calculate_sma(prices, 200),
            'ema_12': TechnicalIndicators.calculate_ema(prices, 12),
            'ema_26': TechnicalIndicators.calculate_ema(prices, 26),
            'volatility': TechnicalIndicators.calculate_volatility(prices, 20)
        }
        
        macd_data = TechnicalIndicators.calculate_macd(prices)
        if macd_data:
            indicators.update({
                'macd': macd_data['macd'],
                'macd_signal': macd_data['signal'],
                'macd_histogram': macd_data['histogram']
            })
        
        bb_data = TechnicalIndicators.calculate_bollinger_bands(prices)
        if bb_data:
            indicators.update({
                'bb_upper': bb_data['upper'],
                'bb_middle': bb_data['middle'],
                'bb_lower': bb_data['lower'],
                'bb_percent_b': bb_data['percent_b']
            })
        
        return indicators


# ============================================================================
# Document Store and RAG Components
# ============================================================================

class SimpleDocumentStore:
    """Simple document store with text search"""
    
    def __init__(self, watch_dir: str, doc_type: str = "news"):
        self.watch_dir = watch_dir
        self.doc_type = doc_type
        self.documents = []
        self.last_scan_time = None
        os.makedirs(watch_dir, exist_ok=True)
        logger.info(f"DocumentStore initialized for {doc_type} at {watch_dir}")
    
    def scan_and_index(self):
        """Scan directory and index new documents"""
        try:
            json_files = glob.glob(os.path.join(self.watch_dir, "*.json"))
            new_docs = 0
            
            for file_path in json_files:
                if any(doc.get('file_path') == file_path for doc in self.documents):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        doc_data = json.load(f)
                    
                    doc_data['file_path'] = file_path
                    doc_data['indexed_at'] = datetime.now().isoformat()
                    doc_data['doc_type'] = self.doc_type
                    
                    self.documents.append(doc_data)
                    new_docs += 1
                    logger.debug(f"Indexed document: {os.path.basename(file_path)}")
                    
                except Exception as e:
                    logger.error(f"Error indexing {file_path}: {e}")
            
            if new_docs > 0:
                logger.info(f"Indexed {new_docs} new {self.doc_type} documents")
            
            self.last_scan_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error scanning directory {self.watch_dir}: {e}")
    
    def search(self, query: str, top_k: int = 5, symbol_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search documents (simple keyword matching)"""
        self.scan_and_index()
        
        query_lower = query.lower()
        query_terms = query_lower.split()
        results = []
        
        for doc in self.documents:
            symbol_matched = False
            if symbol_filter:
                doc_symbol = doc.get('symbol', '')
                doc_symbols = doc.get('symbols', [])
                if doc_symbol == symbol_filter or symbol_filter in doc_symbols:
                    symbol_matched = True
                else:
                    continue
            
            score = 0
            if symbol_matched:
                score = 10
            
            title = doc.get('title', '').lower()
            for term in query_terms:
                if term in title:
                    score += 3
            
            content = doc.get('content', '').lower()
            for term in query_terms:
                score += content.count(term)
            
            company_name = doc.get('company_name', '').lower()
            for term in query_terms:
                if term in company_name:
                    score += 2
            
            if score > 0:
                results.append({'document': doc, 'score': score})
        
        results.sort(key=lambda x: x['score'], reverse=True)
        return [r['document'] for r in results[:top_k]]
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        self.scan_and_index()
        return self.documents
    
    def get_document_count(self) -> int:
        return len(self.documents)


class SimpleRAGEngine:
    """Simple RAG engine using document store and LLM"""
    
    def __init__(self, news_store: SimpleDocumentStore, esg_store: SimpleDocumentStore, 
                 llm_provider: str = "groq", api_key: Optional[str] = None):
        self.news_store = news_store
        self.esg_store = esg_store
        self.llm_provider = llm_provider
        self.api_key = api_key
        self.llm_available = bool(api_key)
        
        if not self.llm_available:
            logger.warning("No LLM API key provided. RAG will return document excerpts only.")
        
        logger.info(f"RAG Engine initialized with {llm_provider} provider")
    
    def query(self, question: str, symbols: Optional[List[str]] = None, 
              include_news: bool = True, include_esg: bool = True) -> Dict[str, Any]:
        """Execute RAG query"""
        try:
            retrieved_docs = []
            
            if include_news:
                news_docs = self.news_store.search(
                    query=question, top_k=3,
                    symbol_filter=symbols[0] if symbols else None
                )
                retrieved_docs.extend([{'source': 'news', 'doc': doc} for doc in news_docs])
            
            if include_esg:
                esg_docs = self.esg_store.search(
                    query=question, top_k=2,
                    symbol_filter=symbols[0] if symbols else None
                )
                retrieved_docs.extend([{'source': 'esg', 'doc': doc} for doc in esg_docs])
            
            context = self._build_context(retrieved_docs)
            
            if self.llm_available:
                answer = self._generate_llm_answer(question, context, symbols)
            else:
                answer = self._generate_fallback_answer(question, retrieved_docs)
            
            citations = self._extract_citations(retrieved_docs)
            
            return {
                'answer': answer,
                'citations': citations,
                'documents_retrieved': len(retrieved_docs),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            return {
                'answer': f"I encountered an error processing your question: {str(e)}",
                'citations': [],
                'documents_retrieved': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def _build_context(self, retrieved_docs: List[Dict]) -> str:
        context_parts = []
        for item in retrieved_docs:
            doc = item['doc']
            source = item['source']
            title = doc.get('title', 'Untitled')
            content = doc.get('content', '')[:500]
            context_parts.append(f"[{source.upper()}] {title}\n{content}...")
        return "\n\n".join(context_parts)
    
    def _generate_llm_answer(self, question: str, context: str, symbols: Optional[List[str]]) -> str:
        if not context:
            return "I don't have enough information to answer that question."
        
        try:
            from groq import Groq
            client = Groq(api_key=self.api_key)
            
            prompt = f"""You are a financial analyst assistant. Answer the user's question based on the provided context.

Context:
{context}

Question: {question}

Instructions:
- Provide a clear, concise answer based on the context
- Cite specific information from the documents
- If the context doesn't contain enough information, say so
- Focus on factual information only
- Keep the response under 200 words

Answer:"""
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful financial analyst assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            symbol_text = f" regarding {', '.join(symbols)}" if symbols else ""
            return f"Based on the available documents{symbol_text}, here's what I found:\n\n{context[:300]}...\n\n(Note: LLM integration error: {str(e)})"
    
    def _generate_fallback_answer(self, question: str, retrieved_docs: List[Dict]) -> str:
        if not retrieved_docs:
            return "I couldn't find any relevant documents to answer your question."
        
        excerpts = []
        for item in retrieved_docs[:2]:
            doc = item['doc']
            title = doc.get('title', 'Untitled')
            content = doc.get('content', '')[:200]
            excerpts.append(f"• {title}: {content}...")
        
        return "Here are relevant excerpts from the documents:\n\n" + "\n\n".join(excerpts)
    
    def _extract_citations(self, retrieved_docs: List[Dict]) -> List[Dict[str, Any]]:
        citations = []
        for item in retrieved_docs:
            doc = item['doc']
            source = item['source']
            citation = {
                'title': doc.get('title', 'Untitled'),
                'source': source,
                'url': doc.get('url', ''),
                'published_date': doc.get('published_date', ''),
                'excerpt': doc.get('content', '')[:150] + "..."
            }
            citations.append(citation)
        return citations


class GreenScoreCalculator:
    """Calculate ESG/Green scores from ESG documents"""
    
    def __init__(self, esg_store: SimpleDocumentStore):
        self.esg_store = esg_store
        logger.info("GreenScoreCalculator initialized")
    
    def calculate_score(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Calculate green score for a symbol"""
        if not symbol.endswith('.NS'):
            symbol = f"{symbol}.NS"
        
        esg_docs = self.esg_store.search(query=symbol, symbol_filter=symbol, top_k=1)
        
        if not esg_docs:
            return None
        
        doc = esg_docs[0]
        
        overall_score = doc.get('overall_score', 50)
        category = doc.get('category', 'medium')
        
        env = doc.get('environmental', {})
        social = doc.get('social', {})
        gov = doc.get('governance', {})
        
        breakdown = {
            'environmental': env.get('overall', 50),
            'social': social.get('overall', 50),
            'governance': gov.get('overall', 50),
            'carbon_emissions': env.get('carbon_emissions_score', 50),
            'water_usage': env.get('water_usage_score', 50),
            'board_diversity': social.get('board_diversity_score', 50)
        }
        
        return {
            'symbol': symbol,
            'score': round(overall_score, 1),
            'category': category,
            'breakdown': breakdown,
            'company_name': doc.get('company_name', symbol),
            'report_date': doc.get('report_date', ''),
            'timestamp': datetime.now().isoformat()
        }


# ============================================================================
# Pathway Streaming Components (Linux/WSL only)
# ============================================================================

if PATHWAY_AVAILABLE:
    
    class StockSchema(pw.Schema):
        """Pathway schema for stock data streaming table"""
        symbol: str
        price: float
        volume: int
        open_price: float
        high: float
        low: float
        change_percent: float
        timestamp: str
        market_cap: int
        company_name: str
    
    
    class StockDataSubject(pw.io.python.ConnectorSubject):
        """
        Pathway ConnectorSubject that polls yfinance for live NSE stock data.
        
        This runs in a dedicated thread managed by Pathway's engine.
        Every POLL_INTERVAL seconds, it fetches fresh data for all watched
        symbols and pushes them into the Pathway streaming table via self.next().
        """
        
        deletions_enabled = False  # We only add/update, never delete
        
        def __init__(self, symbols: List[str], poll_interval: int = 60, mode: str = 'live'):
            super().__init__()
            self.symbols = symbols
            self.poll_interval = poll_interval
            self.mode = mode
            self._fetch_count = 0
            
            # Realistic base prices for demo mode
            self._demo_prices = {
                'RELIANCE.NS': 1400.0, 'TCS.NS': 2650.0,
                'INFY.NS': 1450.0, 'HDFCBANK.NS': 906.0,
                'ICICIBANK.NS': 650.0, 'HINDUNILVR.NS': 2100.0,
                'ITC.NS': 320.0, 'SBIN.NS': 380.0,
                'BHARTIARTL.NS': 900.0, 'KOTAKBANK.NS': 1550.0
            }
            self._current_demo_prices = {s: self._demo_prices.get(s, 1000.0) for s in symbols}
            
            logger.info(f"StockDataSubject initialized: {len(symbols)} symbols, "
                        f"mode={mode}, poll_interval={poll_interval}s")
        
        def run(self):
            """
            Main loop — called by Pathway engine in a separate thread.
            Continuously polls yfinance and pushes data via self.next().
            """
            logger.info("🚀 StockDataSubject.run() started — streaming data into Pathway")
            
            while True:
                try:
                    self._fetch_count += 1
                    current_time = datetime.now()
                    
                    if self.mode == 'live':
                        records = self._fetch_live_data(current_time)
                    else:
                        records = self._generate_demo_data(current_time)
                    
                    # Push each record into Pathway's streaming engine
                    for record in records:
                        self.next(
                            symbol=record['symbol'],
                            price=record['price'],
                            volume=record['volume'],
                            open_price=record['open'],
                            high=record['high'],
                            low=record['low'],
                            change_percent=record['change_percent'],
                            timestamp=record['timestamp'],
                            market_cap=record['market_cap'],
                            company_name=record['company_name']
                        )
                    
                    logger.info(f"📊 Pathway stream update #{self._fetch_count}: "
                                f"pushed {len(records)}/{len(self.symbols)} symbols")
                    
                    # Wait for next poll interval
                    time.sleep(self.poll_interval)
                    
                except Exception as e:
                    logger.error(f"Error in StockDataSubject.run(): {e}")
                    time.sleep(10)  # Back off on error
        
        def _fetch_live_data(self, current_time: datetime) -> List[Dict[str, Any]]:
            """Fetch real stock data from yfinance"""
            results = []
            
            for symbol in self.symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='5d', interval='1d')
                    
                    if hist.empty:
                        logger.warning(f"No data available for {symbol}")
                        continue
                    
                    latest = hist.iloc[-1]
                    previous = hist.iloc[-2] if len(hist) > 1 else latest
                    
                    change_percent = (
                        (latest['Close'] - previous['Close']) / previous['Close'] * 100
                    ) if previous['Close'] > 0 else 0.0
                    
                    info = ticker.info
                    
                    stock_data = {
                        'symbol': symbol,
                        'price': float(latest['Close']),
                        'volume': int(latest['Volume']),
                        'open': float(latest['Open']),
                        'high': float(latest['High']),
                        'low': float(latest['Low']),
                        'change_percent': float(change_percent),
                        'timestamp': current_time.isoformat(),
                        'market_cap': int(info.get('marketCap', 0)),
                        'company_name': info.get('longName', symbol.replace('.NS', ''))
                    }
                    
                    results.append(stock_data)
                    logger.debug(f"  {symbol}: ₹{stock_data['price']:.2f} ({change_percent:+.2f}%)")
                    
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
                    continue
            
            return results
        
        def _generate_demo_data(self, current_time: datetime) -> List[Dict[str, Any]]:
            """Generate simulated stock data for demo mode"""
            results = []
            
            for symbol in self.symbols:
                try:
                    previous_price = self._current_demo_prices[symbol]
                    change_percent = float(np.random.normal(0, 2))
                    new_price = previous_price * (1 + change_percent / 100)
                    
                    base_price = self._demo_prices.get(symbol, 1000.0)
                    new_price = max(base_price * 0.7, min(base_price * 1.3, new_price))
                    self._current_demo_prices[symbol] = new_price
                    
                    volume = int(np.random.uniform(100000, 10000000))
                    
                    results.append({
                        'symbol': symbol,
                        'price': float(new_price),
                        'volume': volume,
                        'open': float(previous_price),
                        'high': float(max(previous_price, new_price) * 1.01),
                        'low': float(min(previous_price, new_price) * 0.99),
                        'change_percent': float(change_percent),
                        'timestamp': current_time.isoformat(),
                        'market_cap': int(new_price * np.random.uniform(1e9, 1e12)),
                        'company_name': symbol.replace('.NS', '')
                    })
                    
                except Exception as e:
                    logger.error(f"Error generating demo data for {symbol}: {e}")
            
            return results
    
    
    class StockDataObserver(pw.io.python.ConnectorObserver):
        """
        Pathway ConnectorObserver that captures streaming table changes
        and updates the in-memory cache used by the REST API.
        """
        
        def __init__(self, cache: Dict[str, Dict], aggregator: StockDataAggregator):
            super().__init__()
            self._cache = cache
            self._aggregator = aggregator
            self._update_count = 0
        
        def on_change(self, key, row, time, is_addition):
            """Called by Pathway engine whenever the streaming table changes"""
            if is_addition:
                symbol = row['symbol']
                
                stock_data = {
                    'symbol': symbol,
                    'price': row['price'],
                    'volume': row['volume'],
                    'open': row['open_price'],
                    'high': row['high'],
                    'low': row['low'],
                    'change_percent': row['change_percent'],
                    'timestamp': row['timestamp'],
                    'market_cap': row['market_cap'],
                    'company_name': row['company_name']
                }
                
                # Update cache
                self._cache[symbol] = stock_data
                
                # Update aggregator for indicator calculation
                self._aggregator.add_data_point(
                    symbol=symbol,
                    price=row['price'],
                    volume=row['volume'],
                    timestamp=row['timestamp']
                )
                
                self._update_count += 1
                
                if self._update_count % 10 == 0:
                    logger.info(f"🔄 Observer: {self._update_count} streaming updates processed, "
                                f"{len(self._cache)} symbols in cache")
        
        def on_time_end(self, time):
            """Called when a processing time batch completes"""
            pass
        
        def on_end(self):
            """Called when the stream ends"""
            logger.info(f"Stream ended. Total updates: {self._update_count}")


# ============================================================================
# Pathway Pipeline Class
# ============================================================================

class PathwayPipeline:
    """Main Pathway streaming pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.start_time = datetime.now()
        self.pathway_active = PATHWAY_AVAILABLE
        
        # Pipeline components
        self.stock_connector = None
        self.news_store = None
        self.esg_store = None
        self.rag_engine = None
        self.green_score_calculator = None
        
        # Stock data aggregator for historical data & indicators
        self.stock_aggregator = StockDataAggregator(max_history=200)
        
        # In-memory cache for latest stock data (served by REST API)
        self.latest_stock_data: Dict[str, Dict] = {}
        
        # Update counter
        self._streaming_updates = 0
        
        # FastAPI app
        self.app = self._create_fastapi_app()
        
        logger.info(f"PathwayPipeline initialized: mode={config.MODE}, "
                     f"pathway_active={self.pathway_active}")
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application for REST endpoints"""
        app = FastAPI(
            title="Pathway Streaming Pipeline API",
            description="Real-time NSE stock analytics powered by Pathway streaming",
            version="2.0.0"
        )
        
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._register_routes(app)
        return app
    
    def _register_routes(self, app: FastAPI):
        """Register API routes"""
        
        @app.get("/")
        async def root():
            return {
                "service": "Pathway Streaming Pipeline",
                "version": "2.0.0",
                "status": "running",
                "mode": self.config.MODE,
                "pathway_active": self.pathway_active
            }
        
        @app.get("/v1/status", response_model=StatusResponse)
        async def get_status():
            """Get pipeline status"""
            uptime = (datetime.now() - self.start_time).total_seconds()
            doc_count = 0
            if self.news_store:
                doc_count += self.news_store.get_document_count()
            if self.esg_store:
                doc_count += self.esg_store.get_document_count()
            
            return StatusResponse(
                status="running",
                mode=self.config.MODE,
                pathway_active=self.pathway_active,
                uptime_seconds=uptime,
                stocks_tracked=len(self.latest_stock_data),
                documents_indexed=doc_count,
                last_update=datetime.now().isoformat(),
                updates_count=self._streaming_updates
            )
        
        @app.get("/v1/ticker/{symbol}", response_model=StockDataResponse)
        async def get_ticker_data(symbol: str):
            """Get latest streaming data for a stock"""
            symbol_upper = symbol.upper()
            
            # On fallback mode (Windows), fetch on-demand
            if not self.pathway_active:
                self._fallback_update_stock_data()
            
            data = self.latest_stock_data.get(symbol_upper)
            
            if not data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Stock {symbol} not found. "
                           f"Available: {list(self.latest_stock_data.keys())}"
                )
            
            indicators = self.stock_aggregator.calculate_all_indicators(symbol_upper)
            
            return StockDataResponse(
                symbol=data['symbol'],
                price=data['price'],
                volume=data['volume'],
                change_percent=data['change_percent'],
                timestamp=data['timestamp'],
                indicators=indicators if indicators else None
            )
        
        @app.get("/v1/tickers")
        async def get_all_tickers():
            """Get latest data for all tracked stocks"""
            if not self.pathway_active:
                self._fallback_update_stock_data()
            
            return {
                "stocks": list(self.latest_stock_data.values()),
                "count": len(self.latest_stock_data),
                "timestamp": datetime.now().isoformat(),
                "pathway_active": self.pathway_active
            }
        
        @app.post("/v1/rag/query", response_model=RAGQueryResponse)
        async def rag_query(request: RAGQueryRequest):
            """Execute RAG query against document store"""
            if not self.rag_engine:
                raise HTTPException(status_code=503, detail="RAG engine not initialized")
            
            result = self.rag_engine.query(
                question=request.query,
                symbols=request.symbols,
                include_news=request.include_news,
                include_esg=request.include_esg
            )
            
            return RAGQueryResponse(
                answer=result['answer'],
                citations=result['citations'],
                stock_data=None,
                timestamp=result['timestamp']
            )
        
        @app.get("/v1/green-score/{symbol}", response_model=GreenScoreResponse)
        async def get_green_score(symbol: str):
            """Get ESG/green score for a stock"""
            if not self.green_score_calculator:
                raise HTTPException(status_code=503, detail="Green score calculator not initialized")
            
            score_data = self.green_score_calculator.calculate_score(symbol.upper())
            
            if not score_data:
                raise HTTPException(status_code=404, detail=f"No ESG data for {symbol}")
            
            return GreenScoreResponse(**score_data)
    
    def _initialize_document_stores(self):
        """Initialize news and ESG document stores"""
        logger.info("Initializing document stores...")
        
        self.news_store = SimpleDocumentStore(
            watch_dir=self.config.NEWS_DIR, doc_type="news"
        )
        self.esg_store = SimpleDocumentStore(
            watch_dir=self.config.ESG_DIR, doc_type="esg"
        )
        
        self.news_store.scan_and_index()
        self.esg_store.scan_and_index()
        
        logger.info(f"Document stores: {self.news_store.get_document_count()} news, "
                     f"{self.esg_store.get_document_count()} ESG docs")
    
    def _initialize_rag_engine(self):
        """Initialize RAG engine"""
        logger.info("Initializing RAG engine...")
        
        api_key = self.config.OPENAI_API_KEY or self.config.GROQ_API_KEY
        
        self.rag_engine = SimpleRAGEngine(
            news_store=self.news_store,
            esg_store=self.esg_store,
            llm_provider='groq',
            api_key=api_key
        )
    
    def _initialize_green_score(self):
        """Initialize green score calculator"""
        self.green_score_calculator = GreenScoreCalculator(esg_store=self.esg_store)
    
    # ------------------------------------------------------------------
    # Fallback mode (Windows — no Pathway)
    # ------------------------------------------------------------------
    
    def _fallback_fetch_initial_data(self):
        """Fetch initial stock data without Pathway (fallback for Windows)"""
        logger.info("Fetching initial stock data (fallback mode)...")
        
        current_time = datetime.now()
        
        if self.config.MODE == 'live':
            for symbol in self.config.WATCHLIST:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='5d', interval='1d')
                    
                    if hist.empty:
                        continue
                    
                    latest = hist.iloc[-1]
                    previous = hist.iloc[-2] if len(hist) > 1 else latest
                    change_pct = ((latest['Close'] - previous['Close']) / previous['Close'] * 100
                                  ) if previous['Close'] > 0 else 0.0
                    
                    info = ticker.info
                    
                    self.latest_stock_data[symbol] = {
                        'symbol': symbol,
                        'price': float(latest['Close']),
                        'volume': int(latest['Volume']),
                        'open': float(latest['Open']),
                        'high': float(latest['High']),
                        'low': float(latest['Low']),
                        'change_percent': float(change_pct),
                        'timestamp': current_time.isoformat(),
                        'market_cap': int(info.get('marketCap', 0)),
                        'company_name': info.get('longName', symbol.replace('.NS', ''))
                    }
                except Exception as e:
                    logger.error(f"Error fetching {symbol}: {e}")
        else:
            # Demo mode — generate random data
            demo_prices = {
                'RELIANCE.NS': 1400.0, 'TCS.NS': 2650.0,
                'INFY.NS': 1450.0, 'HDFCBANK.NS': 906.0,
                'ICICIBANK.NS': 650.0, 'HINDUNILVR.NS': 2100.0,
                'ITC.NS': 320.0, 'SBIN.NS': 380.0,
                'BHARTIARTL.NS': 900.0, 'KOTAKBANK.NS': 1550.0
            }
            for symbol in self.config.WATCHLIST:
                base = demo_prices.get(symbol, 1000.0)
                price = base * (1 + np.random.normal(0, 0.02))
                self.latest_stock_data[symbol] = {
                    'symbol': symbol,
                    'price': float(price),
                    'volume': int(np.random.uniform(100000, 10000000)),
                    'open': float(base),
                    'high': float(price * 1.01),
                    'low': float(price * 0.99),
                    'change_percent': float((price - base) / base * 100),
                    'timestamp': current_time.isoformat(),
                    'market_cap': int(price * np.random.uniform(1e9, 1e12)),
                    'company_name': symbol.replace('.NS', '')
                }
        
        logger.info(f"Fallback: loaded {len(self.latest_stock_data)} stocks")
    
    def _fallback_update_stock_data(self):
        """Update stock data on-demand (fallback for Windows)"""
        if self.config.MODE == 'live':
            current_time = datetime.now()
            for symbol in self.config.WATCHLIST:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='5d', interval='1d')
                    if hist.empty:
                        continue
                    
                    latest = hist.iloc[-1]
                    previous = hist.iloc[-2] if len(hist) > 1 else latest
                    change_pct = ((latest['Close'] - previous['Close']) / previous['Close'] * 100
                                  ) if previous['Close'] > 0 else 0.0
                    
                    info = ticker.info
                    
                    self.latest_stock_data[symbol] = {
                        'symbol': symbol,
                        'price': float(latest['Close']),
                        'volume': int(latest['Volume']),
                        'open': float(latest['Open']),
                        'high': float(latest['High']),
                        'low': float(latest['Low']),
                        'change_percent': float(change_pct),
                        'timestamp': current_time.isoformat(),
                        'market_cap': int(info.get('marketCap', 0)),
                        'company_name': info.get('longName', symbol.replace('.NS', ''))
                    }
                    
                    self.stock_aggregator.add_data_point(
                        symbol=symbol, price=float(latest['Close']),
                        volume=int(latest['Volume']),
                        timestamp=current_time.isoformat()
                    )
                except Exception as e:
                    logger.error(f"Error updating {symbol}: {e}")
        else:
            # Demo mode — randomize prices
            current_time = datetime.now()
            for symbol, data in self.latest_stock_data.items():
                old_price = data['price']
                change = float(np.random.normal(0, 2))
                new_price = old_price * (1 + change / 100)
                data['price'] = float(new_price)
                data['change_percent'] = float(change)
                data['timestamp'] = current_time.isoformat()
                
                self.stock_aggregator.add_data_point(
                    symbol=symbol, price=float(new_price),
                    volume=data['volume'], timestamp=current_time.isoformat()
                )
    
    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------
    
    def run(self):
        """Start the pipeline"""
        logger.info("=" * 60)
        logger.info("QuantPulse Pathway Streaming Pipeline")
        logger.info("=" * 60)
        
        # Initialize shared components
        self._initialize_document_stores()
        self._initialize_rag_engine()
        self._initialize_green_score()
        
        if self.pathway_active:
            self._run_with_pathway()
        else:
            self._run_fallback()
    
    def _run_with_pathway(self):
        """Run with real Pathway streaming engine (Linux/WSL)"""
        logger.info("🚀 Starting with REAL Pathway streaming engine")
        logger.info(f"   Mode: {self.config.MODE}")
        logger.info(f"   Symbols: {len(self.config.WATCHLIST)}")
        logger.info(f"   Poll interval: {self.config.POLL_INTERVAL}s")
        
        # 1. Create the Pathway ConnectorSubject for stock data
        stock_subject = StockDataSubject(
            symbols=self.config.WATCHLIST,
            poll_interval=self.config.POLL_INTERVAL,
            mode=self.config.MODE
        )
        
        # 2. Create streaming table via pw.io.python.read()
        stock_table = pw.io.python.read(
            stock_subject,
            schema=StockSchema,
            autocommit_duration_ms=5000  # Commit every 5 seconds
        )
        
        # 3. Set up observer to capture streaming updates into cache
        observer = StockDataObserver(
            cache=self.latest_stock_data,
            aggregator=self.stock_aggregator
        )
        
        # 4. Write streaming table changes to observer
        pw.io.python.write(stock_table, observer)
        
        # 5. Start FastAPI in a background thread
        api_thread = threading.Thread(
            target=self._start_api_server,
            daemon=True,
            name="FastAPI-Server"
        )
        api_thread.start()
        logger.info(f"✅ REST API started on {self.config.HOST}:{self.config.PORT}")
        
        # 6. Run Pathway engine (blocking — this drives everything)
        logger.info("✅ Starting Pathway engine (pw.run)...")
        logger.info("   Stock data will stream automatically every "
                     f"{self.config.POLL_INTERVAL}s")
        pw.run()
    
    def _run_fallback(self):
        """Run without Pathway (Windows fallback)"""
        logger.info("⚠️ Running in FALLBACK mode (no Pathway)")
        logger.info("   Stock data updates on-demand only")
        
        # Fetch initial data
        self._fallback_fetch_initial_data()
        
        # Start API server (blocking)
        logger.info(f"Starting REST API on {self.config.HOST}:{self.config.PORT}")
        uvicorn.run(
            self.app,
            host=self.config.HOST,
            port=self.config.PORT,
            log_level="info"
        )
    
    def _start_api_server(self):
        """Start uvicorn in the current thread (used as background thread)"""
        uvicorn.run(
            self.app,
            host=self.config.HOST,
            port=self.config.PORT,
            log_level="info"
        )


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for Pathway pipeline"""
    logger.info("=" * 60)
    logger.info("Pathway Real-Time Streaming Pipeline for QuantPulse")
    logger.info(f"Pathway available: {PATHWAY_AVAILABLE}")
    logger.info("=" * 60)
    
    config = PipelineConfig()
    
    if config.MODE == 'live' and not config.OPENAI_API_KEY and not config.GROQ_API_KEY:
        logger.warning("No LLM API key set. RAG features will be limited.")
    
    pipeline = PathwayPipeline(config)
    
    try:
        pipeline.run()
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user")
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
