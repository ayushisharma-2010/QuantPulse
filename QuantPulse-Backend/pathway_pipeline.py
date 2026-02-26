"""
Pathway Real-Time Streaming Pipeline for QuantPulse
====================================================

This module implements the core Pathway streaming pipeline that:
1. Ingests live stock data from yfinance
2. Computes technical indicators in real-time
3. Indexes news and ESG documents for RAG queries
4. Exposes REST API endpoints for the FastAPI backend

Architecture:
- Stock Data Connector: Polls yfinance every 60s
- Streaming Tables: pw.Table for stock data, indicators, documents
- Document Store: Vector + BM25 hybrid search
- RAG Engine: LLM-powered Q&A with citations
- REST Server: FastAPI on port 8090

Usage:
    python pathway_pipeline.py

Environment Variables:
    PATHWAY_PORT: REST API port (default: 8090)
    OPENAI_API_KEY: OpenAI API key for embeddings and LLM
    PATHWAY_MODE: 'live' or 'demo' (default: demo)
    PATHWAY_POLL_INTERVAL: Stock polling interval in seconds (default: 60)
"""

import os
import sys
import logging
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
    logger.info("Pathway is available")
except (ImportError, AttributeError) as e:
    PATHWAY_AVAILABLE = False
    logger.warning("Pathway is not available. Running in standalone mode without Pathway streaming.")
    logger.warning("For full Pathway support, run on Linux/WSL or use Docker.")

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
    
    # Pipeline mode
    MODE = os.getenv('PATHWAY_MODE', 'demo')  # 'live' or 'demo'
    
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
    uptime_seconds: float
    stocks_tracked: int
    documents_indexed: int
    last_update: str


# ============================================================================
# Stock Data Connector
# ============================================================================

class StockDataConnector:
    """Custom Pathway connector for yfinance stock data polling"""
    
    def __init__(self, symbols: List[str], poll_interval: int = 60):
        """
        Initialize stock data connector
        
        Args:
            symbols: List of stock symbols to track (e.g., ['RELIANCE.NS', 'TCS.NS'])
            poll_interval: Polling interval in seconds (default: 60)
        """
        self.symbols = symbols
        self.poll_interval = poll_interval
        self.last_fetch_time = {}
        
        logger.info(f"StockDataConnector initialized with {len(symbols)} symbols")
        logger.info(f"Poll interval: {poll_interval} seconds")
    
    def fetch_stock_data(self) -> List[Dict[str, Any]]:
        """
        Fetch current stock data from yfinance
        
        Returns:
            List of stock data dictionaries
        """
        results = []
        current_time = datetime.now()
        
        for symbol in self.symbols:
            try:
                # Fetch data from yfinance
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period='1d', interval='1m')
                
                if hist.empty:
                    logger.warning(f"No data available for {symbol}")
                    continue
                
                # Get latest price data
                latest = hist.iloc[-1]
                previous = hist.iloc[-2] if len(hist) > 1 else latest
                
                # Calculate change percent
                change_percent = ((latest['Close'] - previous['Close']) / previous['Close'] * 100) if previous['Close'] > 0 else 0.0
                
                # Build stock data record
                stock_data = {
                    'symbol': symbol,
                    'price': float(latest['Close']),
                    'volume': int(latest['Volume']),
                    'open': float(latest['Open']),
                    'high': float(latest['High']),
                    'low': float(latest['Low']),
                    'change_percent': float(change_percent),
                    'timestamp': current_time.isoformat(),
                    'market_cap': info.get('marketCap', 0),
                    'company_name': info.get('longName', symbol)
                }
                
                results.append(stock_data)
                self.last_fetch_time[symbol] = current_time
                
                logger.debug(f"Fetched data for {symbol}: ₹{stock_data['price']:.2f} ({change_percent:+.2f}%)")
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched data for {len(results)}/{len(self.symbols)} symbols")
        return results
    
    def create_pathway_connector(self):
        """
        Create Pathway input connector using Python connector API
        
        Returns:
            Pathway connector function
        """
        def connector_func():
            """Generator function for Pathway connector"""
            import time
            
            while True:
                # Fetch stock data
                data = self.fetch_stock_data()
                
                # Yield data to Pathway
                for record in data:
                    yield record
                
                # Wait for next poll interval
                logger.debug(f"Sleeping for {self.poll_interval} seconds...")
                time.sleep(self.poll_interval)
        
        return connector_func


class DemoStockDataConnector:
    """Demo connector that generates simulated stock data"""
    
    def __init__(self, symbols: List[str], poll_interval: int = 60):
        """
        Initialize demo stock data connector
        
        Args:
            symbols: List of stock symbols to simulate
            poll_interval: Polling interval in seconds
        """
        self.symbols = symbols
        self.poll_interval = poll_interval
        
        # Realistic base prices for Indian stocks (approximate current prices)
        realistic_prices = {
            'RELIANCE.NS': 1400.0,
            'TCS.NS': 2650.0,
            'INFY.NS': 1450.0,
            'HDFCBANK.NS': 906.0,
            'ICICIBANK.NS': 650.0,
            'HINDUNILVR.NS': 2100.0,
            'ITC.NS': 320.0,
            'SBIN.NS': 380.0,
            'BHARTIARTL.NS': 900.0,
            'KOTAKBANK.NS': 1550.0
        }
        
        # Use realistic prices if available, otherwise random
        self.base_prices = {}
        for symbol in symbols:
            if symbol in realistic_prices:
                self.base_prices[symbol] = realistic_prices[symbol]
            else:
                self.base_prices[symbol] = np.random.uniform(100, 5000)
        
        self.current_prices = self.base_prices.copy()
        
        logger.info(f"DemoStockDataConnector initialized with {len(symbols)} symbols")
    
    def generate_stock_data(self) -> List[Dict[str, Any]]:
        """
        Generate simulated stock data
        
        Returns:
            List of simulated stock data dictionaries
        """
        results = []
        current_time = datetime.now()
        
        for symbol in self.symbols:
            try:
                # Simulate price movement (random walk)
                previous_price = self.current_prices[symbol]
                change_percent = np.random.normal(0, 2)  # Mean 0%, StdDev 2%
                new_price = previous_price * (1 + change_percent / 100)
                
                # Keep price within reasonable bounds
                base_price = self.base_prices[symbol]
                new_price = max(base_price * 0.7, min(base_price * 1.3, new_price))
                
                self.current_prices[symbol] = new_price
                
                # Generate realistic volume
                volume = int(np.random.uniform(100000, 10000000))
                
                # Build stock data record
                stock_data = {
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
                }
                
                results.append(stock_data)
                
                logger.debug(f"Generated demo data for {symbol}: ₹{new_price:.2f} ({change_percent:+.2f}%)")
                
            except Exception as e:
                logger.error(f"Error generating demo data for {symbol}: {e}")
                continue
        
        logger.info(f"Generated demo data for {len(results)} symbols")
        return results
    
    def create_pathway_connector(self):
        """
        Create Pathway input connector for demo data
        
        Returns:
            Pathway connector function
        """
        def connector_func():
            """Generator function for Pathway connector"""
            import time
            
            while True:
                # Generate demo data
                data = self.generate_stock_data()
                
                # Yield data to Pathway
                for record in data:
                    yield record
                
                # Wait for next poll interval
                logger.debug(f"Sleeping for {self.poll_interval} seconds...")
                time.sleep(self.poll_interval)
        
        return connector_func


# ============================================================================
# Technical Indicators Calculator
# ============================================================================

class TechnicalIndicators:
    """Calculate technical indicators for stock data"""
    
    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            prices: List of closing prices (most recent last)
            period: RSI period (default: 14)
            
        Returns:
            RSI value (0-100) or None if insufficient data
        """
        if len(prices) < period + 1:
            return None
        
        # Calculate price changes
        deltas = np.diff(prices[-period-1:])
        
        # Separate gains and losses
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Calculate average gain and loss
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Simple Moving Average (SMA)
        
        Args:
            prices: List of closing prices
            period: SMA period
            
        Returns:
            SMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        return float(np.mean(prices[-period:]))
    
    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Exponential Moving Average (EMA)
        
        Args:
            prices: List of closing prices
            period: EMA period
            
        Returns:
            EMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        prices_array = np.array(prices[-period:])
        weights = np.exp(np.linspace(-1., 0., period))
        weights /= weights.sum()
        
        ema = np.convolve(prices_array, weights, mode='valid')[-1]
        return float(ema)
    
    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Optional[Dict[str, float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            prices: List of closing prices
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line period (default: 9)
            
        Returns:
            Dictionary with macd, signal, histogram or None if insufficient data
        """
        if len(prices) < slow + signal:
            return None
        
        # Calculate EMAs
        fast_ema = TechnicalIndicators.calculate_ema(prices, fast)
        slow_ema = TechnicalIndicators.calculate_ema(prices, slow)
        
        if fast_ema is None or slow_ema is None:
            return None
        
        macd_line = fast_ema - slow_ema
        
        # For signal line, we'd need historical MACD values
        # Simplified: use the current MACD as signal (in production, maintain history)
        signal_line = macd_line
        histogram = macd_line - signal_line
        
        return {
            'macd': float(macd_line),
            'signal': float(signal_line),
            'histogram': float(histogram)
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> Optional[Dict[str, float]]:
        """
        Calculate Bollinger Bands
        
        Args:
            prices: List of closing prices
            period: Period for moving average (default: 20)
            std_dev: Number of standard deviations (default: 2.0)
            
        Returns:
            Dictionary with upper, middle, lower bands or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        recent_prices = prices[-period:]
        middle_band = np.mean(recent_prices)
        std = np.std(recent_prices)
        
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)
        
        # Calculate %B (position within bands)
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
        """
        Calculate price volatility (standard deviation)
        
        Args:
            prices: List of closing prices
            period: Period for calculation
            
        Returns:
            Volatility value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        recent_prices = prices[-period:]
        returns = np.diff(recent_prices) / recent_prices[:-1]
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        
        return float(volatility)


class StockDataAggregator:
    """Aggregate and maintain historical stock data for indicator calculation"""
    
    def __init__(self, max_history: int = 200):
        """
        Initialize stock data aggregator
        
        Args:
            max_history: Maximum number of historical data points to keep
        """
        self.max_history = max_history
        self.price_history = {}  # symbol -> list of prices
        self.volume_history = {}  # symbol -> list of volumes
        self.timestamp_history = {}  # symbol -> list of timestamps
        
        logger.info(f"StockDataAggregator initialized with max_history={max_history}")
    
    def add_data_point(self, symbol: str, price: float, volume: int, timestamp: str):
        """
        Add a new data point for a symbol
        
        Args:
            symbol: Stock symbol
            price: Closing price
            volume: Trading volume
            timestamp: Timestamp string
        """
        # Initialize lists if symbol is new
        if symbol not in self.price_history:
            self.price_history[symbol] = []
            self.volume_history[symbol] = []
            self.timestamp_history[symbol] = []
        
        # Add new data point
        self.price_history[symbol].append(price)
        self.volume_history[symbol].append(volume)
        self.timestamp_history[symbol].append(timestamp)
        
        # Trim history if needed
        if len(self.price_history[symbol]) > self.max_history:
            self.price_history[symbol] = self.price_history[symbol][-self.max_history:]
            self.volume_history[symbol] = self.volume_history[symbol][-self.max_history:]
            self.timestamp_history[symbol] = self.timestamp_history[symbol][-self.max_history:]
    
    def get_prices(self, symbol: str) -> List[float]:
        """Get price history for a symbol"""
        return self.price_history.get(symbol, [])
    
    def get_volumes(self, symbol: str) -> List[int]:
        """Get volume history for a symbol"""
        return self.volume_history.get(symbol, [])
    
    def calculate_all_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Calculate all technical indicators for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary with all indicators
        """
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
        
        # MACD
        macd_data = TechnicalIndicators.calculate_macd(prices)
        if macd_data:
            indicators.update({
                'macd': macd_data['macd'],
                'macd_signal': macd_data['signal'],
                'macd_histogram': macd_data['histogram']
            })
        
        # Bollinger Bands
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
    """Simple document store with text search (simplified for demo)"""
    
    def __init__(self, watch_dir: str, doc_type: str = "news"):
        """
        Initialize document store
        
        Args:
            watch_dir: Directory to watch for documents
            doc_type: Type of documents ('news' or 'esg')
        """
        self.watch_dir = watch_dir
        self.doc_type = doc_type
        self.documents = []  # List of document dictionaries
        self.last_scan_time = None
        
        # Create directory if it doesn't exist
        os.makedirs(watch_dir, exist_ok=True)
        
        logger.info(f"DocumentStore initialized for {doc_type} at {watch_dir}")
    
    def scan_and_index(self):
        """Scan directory and index new documents"""
        try:
            # Find all JSON files
            json_files = glob.glob(os.path.join(self.watch_dir, "*.json"))
            
            # Track new documents
            new_docs = 0
            
            for file_path in json_files:
                # Check if already indexed
                if any(doc.get('file_path') == file_path for doc in self.documents):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        doc_data = json.load(f)
                    
                    # Add metadata
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
        """
        Search documents (simple keyword matching)
        
        Args:
            query: Search query
            top_k: Number of results to return
            symbol_filter: Optional stock symbol to filter by
            
        Returns:
            List of matching documents
        """
        # Ensure documents are up to date
        self.scan_and_index()
        
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        results = []
        
        for doc in self.documents:
            # Apply symbol filter if provided
            symbol_matched = False
            if symbol_filter:
                # Handle both 'symbol' (singular) and 'symbols' (plural array)
                doc_symbol = doc.get('symbol', '')
                doc_symbols = doc.get('symbols', [])
                
                # Check if symbol matches
                if doc_symbol == symbol_filter or symbol_filter in doc_symbols:
                    symbol_matched = True
                else:
                    continue
            
            # Calculate relevance score (simple keyword matching)
            score = 0
            
            # If symbol matched, give base score
            if symbol_matched:
                score = 10  # Base score for symbol match
            
            # Check title
            title = doc.get('title', '').lower()
            for term in query_terms:
                if term in title:
                    score += 3  # Title matches are more important
            
            # Check content
            content = doc.get('content', '').lower()
            for term in query_terms:
                score += content.count(term)
            
            # Check company_name for ESG documents
            company_name = doc.get('company_name', '').lower()
            for term in query_terms:
                if term in company_name:
                    score += 2
            
            if score > 0:
                results.append({
                    'document': doc,
                    'score': score
                })
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        return [r['document'] for r in results[:top_k]]
    
    def get_all_documents(self) -> List[Dict[str, Any]]:
        """Get all indexed documents"""
        self.scan_and_index()
        return self.documents
    
    def get_document_count(self) -> int:
        """Get total number of indexed documents"""
        return len(self.documents)


class SimpleRAGEngine:
    """Simple RAG engine using document store and LLM"""
    
    def __init__(self, news_store: SimpleDocumentStore, esg_store: SimpleDocumentStore, 
                 llm_provider: str = "groq", api_key: Optional[str] = None):
        """
        Initialize RAG engine
        
        Args:
            news_store: News document store
            esg_store: ESG document store
            llm_provider: LLM provider ('openai' or 'groq')
            api_key: API key for LLM provider
        """
        self.news_store = news_store
        self.esg_store = esg_store
        self.llm_provider = llm_provider
        self.api_key = api_key
        
        # Check if we have LLM access
        self.llm_available = bool(api_key)
        
        if not self.llm_available:
            logger.warning("No LLM API key provided. RAG will return document excerpts only.")
        
        logger.info(f"RAG Engine initialized with {llm_provider} provider")
    
    def query(self, question: str, symbols: Optional[List[str]] = None, 
              include_news: bool = True, include_esg: bool = True) -> Dict[str, Any]:
        """
        Execute RAG query
        
        Args:
            question: User question
            symbols: Optional list of stock symbols to focus on
            include_news: Include news documents
            include_esg: Include ESG documents
            
        Returns:
            Dictionary with answer, citations, and metadata
        """
        try:
            # Retrieve relevant documents
            retrieved_docs = []
            
            if include_news:
                news_docs = self.news_store.search(
                    query=question,
                    top_k=3,
                    symbol_filter=symbols[0] if symbols else None
                )
                retrieved_docs.extend([{'source': 'news', 'doc': doc} for doc in news_docs])
            
            if include_esg:
                esg_docs = self.esg_store.search(
                    query=question,
                    top_k=2,
                    symbol_filter=symbols[0] if symbols else None
                )
                retrieved_docs.extend([{'source': 'esg', 'doc': doc} for doc in esg_docs])
            
            # Build context from retrieved documents
            context = self._build_context(retrieved_docs)
            
            # Generate answer
            if self.llm_available:
                answer = self._generate_llm_answer(question, context, symbols)
            else:
                answer = self._generate_fallback_answer(question, retrieved_docs)
            
            # Extract citations
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
        """Build context string from retrieved documents"""
        context_parts = []
        
        for item in retrieved_docs:
            doc = item['doc']
            source = item['source']
            
            title = doc.get('title', 'Untitled')
            content = doc.get('content', '')[:500]  # Limit content length
            
            context_parts.append(f"[{source.upper()}] {title}\n{content}...")
        
        return "\n\n".join(context_parts)
    
    def _generate_llm_answer(self, question: str, context: str, symbols: Optional[List[str]]) -> str:
        """Generate answer using LLM"""
        if not context:
            return "I don't have enough information to answer that question. Please try asking about specific stocks or topics covered in the available documents."
        
        try:
            # Import Groq client
            from groq import Groq
            
            # Initialize Groq client
            client = Groq(api_key=self.api_key)
            
            # Build prompt
            symbol_text = f" regarding {', '.join(symbols)}" if symbols else ""
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
            
            # Call Groq API
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
            # Fallback to template response
            symbol_text = f" regarding {', '.join(symbols)}" if symbols else ""
            return f"Based on the available documents{symbol_text}, here's what I found:\n\n{context[:300]}...\n\n(Note: LLM integration error: {str(e)})"
    
    def _generate_fallback_answer(self, question: str, retrieved_docs: List[Dict]) -> str:
        """Generate fallback answer without LLM"""
        if not retrieved_docs:
            return "I couldn't find any relevant documents to answer your question. Please try rephrasing or asking about different topics."
        
        # Return excerpts from top documents
        excerpts = []
        for item in retrieved_docs[:2]:
            doc = item['doc']
            title = doc.get('title', 'Untitled')
            content = doc.get('content', '')[:200]
            excerpts.append(f"• {title}: {content}...")
        
        return "Here are relevant excerpts from the documents:\n\n" + "\n\n".join(excerpts)
    
    def _extract_citations(self, retrieved_docs: List[Dict]) -> List[Dict[str, Any]]:
        """Extract citations from retrieved documents"""
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
        """
        Initialize green score calculator
        
        Args:
            esg_store: ESG document store
        """
        self.esg_store = esg_store
        logger.info("GreenScoreCalculator initialized")
    
    def calculate_score(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Calculate green score for a symbol
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE" or "RELIANCE.NS")
            
        Returns:
            Dictionary with score and breakdown or None if no data
        """
        # Normalize symbol - add .NS if not present
        if not symbol.endswith('.NS'):
            symbol = f"{symbol}.NS"
        
        # Search for ESG documents for this symbol
        esg_docs = self.esg_store.search(query=symbol, symbol_filter=symbol, top_k=1)
        
        if not esg_docs:
            return None
        
        doc = esg_docs[0]
        
        # Extract ESG metrics from the new format
        overall_score = doc.get('overall_score', 50)
        category = doc.get('category', 'medium')
        
        # Get breakdown from environmental, social, governance sections
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
# Pathway Pipeline Class
# ============================================================================

class PathwayPipeline:
    """Main Pathway streaming pipeline orchestrator"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.start_time = datetime.now()
        
        # Pipeline components (will be initialized)
        self.stock_connector = None
        self.stock_table = None
        self.indicators_table = None
        self.news_store = None
        self.esg_store = None
        self.rag_engine = None
        self.green_score_calculator = None
        
        # Stock data aggregator for historical data
        self.stock_aggregator = StockDataAggregator(max_history=200)
        
        # In-memory cache for latest stock data (for REST API)
        self.latest_stock_data = {}
        
        # FastAPI app for REST endpoints
        self.app = self._create_fastapi_app()
        
        logger.info(f"Pathway Pipeline initialized in {config.MODE} mode")
        logger.info(f"Tracking {len(config.WATCHLIST)} stocks")
        logger.info(f"REST API will run on {config.HOST}:{config.PORT}")
    
    def _create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application for REST endpoints"""
        app = FastAPI(
            title="Pathway Streaming Pipeline API",
            description="Real-time stock analytics with RAG-powered insights",
            version="1.0.0"
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Register routes
        self._register_routes(app)
        
        return app
    
    def _register_routes(self, app: FastAPI):
        """Register API routes"""
        
        @app.get("/")
        async def root():
            return {
                "service": "Pathway Streaming Pipeline",
                "version": "1.0.0",
                "status": "running",
                "mode": self.config.MODE
            }
        
        @app.get("/v1/status", response_model=StatusResponse)
        async def get_status():
            """Get pipeline status"""
            uptime = (datetime.now() - self.start_time).total_seconds()
            return StatusResponse(
                status="running",
                mode=self.config.MODE,
                uptime_seconds=uptime,
                stocks_tracked=len(self.config.WATCHLIST),
                documents_indexed=0,  # TODO: Implement document counting
                last_update=datetime.now().isoformat()
            )
        
        @app.get("/v1/ticker/{symbol}", response_model=StockDataResponse)
        async def get_ticker_data(symbol: str):
            """Get latest streaming data for a stock"""
            # Update data before serving
            self.update_stock_data()
            
            # Get latest data
            data = self.get_latest_stock_data(symbol.upper())
            
            if not data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Stock {symbol} not found in watchlist"
                )
            
            # Get indicators
            indicators = self.get_indicators(symbol.upper())
            
            return StockDataResponse(
                symbol=data['symbol'],
                price=data['price'],
                volume=data['volume'],
                change_percent=data['change_percent'],
                timestamp=data['timestamp'],
                indicators=indicators if indicators else None
            )
        
        @app.post("/v1/rag/query", response_model=RAGQueryResponse)
        async def rag_query(request: RAGQueryRequest):
            """Execute RAG query against document store"""
            if not self.rag_engine:
                raise HTTPException(
                    status_code=503,
                    detail="RAG engine not initialized"
                )
            
            # Execute RAG query
            result = self.rag_engine.query(
                question=request.query,
                symbols=request.symbols,
                include_news=request.include_news,
                include_esg=request.include_esg
            )
            
            return RAGQueryResponse(
                answer=result['answer'],
                citations=result['citations'],
                stock_data=None,  # TODO: Add stock data if symbols provided
                timestamp=result['timestamp']
            )
        
        @app.get("/v1/green-score/{symbol}", response_model=GreenScoreResponse)
        async def get_green_score(symbol: str):
            """Get ESG/green score for a stock"""
            if not self.green_score_calculator:
                raise HTTPException(
                    status_code=503,
                    detail="Green score calculator not initialized"
                )
            
            # Calculate green score
            score_data = self.green_score_calculator.calculate_score(symbol.upper())
            
            if not score_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"No ESG data available for {symbol}"
                )
            
            return GreenScoreResponse(**score_data)
    
    def initialize(self):
        """Initialize all pipeline components"""
        logger.info("Initializing Pathway pipeline components...")
        
        # 1. Initialize stock data connector
        self._initialize_stock_connector()
        
        # 2. Initialize document stores
        self._initialize_document_stores()
        
        # 3. Initialize RAG engine
        self._initialize_rag_engine()
        
        # 4. Initialize green score calculator
        self._initialize_green_score()
        
        logger.info("Pipeline initialization complete")
    
    def _initialize_document_stores(self):
        """Initialize news and ESG document stores"""
        logger.info("Initializing document stores...")
        
        # News store
        self.news_store = SimpleDocumentStore(
            watch_dir=self.config.NEWS_DIR,
            doc_type="news"
        )
        
        # ESG store
        self.esg_store = SimpleDocumentStore(
            watch_dir=self.config.ESG_DIR,
            doc_type="esg"
        )
        
        # Initial scan
        self.news_store.scan_and_index()
        self.esg_store.scan_and_index()
        
        logger.info(f"Document stores initialized: {self.news_store.get_document_count()} news, {self.esg_store.get_document_count()} ESG documents")
    
    def _initialize_rag_engine(self):
        """Initialize RAG engine"""
        logger.info("Initializing RAG engine...")
        
        # Determine which API key to use
        openai_key = self.config.OPENAI_API_KEY
        groq_key = os.getenv('GROQ_API_KEY', '')
        
        logger.info(f"OpenAI key present: {bool(openai_key)}")
        logger.info(f"Groq key present: {bool(groq_key)}")
        
        api_key = openai_key if openai_key else groq_key
        
        logger.info(f"Using API key: {api_key[:20] if api_key else 'None'}...")
        
        self.rag_engine = SimpleRAGEngine(
            news_store=self.news_store,
            esg_store=self.esg_store,
            llm_provider='groq',  # Default to Groq (free)
            api_key=api_key
        )
        
        logger.info("RAG engine initialized")
    
    def _initialize_green_score(self):
        """Initialize green score calculator"""
        logger.info("Initializing green score calculator...")
        
        self.green_score_calculator = GreenScoreCalculator(
            esg_store=self.esg_store
        )
        
        logger.info("Green score calculator initialized")
    
    def _initialize_stock_connector(self):
        """Initialize stock data ingestion connector"""
        logger.info("Initializing stock data connector...")
        
        if self.config.MODE == 'live':
            # Use real yfinance connector
            logger.info("Using live yfinance connector")
            connector = StockDataConnector(
                symbols=self.config.WATCHLIST,
                poll_interval=self.config.POLL_INTERVAL
            )
        else:
            # Use demo connector
            logger.info("Using demo stock data connector")
            connector = DemoStockDataConnector(
                symbols=self.config.WATCHLIST,
                poll_interval=self.config.POLL_INTERVAL
            )
        
        # Create Pathway input table using Python connector
        # Note: In a full implementation, this would use pw.io.python.read()
        # For now, we'll store the connector and fetch data on-demand for REST API
        self.stock_connector = connector
        
        # Initialize latest data cache
        logger.info("Fetching initial stock data...")
        if self.config.MODE == 'live':
            initial_data = connector.fetch_stock_data()
        else:
            initial_data = connector.generate_stock_data()
        
        for record in initial_data:
            self.latest_stock_data[record['symbol']] = record
        
        logger.info(f"Stock connector initialized with {len(self.latest_stock_data)} symbols")
    
    def get_latest_stock_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest stock data for a symbol
        
        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS')
            
        Returns:
            Stock data dictionary or None if not found
        """
        return self.latest_stock_data.get(symbol)
    
    def update_stock_data(self):
        """Update stock data from connector (called periodically)"""
        if self.stock_connector is None:
            return
        
        try:
            if self.config.MODE == 'live':
                new_data = self.stock_connector.fetch_stock_data()
            else:
                new_data = self.stock_connector.generate_stock_data()
            
            for record in new_data:
                self.latest_stock_data[record['symbol']] = record
                
                # Add to aggregator for indicator calculation
                self.stock_aggregator.add_data_point(
                    symbol=record['symbol'],
                    price=record['price'],
                    volume=record['volume'],
                    timestamp=record['timestamp']
                )
                
        except Exception as e:
            logger.error(f"Error updating stock data: {e}")
    
    def get_indicators(self, symbol: str) -> Dict[str, Any]:
        """
        Get calculated technical indicators for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Dictionary of indicators
        """
        return self.stock_aggregator.calculate_all_indicators(symbol)
    
    def run(self):
        """Start the pipeline and REST server"""
        logger.info("Starting Pathway pipeline...")
        
        # Initialize components
        self.initialize()
        
        # Start REST API server
        logger.info(f"Starting REST API server on {self.config.HOST}:{self.config.PORT}")
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
    logger.info("=" * 60)
    
    # Load configuration
    config = PipelineConfig()
    
    # Validate configuration
    if config.MODE == 'live' and not config.OPENAI_API_KEY:
        logger.warning("OPENAI_API_KEY not set. RAG features will be limited.")
    
    # Create and run pipeline
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
