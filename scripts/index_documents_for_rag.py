"""
Index documents for RAG Pipeline

This script indexes:
1. SEC filings (narratives) into vector store
2. Uploaded documents into vector store

Run this after ingesting new SEC filings or when users upload documents.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot.rag_retriever import VectorStore
from finanlyzeos_chatbot.sec_filing_parser import extract_sections_from_filing
from finanlyzeos_chatbot import database


def index_sec_filings(
    database_path: Path,
    ticker_filter: Optional[str] = None,
    filing_type_filter: Optional[str] = None,
):
    """Index SEC filings into vector store."""
    print("📊 Initializing vector store for SEC filings...")
    try:
        vector_store = VectorStore(database_path)
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nPlease install required packages:")
        print("  pip install chromadb sentence-transformers")
        return 1
    
    stats_before = vector_store.sec_collection.count() if vector_store._available else 0
    print(f"📈 Current SEC narratives: {stats_before} documents")
    
    # TODO: Implement based on your database schema
    # Example:
    # filings = database.fetch_sec_filings(database_path, ticker=ticker_filter, filing_type=filing_type_filter)
    # all_documents = []
    # for filing in filings:
    #     sections = extract_sections_from_filing(...)
    #     all_documents.extend(sections)
    # vector_store.add_sec_documents(all_documents)
    
    print("\n⚠️  NOTE: Implement database.fetch_sec_filings() based on your schema")
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
    parser.add_argument("--database", required=True, type=Path, help="Path to SQLite database")
    parser.add_argument("--type", choices=["sec", "uploaded", "all"], default="all", help="What to index")
    parser.add_argument("--ticker", type=str, help="Filter SEC filings by ticker")
    parser.add_argument("--filing-type", type=str, dest="filing_type", help="Filter SEC filings by type")
    parser.add_argument("--conversation-id", type=str, help="Filter uploaded docs by conversation")
    
    args = parser.parse_args()
    
    if not args.database.exists():
        print(f"❌ Error: Database not found: {args.database}")
        return 1
    
    if args.type in ["sec", "all"]:
        index_sec_filings(args.database, args.ticker, args.filing_type)
    
    if args.type in ["uploaded", "all"]:
        index_uploaded_documents(args.database, args.conversation_id)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

