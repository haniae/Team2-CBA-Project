"""
Fetch and index earnings call transcripts.

Sources:
- Seeking Alpha (free transcripts)
- Fintel.io (free transcripts)
- Company investor relations pages
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
    print("⚠️  Warning: requests/beautifulsoup4 not available. Install: pip install requests beautifulsoup4")


def fetch_seeking_alpha_transcript(ticker: str, quarter: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch earnings transcript from Seeking Alpha.
    
    Args:
        ticker: Company ticker symbol
        quarter: Optional quarter filter (e.g., "Q1-2024")
        
    Returns:
        Dict with transcript data or None
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    try:
        # Seeking Alpha earnings transcript URL pattern
        url = f"https://seekingalpha.com/symbol/{ticker}/earnings/transcript"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find transcript links (this is a simplified version - actual implementation would need more parsing)
        transcript_links = soup.find_all('a', href=re.compile(r'/article/.*transcript'))
        
        if not transcript_links:
            return None
        
        # Get most recent transcript
        latest_link = transcript_links[0]
        transcript_url = f"https://seekingalpha.com{latest_link.get('href')}"
        
        # Fetch transcript content
        transcript_response = requests.get(transcript_url, headers=headers, timeout=30)
        transcript_response.raise_for_status()
        
        transcript_soup = BeautifulSoup(transcript_response.text, 'html.parser')
        
        # Extract transcript text (simplified - actual implementation would parse Q&A sections)
        transcript_text = transcript_soup.get_text()
        
        # Extract date from page
        date_match = re.search(r'(\w+\s+\d+,\s+\d{4})', transcript_text)
        transcript_date = date_match.group(1) if date_match else datetime.now().strftime("%Y-%m-%d")
        
        # Extract quarter from text
        quarter_match = re.search(r'Q(\d)\s+(\d{4})', transcript_text, re.IGNORECASE)
        if quarter_match:
            quarter_str = f"Q{quarter_match.group(1)}-{quarter_match.group(2)}"
        else:
            quarter_str = None
        
        return {
            "text": transcript_text,
            "date": transcript_date,
            "quarter": quarter_str,
            "source_url": transcript_url,
            "source": "seeking_alpha"
        }
        
    except Exception as e:
        print(f"⚠️  Error fetching Seeking Alpha transcript for {ticker}: {e}")
        return None


def fetch_company_ir_transcript(ticker: str, company_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Fetch earnings transcript from company investor relations page.
    
    Args:
        ticker: Company ticker symbol
        company_name: Optional company name for URL construction
        
    Returns:
        Dict with transcript data or None
    """
    if not REQUESTS_AVAILABLE:
        return None
    
    # Common IR page patterns
    ir_patterns = [
        f"https://investor.{ticker.lower()}.com",
        f"https://ir.{ticker.lower()}.com",
        f"https://investorrelations.{ticker.lower()}.com",
    ]
    
    # Add some well-known companies
    known_companies = {
        "AAPL": "https://investor.apple.com",
        "MSFT": "https://www.microsoft.com/investor",
        "GOOGL": "https://abc.xyz/investor",
        "AMZN": "https://ir.aboutamazon.com",
    }
    
    if ticker in known_companies:
        ir_patterns.insert(0, known_companies[ticker])
    
    for base_url in ir_patterns:
        try:
            # Try to find earnings/transcripts page
            transcript_urls = [
                f"{base_url}/events-and-presentations",
                f"{base_url}/earnings",
                f"{base_url}/transcripts",
            ]
            
            for url in transcript_urls:
                try:
                    response = requests.get(url, timeout=10, allow_redirects=True)
                    if response.status_code == 200:
                        # Parse page to find transcript links
                        soup = BeautifulSoup(response.text, 'html.parser')
                        transcript_links = soup.find_all('a', href=re.compile(r'transcript|earnings.*call', re.I))
                        
                        if transcript_links:
                            # This is a placeholder - actual implementation would fetch and parse transcript
                            print(f"ℹ️  Found transcript links at {url} for {ticker}")
                            return None  # Placeholder - would return actual transcript
                except:
                    continue
        except:
            continue
    
    return None


def index_earnings_transcripts(
    database_path: Path,
    ticker: Optional[str] = None,
    source: str = "seeking_alpha",
    limit: Optional[int] = None
) -> int:
    """
    Index earnings call transcripts into vector store.
    
    Args:
        database_path: Path to database
        ticker: Optional ticker to filter by
        source: Source to fetch from ("seeking_alpha", "company_ir", "all")
        limit: Limit number of transcripts per ticker
        
    Returns:
        Number of documents indexed
    """
    print("📊 Initializing vector store for earnings transcripts...")
    try:
        vector_store = VectorStore(database_path)
        if not vector_store._available:
            print("❌ Vector store not available. Install: pip install chromadb sentence-transformers")
            return 1
    except Exception as e:
        print(f"❌ Error initializing vector store: {e}")
        return 1
    
    stats_before = vector_store.earnings_collection.count() if vector_store._available else 0
    print(f"📈 Current earnings transcripts: {stats_before} documents")
    
    if not ticker:
        print("❌ Error: --ticker is required for earnings transcripts")
        return 1
    
    all_documents = []
    
    # Fetch transcript
    transcript_data = None
    if source in ["seeking_alpha", "all"]:
        print(f"🔍 Fetching transcript from Seeking Alpha for {ticker}...")
        transcript_data = fetch_seeking_alpha_transcript(ticker)
    
    if not transcript_data and source in ["company_ir", "all"]:
        print(f"🔍 Fetching transcript from company IR page for {ticker}...")
        transcript_data = fetch_company_ir_transcript(ticker)
    
    if not transcript_data:
        print(f"⚠️  No transcript found for {ticker}")
        return 0
    
    # Create chunks
    metadata = {
        "ticker": ticker.upper(),
        "date": transcript_data.get("date", datetime.now().strftime("%Y-%m-%d")),
        "quarter": transcript_data.get("quarter"),
        "source_type": "earnings_transcript",
        "source_url": transcript_data.get("source_url", ""),
        "source": transcript_data.get("source", "unknown")
    }
    
    chunks = create_document_chunks(
        transcript_data["text"],
        metadata,
        chunk_size=1500,
        chunk_overlap=200,
        max_chunks=1000
    )
    
    all_documents.extend(chunks)
    print(f"✓ Extracted {len(chunks)} chunks from transcript")
    
    # Index documents
    if all_documents:
        print(f"\n📦 Indexing {len(all_documents)} document chunks into vector store...")
        count = vector_store.add_earnings_transcripts(all_documents)
        print(f"✓ Successfully indexed {count} document chunks!")
        
        stats_after = vector_store.earnings_collection.count() if vector_store._available else 0
        print(f"📊 Total earnings transcripts in vector store: {stats_after}")
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and index earnings call transcripts")
    parser.add_argument("--database", required=True, type=Path, help="Path to SQLite database")
    parser.add_argument("--ticker", required=True, type=str, help="Company ticker symbol")
    parser.add_argument("--source", choices=["seeking_alpha", "company_ir", "all"], default="all", help="Source to fetch from")
    parser.add_argument("--limit", type=int, help="Limit number of transcripts (not yet implemented)")
    
    args = parser.parse_args()
    
    if not args.database.exists():
        print(f"❌ Error: Database not found: {args.database}")
        sys.exit(1)
    
    sys.exit(index_earnings_transcripts(
        args.database,
        args.ticker,
        args.source,
        args.limit
    ))

