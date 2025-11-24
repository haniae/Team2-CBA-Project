"""
Index documents for RAG Pipeline

This script indexes:
1. SEC filings (narratives) into vector store
2. Uploaded documents into vector store

Run this after ingesting new SEC filings or when users upload documents.
"""

import sys
import argparse
import time
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot.rag_retriever import VectorStore
from finanlyzeos_chatbot.sec_filing_parser import extract_sections_from_filing
from finanlyzeos_chatbot import database
from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.data_sources import EdgarClient
try:
    from finanlyzeos_chatbot.ticker_universe import load_ticker_universe
except ImportError:
    load_ticker_universe = None

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


def download_filing_text(cik: str, accession_number: str, user_agent: str) -> Optional[str]:
    """
    Download SEC filing text from SEC website.
    
    Args:
        cik: Company CIK (Central Index Key)
        accession_number: SEC accession number (e.g., "0001234567-23-000123")
        user_agent: User agent string for SEC API
        
    Returns:
        Filing text content or None if download fails
    """
    if not REQUESTS_AVAILABLE:
        print("⚠️  requests/BeautifulSoup not available. Install: pip install requests beautifulsoup4")
        return None
    
    try:
        # Parse accession number to get components
        # Format: 0001234567-23-000123 -> 0001234567 (CIK), 23 (year), 000123 (doc number)
        parts = accession_number.split('-')
        if len(parts) != 3:
            print(f"⚠️  Invalid accession number format: {accession_number}")
            return None
        
        # The first part is the CIK embedded in the accession number
        accession_cik = parts[0].lstrip('0') or '0'
        # The last part is the document number (e.g., 000079)
        doc_number = parts[2]
        
        # Build URL to the filing index first, then get the primary document
        # Format: https://www.sec.gov/Archives/edgar/data/{CIK_from_accession}/{doc_number}/{accession_number}-index.htm
        index_url = f"https://www.sec.gov/Archives/edgar/data/{accession_cik}/{doc_number}/{accession_number}-index.htm"
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        })
        
        # Rate limiting
        time.sleep(0.12)
        
        # First, try to get the index to find the primary document
        try:
            index_response = session.get(index_url, timeout=30)
            index_response.raise_for_status()
            
            # Parse index to find primary document (usually ends with .htm or .txt)
            if REQUESTS_AVAILABLE:
                soup = BeautifulSoup(index_response.text, 'html.parser')
                # Look for the primary document link
                primary_doc = None
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    # Primary documents are usually named like the form type (e.g., aapl-20240928.htm)
                    if 'primary' in link.text.lower() or 'document' in link.text.lower() and 'type' in link.text.lower():
                        primary_doc = href
                        break
                
                # If no primary link found, try common patterns
                if not primary_doc:
                    # Try to find .htm or .txt files
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        if href.endswith('.htm') or href.endswith('.txt'):
                            # Prefer files that look like the main filing
                            if any(x in href.lower() for x in ['10k', '10-k', '10q', '10-q', 'primary']):
                                primary_doc = href
                                break
                            elif not primary_doc:  # Fallback to first .htm/.txt
                                primary_doc = href
                
                if primary_doc:
                    # Make absolute URL
                    if primary_doc.startswith('http'):
                        base_url = primary_doc
                    else:
                        base_url = f"https://www.sec.gov{primary_doc}" if primary_doc.startswith('/') else f"https://www.sec.gov/Archives/edgar/data/{accession_cik}/{doc_number}/{primary_doc}"
                else:
                    # Fallback to the .txt file
                    base_url = f"https://www.sec.gov/Archives/edgar/data/{accession_cik}/{doc_number}/{accession_number}.txt"
            else:
                # Fallback to .txt file
                base_url = f"https://www.sec.gov/Archives/edgar/data/{accession_cik}/{doc_number}/{accession_number}.txt"
        except:
            # If index fails, try the .txt file directly
            base_url = f"https://www.sec.gov/Archives/edgar/data/{accession_cik}/{doc_number}/{accession_number}.txt"
        
        # Rate limiting
        time.sleep(0.12)
        
        response = session.get(base_url, timeout=30)
        response.raise_for_status()
        
        # Extract text from HTML if needed
        content = response.text
        
        # If it's HTML, try to extract text
        if '<html' in content.lower() or '<body' in content.lower():
            soup = BeautifulSoup(content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            content = soup.get_text()
        
        return content
        
    except Exception as e:
        print(f"⚠️  Error downloading filing {accession_number}: {e}")
        return None


def index_sec_filings(
    database_path: Path,
    ticker_filter: Optional[str] = None,
    filing_type_filter: Optional[str] = None,
    fetch_from_sec: bool = False,
    limit: Optional[int] = None,
):
    """Index SEC filings into vector store."""
    print("📊 Initializing vector store for SEC filings...")
    try:
        vector_store = VectorStore(database_path)
        if not vector_store._available:
            print("❌ Vector store not available. Install: pip install chromadb sentence-transformers")
            return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease install required packages:")
        print("  pip install chromadb sentence-transformers")
        return 1
    
    stats_before = vector_store.sec_collection.count() if vector_store._available else 0
    print(f"📈 Current SEC narratives: {stats_before} documents")
    
    # Check if company_filings table exists
    import sqlite3
    try:
        test_conn = sqlite3.connect(str(database_path))
        test_conn.execute("SELECT 1 FROM company_filings LIMIT 1")
        test_conn.close()
        table_exists = True
    except (sqlite3.OperationalError, sqlite3.DatabaseError):
        table_exists = False
    
    # Fetch filings from database if table exists
    filings = []
    if table_exists:
        try:
            filings = database.fetch_company_filings(
                database_path,
                ticker=ticker_filter,
                form_type=filing_type_filter,
                limit=limit,
            )
        except Exception as e:
            print(f"⚠️  Error fetching from database: {e}")
            filings = []
    
    if not filings:
        if fetch_from_sec:
            print("\n📥 No filings in database. Fetching from SEC API...")
            settings = load_settings()
            try:
                edgar_client = EdgarClient(
                    base_url=settings.edgar_base_url,
                    user_agent=settings.sec_api_user_agent,
                    cache_dir=settings.cache_dir,
                )
                
                # If ticker filter provided, fetch filings for that ticker
                if ticker_filter:
                    print(f"📥 Fetching filings for {ticker_filter} from SEC...")
                    try:
                        # Get CIK for ticker first
                        try:
                            cik = edgar_client.cik_for_ticker(ticker_filter)
                            print(f"   Found CIK: {cik}")
                        except Exception as e:
                            print(f"⚠️  Error looking up CIK for {ticker_filter}: {e}")
                            print("   Make sure the ticker symbol is correct")
                            return 0
                        
                        # Fetch filings - try without form filter first to see what's available
                        forms_to_fetch = None if not filing_type_filter else [filing_type_filter]
                        if not forms_to_fetch:
                            # Try to get 10-K and 10-Q, but don't filter if that fails
                            forms_to_fetch = ["10-K", "10-Q"]
                        
                        print(f"   Fetching forms: {forms_to_fetch}")
                        sec_filings = edgar_client.fetch_filings(
                            ticker_filter,
                            forms=forms_to_fetch,
                            limit=limit or 50,  # Increase limit to get more results
                        )
                        
                        # If no results with form filter, try without filter but then filter manually
                        if not sec_filings and forms_to_fetch:
                            print(f"   No results with form filter, trying without filter...")
                            all_filings = edgar_client.fetch_filings(
                                ticker_filter,
                                forms=None,  # No filter
                                limit=(limit or 50) * 2,  # Get more to filter from
                            )
                            # Filter to only 10-K and 10-Q
                            sec_filings = [f for f in all_filings if f.form_type in ["10-K", "10-Q"]]
                            print(f"   Found {len(all_filings)} total filings, {len(sec_filings)} are 10-K/10-Q")
                        
                        # Final filter to ensure we only have 10-K and 10-Q
                        sec_filings = [f for f in sec_filings if f.form_type in ["10-K", "10-Q"]]
                        
                        print(f"   Retrieved {len(sec_filings)} 10-K/10-Q filings from SEC")
                        
                        # Store in database first (if table exists or we can create it)
                        if sec_filings:
                            try:
                                # Ensure database is initialized (creates tables if needed)
                                database.initialise(database_path)
                                database.bulk_upsert_company_filings(database_path, sec_filings)
                                print(f"✓ Stored {len(sec_filings)} filings in database")
                            except Exception as e:
                                print(f"⚠️  Could not store in database: {e}")
                                print("   Continuing with indexing anyway (filings will be re-fetched if needed)...")
                            
                            # Convert to our format
                            filings = []
                            for f in sec_filings:
                                filings.append({
                                    "cik": f.cik,
                                    "ticker": f.ticker,
                                    "accession_number": f.accession_number,
                                    "form_type": f.form_type,
                                    "filed_at": f.filed_at.isoformat() if f.filed_at else None,
                                    "period_of_report": f.period_of_report.isoformat() if f.period_of_report else None,
                                    "data": f.data,
                                })
                        else:
                            print("⚠️  No filings returned from SEC API")
                            print("   This might mean:")
                            print("   - The ticker has no recent filings")
                            print("   - The SEC API is temporarily unavailable")
                            print("   - Check your internet connection")
                    except Exception as e:
                        print(f"⚠️  Error fetching from SEC: {e}")
                        import traceback
                        traceback.print_exc()
                        print("   Make sure the ticker exists and you have internet connection")
                else:
                    print("⚠️  No ticker specified. Please provide --ticker to fetch from SEC")
            except Exception as e:
                print(f"⚠️  Error initializing SEC client: {e}")
        else:
            print("\n⚠️  No filings found in database.")
            print("   Options:")
            print("   1. Run ingestion scripts first to populate company_filings table")
            print("   2. Use --fetch-from-sec flag to download filings from SEC API")
            print("   3. Specify --ticker to fetch filings for a specific company")
            return 0
    
    if not filings:
        print("❌ No filings to index")
        return 0
    
    print(f"\n📄 Processing {len(filings)} filings...")
    
    settings = load_settings()
    all_documents = []
    processed = 0
    failed = 0
    
    for filing in filings:
        try:
            ticker = filing["ticker"]
            form_type = filing["form_type"]
            accession_number = filing["accession_number"]
            cik = filing["cik"]
            filed_at = filing.get("filed_at")
            
            # Extract fiscal year from period_of_report or filed_at
            fiscal_year = None
            if filing.get("period_of_report"):
                try:
                    # Parse YYYY-MM-DD format
                    period_date = datetime.fromisoformat(filing["period_of_report"].replace('Z', '+00:00'))
                    fiscal_year = period_date.year
                except:
                    pass
            
            if not fiscal_year and filed_at:
                try:
                    filed_date = datetime.fromisoformat(filed_at.replace('Z', '+00:00'))
                    fiscal_year = filed_date.year
                except:
                    pass
            
            if not fiscal_year:
                fiscal_year = datetime.now().year
            
            # Build SEC URL
            clean_cik = cik.lstrip('0') or '0'
            parts = accession_number.split('-')
            if len(parts) == 3:
                sec_url = f"https://www.sec.gov/cgi-bin/viewer?action=view&cik={clean_cik}&accession_number={accession_number}&xbrl_type=v"
            else:
                sec_url = f"https://www.sec.gov/edgar/browse/?CIK={clean_cik}"
            
            # Download filing text
            print(f"  📥 Downloading {ticker} {form_type} ({accession_number})...")
            filing_text = download_filing_text(cik, accession_number, settings.sec_api_user_agent)
            
            if not filing_text:
                print(f"    ⚠️  Could not download filing text, skipping...")
                failed += 1
                continue
            
            print(f"    ✓ Downloaded {len(filing_text):,} characters")
            
            # Extract sections
            sections = extract_sections_from_filing(
                filing_text=filing_text,
                ticker=ticker,
                filing_type=form_type,
                fiscal_year=fiscal_year,
                source_url=sec_url,
                filing_date=filed_at,
            )
            
            if sections:
                all_documents.extend(sections)
                processed += 1
                print(f"    ✓ Extracted {len(sections)} sections")
            else:
                print(f"    ⚠️  No sections extracted (filing text length: {len(filing_text):,} chars)")
                # Check if filing text has expected content
                if "ITEM" in filing_text.upper() or "MANAGEMENT" in filing_text.upper():
                    print(f"    ℹ️  Filing contains 'ITEM' or 'MANAGEMENT' keywords - parser may need adjustment")
                failed += 1
                
        except Exception as e:
            print(f"    ❌ Error processing filing: {e}")
            import traceback
            print(f"    Full error details:")
            traceback.print_exc()
            failed += 1
            continue
    
    # Add all documents to vector store
    if all_documents:
        print(f"\n📦 Indexing {len(all_documents)} document chunks into vector store...")
        count = vector_store.add_sec_documents(all_documents)
        print(f"✓ Successfully indexed {count} document chunks!")
        
        stats_after = vector_store.sec_collection.count() if vector_store._available else 0
        print(f"📊 Total SEC narratives in vector store: {stats_after}")
        print(f"   Processed: {processed} filings, Failed: {failed} filings")
    else:
        print("\n⚠️  No documents to index")
    
    return 0


def index_uploaded_documents(database_path: Path, conversation_id: Optional[str] = None):
    """Index uploaded documents into vector store."""
    print("📊 Initializing vector store for uploaded documents...")
    try:
        vector_store = VectorStore(database_path)
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    # Fetch uploaded documents
    try:
        # Try with limit parameter first
        try:
            documents = database.fetch_uploaded_documents(
                database_path,
                conversation_id,
                limit=1000,  # Get up to 1000 documents
                include_unscoped=True,
            )
        except TypeError:
            # If limit parameter not supported, fetch without it
            documents = database.fetch_uploaded_documents(
                database_path,
                conversation_id,
                include_unscoped=True,
            )
    except Exception as e:
        print(f"❌ Error fetching documents: {e}")
        return 1
    
    if not documents:
        print("ℹ️  No uploaded documents to index")
        return 0
    
    # Convert to vector store format
    all_documents = []
    for doc in documents:
        # Chunk the document
        text = doc.content or ""
        chunk_size = 1500
        chunk_overlap = 200
        
        # Simple chunking
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk.strip())
            start = end - chunk_overlap
            if start >= len(text):
                break
        
        # Create document entries
        for chunk_idx, chunk_text in enumerate(chunks):
            all_documents.append({
                "text": chunk_text,
                "metadata": {
                    "filename": doc.filename,
                    "file_type": doc.file_type or "unknown",
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "conversation_id": conversation_id,
                    "chunk_index": chunk_idx,
                    "total_chunks": len(chunks),
                }
            })
    
    # Add to vector store
    if all_documents:
        print(f"📦 Indexing {len(all_documents)} document chunks...")
        count = vector_store.add_uploaded_documents(all_documents)
        print(f"✓ Successfully indexed {count} document chunks!")
        
        stats_after = vector_store.uploaded_collection.count() if vector_store._available else 0
        print(f"📊 Total uploaded documents in vector store: {stats_after}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(description="Index documents for RAG pipeline")
    parser.add_argument("--database", required=False, type=Path, help="Path to SQLite database (required unless using --list-universes)")
    parser.add_argument("--type", choices=["sec", "uploaded", "all"], default="all", help="What to index")
    parser.add_argument("--ticker", type=str, help="Filter SEC filings by ticker (or use --universe for all)")
    parser.add_argument("--universe", type=str, help="Process all tickers from universe (e.g., sp500, sp1500). Use --list-universes to see available options.")
    parser.add_argument("--list-universes", action="store_true", help="List available ticker universes and exit")
    parser.add_argument("--filing-type", type=str, dest="filing_type", help="Filter SEC filings by type (e.g., 10-K, 10-Q)")
    parser.add_argument("--conversation-id", type=str, help="Filter uploaded docs by conversation")
    parser.add_argument("--fetch-from-sec", action="store_true", help="Fetch filings from SEC API if not in database")
    parser.add_argument("--limit", type=int, help="Limit number of filings per ticker to process")
    parser.add_argument("--max-tickers", type=int, help="Limit number of tickers to process (when using --universe)")
    parser.add_argument("--start-from", type=str, help="Start from this ticker (useful for resuming)")
    
    args = parser.parse_args()
    
    # List universes if requested
    if args.list_universes:
        try:
            from finanlyzeos_chatbot.ticker_universe import available_universes
            if load_ticker_universe is None:
                from finanlyzeos_chatbot.ticker_universe import load_ticker_universe
            universes = available_universes()
            print("Available ticker universes:")
            for u in universes:
                try:
                    tickers = load_ticker_universe(u)
                    print(f"  - {u}: {len(tickers)} tickers")
                except Exception as e:
                    print(f"  - {u}: (error loading - {e})")
            return 0
        except Exception as e:
            print(f"Error listing universes: {e}")
            return 1
    
    if not args.database:
        print("❌ Error: --database is required (unless using --list-universes)")
        print("Use --list-universes to see available ticker universes")
        return 1
    
    if not args.database.exists():
        print(f"❌ Error: Database not found: {args.database}")
        return 1
    
    # Handle universe processing
    if args.universe and args.type in ["sec", "all"]:
        # Import ticker universe loader
        try:
            if load_ticker_universe is None:
                from finanlyzeos_chatbot.ticker_universe import load_ticker_universe as _load_universe
            else:
                _load_universe = load_ticker_universe
        except (ImportError, NameError):
            try:
                from finanlyzeos_chatbot.ticker_universe import load_ticker_universe as _load_universe
            except ImportError:
                print("❌ Error: ticker_universe module not available")
                return 1
        
        print(f"📊 Loading {args.universe.upper()} ticker universe...")
        try:
            all_tickers = _load_universe(args.universe)
            print(f"✓ Loaded {len(all_tickers)} tickers")
            
            # Apply start-from filter if specified
            if args.start_from:
                start_idx = 0
                try:
                    start_idx = all_tickers.index(args.start_from.upper())
                    all_tickers = all_tickers[start_idx:]
                    print(f"✓ Starting from ticker: {args.start_from.upper()} (skipped {start_idx} tickers)")
                except ValueError:
                    print(f"⚠️  Ticker {args.start_from} not found in universe, starting from beginning")
            
            # Apply max-tickers limit if specified
            if args.max_tickers:
                all_tickers = all_tickers[:args.max_tickers]
                print(f"✓ Limited to {len(all_tickers)} tickers")
            
            print(f"\n🚀 Processing {len(all_tickers)} tickers...")
            print("=" * 60)
            
            total_processed = 0
            total_failed = 0
            
            for idx, ticker in enumerate(all_tickers, 1):
                print(f"\n[{idx}/{len(all_tickers)}] Processing {ticker}...")
                print("-" * 60)
                
                try:
                    result = index_sec_filings(
                        args.database,
                        ticker_filter=ticker,
                        filing_type_filter=args.filing_type,
                        fetch_from_sec=args.fetch_from_sec,
                        limit=args.limit,
                    )
                    if result == 0:
                        total_processed += 1
                    else:
                        total_failed += 1
                except KeyboardInterrupt:
                    print("\n\n⚠️  Interrupted by user")
                    print(f"Processed: {total_processed}/{idx-1} tickers")
                    print(f"To resume, use: --start-from {ticker}")
                    return 1
                except Exception as e:
                    print(f"❌ Error processing {ticker}: {e}")
                    total_failed += 1
                    continue
                
                # Small delay between tickers to be respectful to SEC API
                if idx < len(all_tickers):
                    time.sleep(1)
            
            print("\n" + "=" * 60)
            print(f"✅ COMPLETE: Processed {total_processed} tickers, {total_failed} failed")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Error loading ticker universe: {e}")
            return 1
    elif args.type in ["sec", "all"]:
        # Single ticker processing
        index_sec_filings(
            args.database, 
            args.ticker, 
            args.filing_type,
            fetch_from_sec=args.fetch_from_sec,
            limit=args.limit,
        )
    
    if args.type in ["uploaded", "all"] and not args.universe:
        index_uploaded_documents(args.database, args.conversation_id)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

