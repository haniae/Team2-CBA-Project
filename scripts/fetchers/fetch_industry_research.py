"""
Fetch and index industry research reports.

Sources:
- Industry association reports
- Government economic reports
- Academic research papers (SSRN, NBER)
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


def fetch_ssrn_papers(sector: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch research papers from SSRN (Social Science Research Network).
    
    Args:
        sector: Industry sector (e.g., "Technology", "Finance")
        limit: Maximum number of papers to fetch
        
    Returns:
        List of paper dicts
    """
    papers = []
    
    if not REQUESTS_AVAILABLE:
        return papers
    
    try:
        # SSRN search URL
        url = "https://papers.ssrn.com/sol3/results.cfm"
        params = {
            "form_name": "journalBrowse",
            "journal_id": "",
            "Network": "yes",
            "NetworkID": "",
            "txtKeyWords": sector,
            "txtAuthors": "",
            "txtTitle": "",
            "SortOrder": "relevance",
            "pageNumber": 1,
            "pageSize": limit
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find paper links (simplified - actual implementation would need more parsing)
        paper_links = soup.find_all('a', href=re.compile(r'/sol3/papers\.cfm'), limit=limit)
        
        for link in paper_links[:limit]:
            paper_url = f"https://papers.ssrn.com{link.get('href')}"
            
            try:
                paper_response = requests.get(paper_url, headers=headers, timeout=30)
                paper_response.raise_for_status()
                
                paper_soup = BeautifulSoup(paper_response.text, 'html.parser')
                
                # Extract title
                title_elem = paper_soup.find('h1') or paper_soup.find('title')
                title = title_elem.get_text() if title_elem else "Research Paper"
                
                # Extract abstract/content
                abstract_elem = paper_soup.find('div', class_=re.compile(r'abstract|content'))
                abstract = abstract_elem.get_text() if abstract_elem else ""
                
                # Extract date
                date_elem = paper_soup.find(text=re.compile(r'\d{4}'))
                date_match = re.search(r'(\d{4})', date_elem if date_elem else "")
                paper_date = date_match.group(1) + "-01-01" if date_match else datetime.now().strftime("%Y-%m-%d")
                
                paper = {
                    "title": title,
                    "text": abstract,
                    "sector": sector,
                    "date": paper_date,
                    "source_url": paper_url,
                    "source": "ssrn"
                }
                
                papers.append(paper)
                
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"⚠️  Error fetching SSRN papers for {sector}: {e}")
    
    return papers


def fetch_government_reports(sector: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch industry reports from government sources (BLS, Census, etc.).
    
    Args:
        sector: Industry sector
        limit: Maximum number of reports to fetch
        
    Returns:
        List of report dicts
    """
    reports = []
    
    if not REQUESTS_AVAILABLE:
        return reports
    
    # This is a placeholder - actual implementation would query specific government APIs
    # For now, return empty list
    print(f"ℹ️  Government reports fetching for {sector} not yet fully implemented")
    
    return reports


def index_industry_research(
    database_path: Path,
    sector: Optional[str] = None,
    source: str = "ssrn",
    limit: int = 10
) -> int:
    """
    Index industry research reports into vector store.
    
    Args:
        database_path: Path to database
        sector: Industry sector (e.g., "Technology", "Finance")
        source: Source to fetch from ("ssrn", "government", "all")
        limit: Maximum reports per sector
        
    Returns:
        Number of documents indexed
    """
    print("📊 Initializing vector store for industry research...")
    try:
        vector_store = VectorStore(database_path)
        if not vector_store._available:
            print("❌ Vector store not available. Install: pip install chromadb sentence-transformers")
            return 1
    except Exception as e:
        print(f"❌ Error initializing vector store: {e}")
        return 1
    
    stats_before = vector_store.industry_collection.count() if vector_store._available else 0
    print(f"📈 Current industry research: {stats_before} documents")
    
    if not sector:
        print("❌ Error: --sector is required for industry research")
        return 1
    
    all_documents = []
    
    # Fetch research reports
    reports = []
    
    if source in ["ssrn", "all"]:
        print(f"🔍 Fetching research from SSRN for {sector}...")
        reports.extend(fetch_ssrn_papers(sector, limit))
    
    if source in ["government", "all"]:
        print(f"🔍 Fetching research from government sources for {sector}...")
        reports.extend(fetch_government_reports(sector, limit))
    
    if not reports:
        print(f"⚠️  No industry research found for {sector}")
        return 0
    
    print(f"✓ Found {len(reports)} research reports")
    
    # Create chunks for each report
    for report in reports:
        # Combine title and text
        full_text = f"{report['title']}\n\n{report['text']}"
        
        metadata = {
            "sector": sector,
            "industry": report.get("industry", sector),
            "date": report.get("date", datetime.now().strftime("%Y-%m-%d")),
            "title": report.get("title", ""),
            "source_type": "industry_research",
            "source_url": report.get("source_url", ""),
            "source": report.get("source", "unknown")
        }
        
        chunks = create_document_chunks(
            full_text,
            metadata,
            chunk_size=1500,
            chunk_overlap=200,
            max_chunks=200  # Research papers can be longer
        )
        
        all_documents.extend(chunks)
    
    # Index documents
    if all_documents:
        print(f"\n📦 Indexing {len(all_documents)} document chunks into vector store...")
        count = vector_store.add_industry_research(all_documents)
        print(f"✓ Successfully indexed {count} document chunks!")
        
        stats_after = vector_store.industry_collection.count() if vector_store._available else 0
        print(f"📊 Total industry research in vector store: {stats_after}")
    
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and index industry research reports")
    parser.add_argument("--database", required=True, type=Path, help="Path to SQLite database")
    parser.add_argument("--sector", required=True, type=str, help="Industry sector (e.g., Technology, Finance)")
    parser.add_argument("--source", choices=["ssrn", "government", "all"], default="ssrn", help="Source to fetch from")
    parser.add_argument("--limit", type=int, default=10, help="Maximum reports to fetch")
    
    args = parser.parse_args()
    
    if not args.database.exists():
        print(f"❌ Error: Database not found: {args.database}")
        sys.exit(1)
    
    sys.exit(index_industry_research(
        args.database,
        args.sector,
        args.source,
        args.limit
    ))

