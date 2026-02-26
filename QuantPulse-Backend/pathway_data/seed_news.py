"""
News Seeding Script for Pathway Pipeline
=========================================

This script fetches news articles and writes them as JSON files
to the pathway_data/news/ directory for Pathway to index.

Usage:
    python pathway_data/seed_news.py [--once]
    
Options:
    --once: Run once and exit (default: continuous loop every 2 minutes)

Environment Variables:
    NEWSAPI_KEY: NewsAPI key (optional, will use demo data if not set)
    SERPER_API_KEY: Serper API key (optional alternative)
"""

import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import requests
try:
    import requests
except ImportError:
    print("requests library not found. Install with: pip install requests")
    sys.exit(1)


class NewsSeeder:
    """Seed news articles for Pathway pipeline"""
    
    def __init__(self, output_dir: str, api_key: Optional[str] = None):
        """
        Initialize news seeder
        
        Args:
            output_dir: Directory to write news JSON files
            api_key: NewsAPI or Serper API key
        """
        self.output_dir = output_dir
        self.api_key = api_key
        self.use_demo = not bool(api_key)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Stock symbols to fetch news for
        self.symbols = [
            'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
            'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK'
        ]
        
        print(f"NewsSeeder initialized")
        print(f"Output directory: {output_dir}")
        print(f"Mode: {'DEMO' if self.use_demo else 'LIVE'}")
    
    def fetch_news_from_api(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Fetch news from NewsAPI
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of news articles
        """
        if not self.api_key:
            return []
        
        try:
            # NewsAPI endpoint
            url = "https://newsapi.org/v2/everything"
            params = {
                'q': f"{symbol} India stock",
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': 5,
                'apiKey': self.api_key
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            articles = data.get('articles', [])
            
            # Convert to our format
            news_items = []
            for article in articles:
                news_item = {
                    'title': article.get('title', ''),
                    'content': article.get('description', '') or article.get('content', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'published_date': article.get('publishedAt', datetime.now().isoformat()),
                    'symbols': [f"{symbol}.NS"],
                    'url': article.get('url', '')
                }
                news_items.append(news_item)
            
            return news_items
            
        except Exception as e:
            print(f"Error fetching news for {symbol}: {e}")
            return []
    
    def generate_demo_news(self, symbol: str) -> List[Dict[str, Any]]:
        """
        Generate demo news articles
        
        Args:
            symbol: Stock symbol
            
        Returns:
            List of demo news articles
        """
        templates = [
            {
                'title': f"{symbol} Reports Strong Q4 Earnings, Beats Estimates",
                'content': f"{symbol} has reported better-than-expected earnings for Q4, with revenue growth of 15% YoY. The company's strong performance was driven by increased demand in key markets and successful cost optimization initiatives."
            },
            {
                'title': f"{symbol} Announces New Strategic Partnership",
                'content': f"{symbol} today announced a strategic partnership aimed at expanding its market presence. The collaboration is expected to drive innovation and create new growth opportunities in the coming quarters."
            },
            {
                'title': f"Analysts Upgrade {symbol} Stock Rating",
                'content': f"Leading financial analysts have upgraded their rating for {symbol} stock, citing strong fundamentals and positive growth outlook. The target price has been revised upward by 12%."
            },
            {
                'title': f"{symbol} Invests in Sustainability Initiatives",
                'content': f"{symbol} has announced significant investments in sustainability and ESG initiatives. The company aims to reduce carbon emissions by 30% over the next five years and improve its environmental footprint."
            },
            {
                'title': f"{symbol} Expands Operations in Key Markets",
                'content': f"{symbol} is expanding its operations in key growth markets, with plans to open new facilities and increase workforce. The expansion is part of the company's long-term growth strategy."
            }
        ]
        
        # Select 2-3 random templates
        selected = random.sample(templates, k=random.randint(2, 3))
        
        news_items = []
        for template in selected:
            news_item = {
                'title': template['title'],
                'content': template['content'],
                'source': random.choice(['Economic Times', 'Business Standard', 'Moneycontrol', 'LiveMint']),
                'published_date': (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
                'symbols': [f"{symbol}.NS"],
                'url': f"https://example.com/news/{symbol.lower()}-{random.randint(1000, 9999)}"
            }
            news_items.append(news_item)
        
        return news_items
    
    def write_news_file(self, news_item: Dict[str, Any]):
        """
        Write news item to JSON file
        
        Args:
            news_item: News article dictionary
        """
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        symbol = news_item['symbols'][0].replace('.NS', '')
        random_id = random.randint(1000, 9999)
        filename = f"news_{symbol}_{timestamp}_{random_id}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(news_item, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Written: {filename}")
            
        except Exception as e:
            print(f"✗ Error writing {filename}: {e}")
    
    def seed_once(self):
        """Seed news articles once"""
        print("\n" + "="*60)
        print(f"Seeding news articles at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        total_articles = 0
        
        for symbol in self.symbols:
            print(f"\nFetching news for {symbol}...")
            
            if self.use_demo:
                articles = self.generate_demo_news(symbol)
            else:
                articles = self.fetch_news_from_api(symbol)
                if not articles:
                    # Fallback to demo if API fails
                    print(f"  Falling back to demo data for {symbol}")
                    articles = self.generate_demo_news(symbol)
            
            # Write articles
            for article in articles:
                self.write_news_file(article)
                total_articles += 1
            
            # Small delay between symbols to avoid rate limiting
            time.sleep(0.5)
        
        print(f"\n✓ Seeded {total_articles} news articles")
    
    def seed_continuous(self, interval: int = 120):
        """
        Seed news articles continuously
        
        Args:
            interval: Interval between seeding runs in seconds (default: 120 = 2 minutes)
        """
        print(f"\nStarting continuous seeding (interval: {interval}s)")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                self.seed_once()
                print(f"\nWaiting {interval} seconds until next run...")
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\nSeeding stopped by user")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Seed news articles for Pathway pipeline")
    parser.add_argument('--once', action='store_true', help="Run once and exit")
    parser.add_argument('--interval', type=int, default=120, help="Interval between runs in seconds (default: 120)")
    args = parser.parse_args()
    
    # Get API key from environment
    api_key = os.getenv('NEWSAPI_KEY') or os.getenv('SERPER_API_KEY')
    
    # Determine output directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'news')
    
    # Create seeder
    seeder = NewsSeeder(output_dir=output_dir, api_key=api_key)
    
    # Run seeding
    if args.once:
        seeder.seed_once()
    else:
        seeder.seed_continuous(interval=args.interval)


if __name__ == "__main__":
    main()
