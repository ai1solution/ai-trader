"""
SerpAPI News Service for Crypto Market Intelligence
"""
import os
import httpx
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

SERPAPI_KEY = os.getenv("SERPAPI_KEY", "37298880d0fcef3adfd0564c3a7cca6fd95b1077fa33677fb1cc5fd1ee21cfb6")
SERPAPI_BASE = "https://serpapi.com/search.json"

async def fetch_crypto_news(symbol: Optional[str] = None, limit: int = 10) -> List[Dict]:
    """
    Fetch latest crypto news from SerpAPI
    
    Args:
        symbol: Crypto symbol to filter news (e.g., "BTC", "ETH")
        limit: Number of results to return
    
    Returns:
        List of news articles with title, link, snippet, source, date
    """
    try:
        # Build query
        if symbol:
            # Remove /USDT suffix if present
            clean_symbol = symbol.split('/')[0]
            query = f"{clean_symbol} cryptocurrency news"
        else:
            query = "cryptocurrency market news"
        
        params = {
            "engine": "google_news",
            "q": query,
            "api_key": SERPAPI_KEY,
            "num": limit,
            "gl": "us",
            "hl": "en"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(SERPAPI_BASE, params=params)
            response.raise_for_status()
            data = response.json()
        
        # Parse news results
        news_results = data.get("news_results", [])
        
        articles = []
        for item in news_results[:limit]:
            article = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": item.get("source", {}).get("name", "Unknown"),
                "date": item.get("date", ""),
                "thumbnail": item.get("thumbnail", ""),
                "timestamp": datetime.now().isoformat()
            }
            articles.append(article)
        
        logger.info(f"Fetched {len(articles)} news articles for query: {query}")
        return articles
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching news: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return []

async def fetch_trending_crypto_news(limit: int = 15) -> List[Dict]:
    """Fetch general trending crypto market news"""
    return await fetch_crypto_news(symbol=None, limit=limit)
