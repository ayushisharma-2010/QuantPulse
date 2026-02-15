"""
Data Provider Service — The Live Data Engine

Uses yfinance exclusively to fetch real-time market data for:
1. The target stock (e.g., RELIANCE.NS)
2. Nifty 50 (^NSEI) for market regime context
3. India VIX (^INDIAVIX) for risk context

Includes TTL-based LRU caching to prevent Yahoo rate-limiting.
"""

import time
import logging
from functools import lru_cache, wraps

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)

# =============================================================================
# TTL-Cached LRU Decorator
# =============================================================================

def timed_lru_cache(seconds: int = 300, maxsize: int = 10):
    """
    LRU cache with a time-to-live (TTL).
    Entries expire after `seconds` and are re-fetched on the next call.
    """
    def wrapper(func):
        func = lru_cache(maxsize=maxsize)(func)
        func._lifetime = seconds
        func._expiration = time.monotonic() + seconds

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            if time.monotonic() >= func._expiration:
                func.cache_clear()
                func._expiration = time.monotonic() + func._lifetime
                logger.info(f"🔄 Cache expired for {func.__name__}, re-fetching...")
            return func(*args, **kwargs)

        wrapped_func.cache_clear = func.cache_clear
        wrapped_func.cache_info = func.cache_info
        return wrapped_func

    return wrapper


# =============================================================================
# Ticker Normalization
# =============================================================================

def normalize_ticker(ticker: str) -> str:
    """
    Ensure ticker has the .NS suffix for NSE stocks.
    If the ticker already has a suffix (contains '.') or starts with '^', leave it.
    """
    ticker = ticker.strip().upper()
    if ticker.startswith("^"):
        return ticker
    if "." not in ticker:
        return f"{ticker}.NS"
    return ticker


# =============================================================================
# Core Data Fetching
# =============================================================================

def _download_safe(ticker: str, period: str = "2y"):
    """
    Safely download data from yfinance with error handling.
    Returns None on failure instead of crashing.
    """
    try:
        logger.info(f"📥 Downloading {ticker} ({period})...")
        data = yf.download(ticker, period=period, progress=False, auto_adjust=True)

        if data is None or data.empty:
            logger.warning(f"⚠️ No data returned for {ticker}")
            return None

        # Flatten MultiIndex columns if present (yfinance sometimes returns multi-level)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        logger.info(f"✅ Got {len(data)} rows for {ticker}")
        return data

    except Exception as e:
        logger.error(f"❌ Failed to download {ticker}: {e}")
        return None


@timed_lru_cache(seconds=300, maxsize=10)
def fetch_market_context(ticker: str) -> dict:
    """
    Fetch complete market context for analysis.

    Downloads 2 years of daily data for:
    1. The target stock
    2. ^NSEI (Nifty 50) — for regime detection
    3. ^INDIAVIX (India VIX) — for risk assessment

    Args:
        ticker: Stock symbol (e.g., "RELIANCE" or "RELIANCE.NS")

    Returns:
        dict with keys: 'target_df', 'nifty_df', 'vix_df'
        - target_df: DataFrame or None if ticker not found
        - nifty_df: DataFrame or None if Nifty data unavailable
        - vix_df: DataFrame or None if VIX data unavailable
    """
    ns_ticker = normalize_ticker(ticker)

    logger.info(f"🔍 Fetching market context for {ns_ticker}...")

    # Fetch all three datasets
    target_df = _download_safe(ns_ticker, period="2y")
    nifty_df = _download_safe("^NSEI", period="2y")
    vix_df = _download_safe("^INDIAVIX", period="2y")

    # Log summary
    target_rows = len(target_df) if target_df is not None else 0
    nifty_rows = len(nifty_df) if nifty_df is not None else 0
    vix_rows = len(vix_df) if vix_df is not None else 0
    logger.info(
        f"📊 Market context ready: "
        f"target={target_rows} rows, "
        f"nifty={nifty_rows} rows, "
        f"vix={vix_rows} rows"
    )

    return {
        "target_df": target_df,
        "nifty_df": nifty_df,
        "vix_df": vix_df,
    }


def get_current_vix_level(vix_df) -> float:
    """
    Extract the latest VIX closing value from the VIX DataFrame.
    Returns 15.0 as a safe default if data is unavailable.
    """
    if vix_df is None:
        logger.warning("⚠️ VIX data unavailable, using default 15.0")
        return 15.0

    try:
        if vix_df.empty:
            logger.warning("⚠️ VIX DataFrame is empty, using default 15.0")
            return 15.0
        return float(vix_df["Close"].iloc[-1])
    except (KeyError, IndexError, AttributeError):
        logger.warning("⚠️ Could not extract VIX close, using default 15.0")
        return 15.0
