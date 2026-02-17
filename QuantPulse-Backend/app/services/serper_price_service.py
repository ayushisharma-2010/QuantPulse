"""
Serper Price Service - Live Stock Price Fallback

Uses Serper API (Google Search) to fetch live stock prices when yfinance fails.
This is a fallback mechanism to ensure the Vercel website always has live data.
"""

import os
import logging
import httpx
import re
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SerperPriceService:
    """
    Service to fetch live stock prices using Serper API (Google Search).
    
    This acts as a fallback when yfinance fails to provide live data.
    """
    
    def __init__(self):
        self.api_key = os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"
        
        if not self.api_key:
            logger.warning("⚠️ SERPER_API_KEY not found. Live price fallback disabled.")
    
    async def get_live_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch live stock price from Google Search via Serper API.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE", "TCS")
            
        Returns:
            dict: Live price data or None if failed
        """
        if not self.api_key:
            logger.error("Cannot fetch live price: SERPER_API_KEY not configured")
            return None
        
        try:
            # Clean symbol
            clean_symbol = symbol.strip().upper().replace(".NS", "")
            
            # Search query for NSE stock price
            query = f"{clean_symbol} NSE stock price live"
            
            logger.info(f"🔍 Fetching live price for {clean_symbol} via Serper API...")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.base_url,
                    json={"q": query, "gl": "in", "hl": "en"},
                    headers={
                        "X-API-KEY": self.api_key,
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"Serper API error: {response.status_code}")
                    return None
                
                data = response.json()
                
                # Extract price from knowledge graph or organic results
                price_data = self._extract_price_from_response(data, clean_symbol)
                
                if price_data:
                    logger.info(f"✅ Live price fetched for {clean_symbol}: ₹{price_data['price']}")
                    return price_data
                else:
                    logger.warning(f"⚠️ Could not extract price for {clean_symbol} from Serper response")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching live price via Serper: {e}")
            return None
    
    def _extract_price_from_response(self, data: Dict, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Extract stock price from Serper API response.
        
        Tries multiple extraction strategies:
        1. Knowledge Graph (Google Finance widget)
        2. Organic results with price patterns
        3. Answer box
        """
        try:
            # Strategy 1: Knowledge Graph (most reliable)
            if "knowledgeGraph" in data:
                kg = data["knowledgeGraph"]
                
                # Look for price in various fields
                price = None
                change = None
                change_pct = None
                
                # Check attributes
                if "attributes" in kg:
                    for attr in kg["attributes"]:
                        if "price" in attr.lower() or "₹" in str(attr):
                            price_match = re.search(r'₹?\s*([\d,]+\.?\d*)', str(attr))
                            if price_match:
                                price = float(price_match.group(1).replace(',', ''))
                
                # Check description
                if not price and "description" in kg:
                    price_match = re.search(r'₹\s*([\d,]+\.?\d*)', kg["description"])
                    if price_match:
                        price = float(price_match.group(1).replace(',', ''))
                
                if price:
                    return {
                        "symbol": symbol,
                        "price": price,
                        "change": change,
                        "change_percent": change_pct,
                        "timestamp": datetime.now().isoformat(),
                        "source": "serper_knowledge_graph"
                    }
            
            # Strategy 2: Organic Results
            if "organic" in data:
                for result in data["organic"][:3]:  # Check first 3 results
                    snippet = result.get("snippet", "")
                    
                    # Look for price patterns in snippet
                    # Pattern: ₹2,950.50 or 2950.50 or 2,950
                    price_match = re.search(r'₹?\s*([\d,]+\.?\d*)', snippet)
                    if price_match:
                        try:
                            price = float(price_match.group(1).replace(',', ''))
                            
                            # Validate price range (NSE stocks typically 1-100000)
                            if 1 <= price <= 100000:
                                # Try to extract change
                                change_match = re.search(r'([+-]?\d+\.?\d*)\s*\(([+-]?\d+\.?\d*)%\)', snippet)
                                change = None
                                change_pct = None
                                
                                if change_match:
                                    change = float(change_match.group(1))
                                    change_pct = float(change_match.group(2))
                                
                                return {
                                    "symbol": symbol,
                                    "price": price,
                                    "change": change,
                                    "change_percent": change_pct,
                                    "timestamp": datetime.now().isoformat(),
                                    "source": "serper_organic"
                                }
                        except ValueError:
                            continue
            
            # Strategy 3: Answer Box
            if "answerBox" in data:
                answer = data["answerBox"].get("answer", "")
                price_match = re.search(r'₹?\s*([\d,]+\.?\d*)', answer)
                if price_match:
                    try:
                        price = float(price_match.group(1).replace(',', ''))
                        if 1 <= price <= 100000:
                            return {
                                "symbol": symbol,
                                "price": price,
                                "change": None,
                                "change_percent": None,
                                "timestamp": datetime.now().isoformat(),
                                "source": "serper_answer_box"
                            }
                    except ValueError:
                        pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting price from Serper response: {e}")
            return None


# Global instance
serper_price_service = SerperPriceService()
