"""
Fetch and index company press releases.

Sources:
- Company investor relations pages
- PR Newswire (some free access)
- Business Wire
"""

import sys
import argparse
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

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


def fetch_company_press_releases(ticker: str, company_name: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch press releases from company investor relations page.
    
    Args:
        ticker: Company ticker symbol
        company_name: Optional company name
        limit: Maximum number of press releases to fetch
        
    Returns:
        List of press release dicts
    """
    releases = []
    
    if not REQUESTS_AVAILABLE:
        return releases
    
    # Common IR page patterns
    ir_patterns = [
        f"https://investor.{ticker.lower()}.com",
        f"https://ir.{ticker.lower()}.com",
        f"https://investorrelations.{ticker.lower()}.com",
    ]
    
    # Add some well-known companies
    known_companies = {
        "AAPL": "https://investor.apple.com/newsroom",
        "MSFT": "https://www.microsoft.com/investor/news",
        "GOOGL": "https://abc.xyz/investor/news",
        "AMZN": "https://ir.aboutamazon.com/news-releases",
        "META": "https://investor.fb.com/news",
        "TSLA": "https://ir.tesla.com/press-releases",
    }
    
    if ticker in known_companies:
        ir_patterns.insert(0, known_companies[ticker])
    
    for base_url in ir_patterns:
        try:
            # Try common press release URL patterns
            pr_urls = [
                f"{base_url}/news-releases",
                f"{base_url}/press-releases",
                f"{base_url}/news",
                f"{base_url}/press",
                base_url,
            ]
            
            for url in pr_urls:
                try:
                    response = requests.get(url, timeout=10, allow_redirects=True, headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    })
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Find press release links
                        pr_links = soup.find_all('a', href=re.compile(r'press|release|news', re.I), limit=limit)
                        
                        if pr_links:
                            print(f"✓ Found press release links at {url}")
                            
                            for link in pr_links[:limit]:
                                pr_url = link.get('href')
                                if not pr_url.startswith('http'):
                                    pr_url = f"{base_url.rstrip('/')}/{pr_url.lstrip('/')}"
                                
                                try:
                                    pr_response = requests.get(pr_url, timeout=10, headers={
                                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                                    })
                                    if pr_response.status_code == 200:
                                        pr_soup = BeautifulSoup(pr_response.text, 'html.parser')
                                        
                                        # Extract title
                                        title_elem = pr_soup.find('h1') or pr_soup.find('title')
                                        title = title_elem.get_text() if title_elem else "Press Release"
                                        
                                        # Extract date
                                        date_elem = pr_soup.find('time') or pr_soup.find(class_=re.compile(r'date'))
                                        date_text = date_elem.get_text() if date_elem else ""
                                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)
                                        pr_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
                                        
                                        # Extract content
                                        content_elem = pr_soup.find('article') or pr_soup.find('div', class_=re.compile(r'content|body|release'))
                                        content = content_elem.get_text() if content_elem else pr_soup.get_text()
                                        
                                        # Determine category
                                        category = "General"
                                        if re.search(r'earnings|financial|results', title, re.I):
                                            category = "Earnings"
                                        elif re.search(r'product|launch|announcement', title, re.I):
                                            category = "Product Launch"
                                        elif re.search(r'acquisition|merger|deal', title, re.I):
                                            category = "M&A"
                                        
                                        release = {
                                            "title": title,
                                            "text": content,
                                            "date": pr_date,
                                            "category": category,
                                            "source_url": pr_url,
                                            "source": "company_ir"
                                        }
                                        
                                        releases.append(release)
                                        
                                        time.sleep(0.5)  # Rate limiting
                                        
                                except Exception as e:
                                    continue
                            
                            if releases:
                                break  # Found releases, stop trying other URLs
                                
                except:
                    continue
            
            if releases:
                break  # Found releases, stop trying other base URLs
                
        except:
            continue
    
    return releases


def index_press_releases(
    database_path: Path,
    ticker: Optional[str] = None,
    limit: int = 20
) -> int:
    """
    Index company press releases into vector store.
    
    Args:
        database_path: Path to database
        ticker: Optional ticker to filter by
        limit: Maximum releases per ticker
        
    Returns:
        Number of documents indexed
    """
    print("📊 Initializing vector store for press releases...")
    try:
        vector_store = VectorStore(database_path)
        if not vector_store._available:
            print("❌ Vector store not available. Install: pip install chromadb sentence-transformers")
            return 1
    except Exception as e:
        print(f"❌ Error initializing vector store: {e}")
        return 1
    
    stats_before = vector_store.press_collection.count() if vector_store._available else 0
    print(f"📈 Current press releases: {stats_before} documents")
    
    if not ticker:
        print("❌ Error: --ticker is required for press releases")
        return 1
    
    all_documents = []
    
    # Fetch press releases
    print(f"🔍 Fetching press releases for {ticker}...")
    releases = fetch_company_press_releases(ticker, limit=limit)
    
    if not releases:
        print(f"⚠️  No press releases found for {ticker}")
        return 0
    
    print(f"✓ Found {len(releases)} press releases")
    
    # Create chunks for each release
    for release in releases:
        # Combine title and text
        full_text = f"{release['title']}\n\n{release['text']}"
        
        metadata = {
            "ticker": ticker.upper(),
            "date": release.get("date", datetime.now().strftime("%Y-%m-%d")),
            "title": release.get("title", ""),
            "category": release.get("category", "General"),
            "source_type": "press_release",
            "source_url": release.get("source_url", ""),
            "source": release.get("source", "unknown")
        }
        
        chunks = create_document_chunks(
            full_text,
            metadata,
            chunk_size=1500,
            chunk_overlap=200,
            max_chunks=50  # Press releases are typically shorter
        )
        
        all_documents.extend(chunks)
    
    # Index documents
    if all_documents:
        print(f"\n📦 Indexing {len(all_documents)} document chunks into vector store...")
        count = vector_store.add_press_releases(all_documents)
        print(f"✓ Successfully indexed {count} document chunks!")
        
        stats_after = vector_store.press_collection.count() if vector_store._available else 0
        print(f"📊 Total press releases in vector store: {stats_after}")
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and index company press releases")
    parser.add_argument("--database", required=True, type=Path, help="Path to SQLite database")
    parser.add_argument("--ticker", required=True, type=str, help="Company ticker symbol")
    parser.add_argument("--limit", type=int, default=20, help="Maximum releases to fetch")
    
    args = parser.parse_args()
    
    if not args.database.exists():
        print(f"❌ Error: Database not found: {args.database}")
        sys.exit(1)
    
    sys.exit(index_press_releases(
        args.database,
        args.ticker,
        args.limit
    ))

