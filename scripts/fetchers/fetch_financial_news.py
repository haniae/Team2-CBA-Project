"""
Fetch and index financial news articles.

Sources:
- Yahoo Finance news (via yfinance)
- NewsAPI (free tier available)
- RSS feeds
"""

import sys
import io
import argparse
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Fix Windows console encoding issues (safer approach)
if sys.platform == 'win32':
    try:
        if not isinstance(sys.stdout, io.TextIOWrapper) and hasattr(sys.stdout, 'buffer'):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if not isinstance(sys.stderr, io.TextIOWrapper) and hasattr(sys.stderr, 'buffer'):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except (AttributeError, ValueError, OSError):
        import os
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

from finanlyzeos_chatbot.rag_retriever import VectorStore
from scripts.utils.chunking import create_document_chunks

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None


def fetch_yahoo_news(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch news articles from Yahoo Finance.
    
    Args:
        ticker: Company ticker symbol
        limit: Maximum number of articles to fetch
        
    Returns:
        List of news article dicts
    """
    articles = []
    
    if not YFINANCE_AVAILABLE:
        print("⚠️  yfinance not available. Install: pip install yfinance")
        return articles
    
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news:
            return articles
        
        for item in news[:limit]:
            # Yahoo Finance news structure has changed - data is nested
            content = item.get("content", {})
            title = content.get("title", item.get("title", ""))
            summary = content.get("summary", item.get("summary", ""))
            description = content.get("description", "")
            
            # Combine summary and description for text
            text = summary or description or ""
            
            # Get URL
            canonical_url = item.get("canonicalUrl", {})
            source_url = canonical_url.get("url", "") if isinstance(canonical_url, dict) else canonical_url or item.get("link", "")
            
            # Get publisher
            provider = item.get("provider", {})
            publisher = provider.get("displayName", "Yahoo Finance") if isinstance(provider, dict) else str(provider) or "Yahoo Finance"
            
            # Get date
            pub_date = content.get("pubDate", item.get("pubDate", ""))
            if pub_date:
                try:
                    from dateutil import parser as date_parser
                    date_obj = date_parser.parse(pub_date)
                    date_str = date_obj.strftime("%Y-%m-%d")
                except:
                    date_str = datetime.now().strftime("%Y-%m-%d")
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
            
            article = {
                "title": title,
                "text": text,
                "publisher": publisher,
                "date": date_str,
                "source_url": source_url,
                "source": "yahoo_finance"
            }
            
            # If we have a link and text is short, try to fetch full article
            if article["source_url"] and len(article["text"]) < 500 and REQUESTS_AVAILABLE:
                try:
                    response = requests.get(article["source_url"], timeout=10, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        # Extract article text (simplified - would need better parsing)
                        article_text = soup.get_text()
                        if len(article_text) > len(article["text"]):
                            article["text"] = article_text
                except:
                    pass  # Use summary if full article fetch fails
            
            # Only add if we have some text
            if article["text"]:
                articles.append(article)
            
    except Exception as e:
        print(f"⚠️  Error fetching Yahoo Finance news for {ticker}: {e}")
    
    return articles


def fetch_newsapi_news(ticker: str, api_key: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch news articles from NewsAPI.
    
    Args:
        ticker: Company ticker symbol
        api_key: NewsAPI API key (optional, free tier available)
        limit: Maximum number of articles to fetch
        
    Returns:
        List of news article dicts
    """
    articles = []
    
    if not api_key:
        # Try to get from environment
        import os
        api_key = os.getenv("NEWSAPI_KEY")
    
    if not api_key or not REQUESTS_AVAILABLE:
        return articles
    
    try:
        # NewsAPI endpoint
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": ticker,
            "apiKey": api_key,
            "sortBy": "publishedAt",
            "pageSize": limit,
            "language": "en"
        }
        
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        for item in data.get("articles", [])[:limit]:
            article = {
                "title": item.get("title", ""),
                "text": item.get("description", "") + " " + item.get("content", ""),
                "publisher": item.get("source", {}).get("name", "Unknown"),
                "date": item.get("publishedAt", "")[:10] if item.get("publishedAt") else datetime.now().strftime("%Y-%m-%d"),
                "source_url": item.get("url", ""),
                "source": "newsapi"
            }
            articles.append(article)
            
    except Exception as e:
        print(f"⚠️  Error fetching NewsAPI news for {ticker}: {e}")
    
    return articles


def index_financial_news(
    database_path: Path,
    ticker: Optional[str] = None,
    source: str = "yahoo",
    limit: int = 10,
    days_back: int = 30
) -> int:
    """
    Index financial news articles into vector store.
    
    Args:
        database_path: Path to database
        ticker: Optional ticker to filter by
        source: Source to fetch from ("yahoo", "newsapi", "all")
        limit: Maximum articles per ticker
        days_back: How many days back to fetch news
        
    Returns:
        Number of documents indexed
    """
    print("📊 Initializing vector store for financial news...")
    try:
        vector_store = VectorStore(database_path)
        if not vector_store._available:
            print("❌ Vector store not available. Install: pip install chromadb sentence-transformers")
            return 1
    except Exception as e:
        print(f"❌ Error initializing vector store: {e}")
        return 1
    
    stats_before = vector_store.news_collection.count() if vector_store._available else 0
    print(f"📈 Current financial news: {stats_before} documents")
    
    if not ticker:
        print("❌ Error: --ticker is required for financial news")
        return 1
    
    all_documents = []
    
    # Fetch news articles
    articles = []
    
    if source in ["yahoo", "all"]:
        print(f"🔍 Fetching news from Yahoo Finance for {ticker}...")
        articles.extend(fetch_yahoo_news(ticker, limit))
    
    if source in ["newsapi", "all"]:
        print(f"🔍 Fetching news from NewsAPI for {ticker}...")
        articles.extend(fetch_newsapi_news(ticker, limit=limit))
    
    if not articles:
        print(f"⚠️  No news articles found for {ticker}")
        return 0
    
    print(f"✓ Found {len(articles)} news articles")
    
    # Create chunks for each article
    for article in articles:
        # Combine title and text
        full_text = f"{article['title']}\n\n{article['text']}"
        
        metadata = {
            "ticker": ticker.upper(),
            "date": article.get("date", datetime.now().strftime("%Y-%m-%d")),
            "publisher": article.get("publisher", "Unknown"),
            "title": article.get("title", ""),
            "source_type": "news",
            "source_url": article.get("source_url", ""),
            "source": article.get("source", "unknown")
        }
        
        chunks = create_document_chunks(
            full_text,
            metadata,
            chunk_size=1500,
            chunk_overlap=200,
            max_chunks=50  # News articles are typically shorter
        )
        
        all_documents.extend(chunks)
    
    # Index documents
    if all_documents:
        print(f"\n📦 Indexing {len(all_documents)} document chunks into vector store...")
        count = vector_store.add_financial_news(all_documents)
        print(f"✓ Successfully indexed {count} document chunks!")
        
        stats_after = vector_store.news_collection.count() if vector_store._available else 0
        print(f"📊 Total financial news in vector store: {stats_after}")
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and index financial news articles")
    parser.add_argument("--database", required=True, type=Path, help="Path to SQLite database")
    parser.add_argument("--ticker", required=True, type=str, help="Company ticker symbol")
    parser.add_argument("--source", choices=["yahoo", "newsapi", "all"], default="yahoo", help="Source to fetch from")
    parser.add_argument("--limit", type=int, default=10, help="Maximum articles to fetch")
    parser.add_argument("--days-back", type=int, default=30, help="How many days back to fetch news")
    
    args = parser.parse_args()
    
    if not args.database.exists():
        print(f"❌ Error: Database not found: {args.database}")
        sys.exit(1)
    
    sys.exit(index_financial_news(
        args.database,
        args.ticker,
        args.source,
        args.limit,
        args.days_back
    ))

