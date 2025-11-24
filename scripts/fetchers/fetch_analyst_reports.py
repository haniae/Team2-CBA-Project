"""
Fetch and index analyst research reports.

Sources:
- Seeking Alpha articles
- MarketWatch analysis
- Company investor relations pages
"""

import sys
import io
import argparse
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Fix Windows console encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

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
    print("⚠️  Warning: requests/beautifulsoup4 not available")

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    yf = None


def fetch_yahoo_analyst_data(ticker: str) -> List[Dict[str, Any]]:
    """
    Fetch analyst recommendations and data from Yahoo Finance (reliable, no blocking).
    
    Args:
        ticker: Company ticker symbol
        
    Returns:
        List of analyst report dicts
    """
    articles = []
    
    if not YFINANCE_AVAILABLE:
        return articles
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        # Get analyst recommendations
        recommendations = info.get('recommendationMean', '')
        target_price = info.get('targetMeanPrice', None)
        target_high = info.get('targetHighPrice', None)
        target_low = info.get('targetLowPrice', None)
        num_analysts = info.get('numberOfAnalystOpinions', 0)
        current_price = info.get('currentPrice', None)
        
        # Get recent recommendations history
        try:
            rec_history = stock.recommendations
            if rec_history is not None and len(rec_history) > 0:
                # Get most recent recommendations
                latest_recs = rec_history.tail(min(10, len(rec_history)))
                
                for idx, (date, row) in enumerate(latest_recs.iterrows()):
                    firm = row.get('Firm', 'Unknown') if hasattr(row, 'get') else 'Unknown'
                    to_grade = row.get('To Grade', '') if hasattr(row, 'get') else ''
                    from_grade = row.get('From Grade', '') if hasattr(row, 'get') else ''
                    
                    # Create analyst report from recommendation
                    article = {
                        "title": f"{firm} {to_grade} {ticker}",
                        "text": f"Analyst Firm: {firm}\nRecommendation: {to_grade}\nPrevious: {from_grade}\nDate: {date.strftime('%Y-%m-%d')}\n\nCurrent Price: ${current_price:.2f} (Yahoo Finance)\nTarget Price: ${target_price:.2f} (Mean)\nTarget Range: ${target_low:.2f} - ${target_high:.2f}\nNumber of Analysts: {num_analysts}",
                        "analyst": firm,
                        "rating": to_grade,
                        "target_price": target_price,
                        "date": date.strftime("%Y-%m-%d"),
                        "source_url": f"https://finance.yahoo.com/quote/{ticker}/analysis",
                        "source": "yahoo_finance"
                    }
                    articles.append(article)
        except:
            pass
        
        # If no history, create a summary report
        if not articles and recommendations:
            article = {
                "title": f"Analyst Consensus for {ticker}",
                "text": f"Analyst Consensus: {recommendations}\nCurrent Price: ${current_price:.2f}\nTarget Price: ${target_price:.2f}\nTarget Range: ${target_low:.2f} - ${target_high:.2f}\nNumber of Analysts: {num_analysts}",
                "analyst": "Yahoo Finance Consensus",
                "rating": recommendations,
                "target_price": target_price,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "source_url": f"https://finance.yahoo.com/quote/{ticker}/analysis",
                "source": "yahoo_finance"
            }
            articles.append(article)
            
    except Exception as e:
        print(f"⚠️  Error fetching Yahoo Finance analyst data for {ticker}: {e}")
    
    return articles


def fetch_seeking_alpha_articles(ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch analyst articles from Seeking Alpha.
    
    Args:
        ticker: Company ticker symbol
        limit: Maximum number of articles to fetch
        
    Returns:
        List of article dicts
    """
    articles = []
    
    if not REQUESTS_AVAILABLE:
        return articles
    
    try:
        # Seeking Alpha articles URL
        url = f"https://seekingalpha.com/symbol/{ticker}/analysis"
        
        # More realistic browser headers to avoid 403 errors
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0"
        }
        
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        
        # Check for 403 or other blocking
        if response.status_code == 403:
            print(f"⚠️  Seeking Alpha blocked access for {ticker} (403 Forbidden). This is common - they have anti-scraping measures.")
            return articles
        
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find article links
        article_links = soup.find_all('a', href=re.compile(r'/article/'), limit=limit)
        
        for link in article_links:
            article_url = f"https://seekingalpha.com{link.get('href')}"
            
            try:
                article_response = requests.get(article_url, headers=headers, timeout=30)
                article_response.raise_for_status()
                
                article_soup = BeautifulSoup(article_response.text, 'html.parser')
                
                # Extract article content
                title = article_soup.find('h1')
                title_text = title.get_text() if title else "Untitled"
                
                # Extract article body
                article_body = article_soup.find('div', class_=re.compile(r'article.*body|content'))
                article_text = article_body.get_text() if article_body else ""
                
                # Extract author/analyst
                author = article_soup.find('a', class_=re.compile(r'author'))
                analyst_name = author.get_text() if author else "Unknown"
                
                # Extract date
                date_elem = article_soup.find('time')
                article_date = date_elem.get('datetime', '')[:10] if date_elem and date_elem.get('datetime') else datetime.now().strftime("%Y-%m-%d")
                
                # Extract rating if available
                rating_match = re.search(r'(Buy|Sell|Hold|Strong Buy|Strong Sell)', article_text, re.I)
                rating = rating_match.group(1) if rating_match else None
                
                # Extract price target if available
                target_match = re.search(r'target.*?\$?(\d+\.?\d*)', article_text, re.I)
                target_price = float(target_match.group(1)) if target_match else None
                
                article = {
                    "title": title_text,
                    "text": article_text,
                    "analyst": analyst_name,
                    "rating": rating,
                    "target_price": target_price,
                    "date": article_date,
                    "source_url": article_url,
                    "source": "seeking_alpha"
                }
                
                articles.append(article)
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                print(f"⚠️  Error fetching article {article_url}: {e}")
                continue
                
    except Exception as e:
        print(f"⚠️  Error fetching Seeking Alpha articles for {ticker}: {e}")
    
    return articles


def index_analyst_reports(
    database_path: Path,
    ticker: Optional[str] = None,
    source: str = "all",
    limit: int = 10
) -> int:
    """
    Index analyst research reports into vector store.
    
    Args:
        database_path: Path to database
        ticker: Optional ticker to filter by
        source: Source to fetch from ("yahoo", "seeking_alpha", "all" - yahoo is most reliable)
        limit: Maximum reports per ticker
        
    Returns:
        Number of documents indexed
    """
    print("📊 Initializing vector store for analyst reports...")
    try:
        vector_store = VectorStore(database_path)
        if not vector_store._available:
            print("❌ Vector store not available. Install: pip install chromadb sentence-transformers")
            return 1
    except Exception as e:
        print(f"❌ Error initializing vector store: {e}")
        return 1
    
    stats_before = vector_store.analyst_collection.count() if vector_store._available else 0
    print(f"📈 Current analyst reports: {stats_before} documents")
    
    if not ticker:
        print("❌ Error: --ticker is required for analyst reports")
        return 1
    
    all_documents = []
    
    # Fetch analyst reports - try Yahoo Finance first (reliable, no blocking)
    articles = []
    
    if source in ["yahoo", "all"]:
        print(f"🔍 Fetching analyst data from Yahoo Finance for {ticker}...")
        articles.extend(fetch_yahoo_analyst_data(ticker))
    
    # Try Seeking Alpha as fallback (may be blocked)
    if source in ["seeking_alpha", "all"] and len(articles) < limit:
        print(f"🔍 Fetching analyst reports from Seeking Alpha for {ticker}...")
        seeking_alpha_articles = fetch_seeking_alpha_articles(ticker, limit - len(articles))
        articles.extend(seeking_alpha_articles)
    
    if not articles:
        print(f"⚠️  No analyst reports found for {ticker}")
        return 0
    
    print(f"✓ Found {len(articles)} analyst reports")
    
    # Create chunks for each report
    for article in articles:
        # Combine title and text
        full_text = f"{article['title']}\n\n{article['text']}"
        
        metadata = {
            "ticker": ticker.upper(),
            "date": article.get("date", datetime.now().strftime("%Y-%m-%d")),
            "analyst": article.get("analyst", "Unknown"),
            "rating": article.get("rating"),
            "target_price": article.get("target_price"),
            "title": article.get("title", ""),
            "source_type": "analyst_report",
            "source_url": article.get("source_url", ""),
            "source": article.get("source", "unknown")
        }
        
        chunks = create_document_chunks(
            full_text,
            metadata,
            chunk_size=1500,
            chunk_overlap=200,
            max_chunks=200  # Analyst reports can be longer
        )
        
        all_documents.extend(chunks)
    
    # Index documents
    if all_documents:
        print(f"\n📦 Indexing {len(all_documents)} document chunks into vector store...")
        count = vector_store.add_analyst_reports(all_documents)
        print(f"✓ Successfully indexed {count} document chunks!")
        
        stats_after = vector_store.analyst_collection.count() if vector_store._available else 0
        print(f"📊 Total analyst reports in vector store: {stats_after}")
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and index analyst research reports")
    parser.add_argument("--database", required=True, type=Path, help="Path to SQLite database")
    parser.add_argument("--ticker", required=True, type=str, help="Company ticker symbol")
    parser.add_argument("--source", choices=["yahoo", "seeking_alpha", "all"], default="all", help="Source to fetch from (yahoo is most reliable, all tries both)")
    parser.add_argument("--limit", type=int, default=10, help="Maximum reports to fetch")
    
    args = parser.parse_args()
    
    if not args.database.exists():
        print(f"❌ Error: Database not found: {args.database}")
        sys.exit(1)
    
    sys.exit(index_analyst_reports(
        args.database,
        args.ticker,
        args.source,
        args.limit
    ))

