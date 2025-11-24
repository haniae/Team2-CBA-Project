"""Check vector database contents and statistics"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from finanlyzeos_chatbot.rag_retriever import VectorStore


def check_vector_db(database_path: Path = None, show_samples: bool = True):
    """
    Check vector database contents and display statistics.
    
    Args:
        database_path: Path to database (default: data/financial.db)
        show_samples: Whether to show sample documents
    """
    if database_path is None:
        database_path = Path("data/financial.db")
    
    print("=" * 80)
    print("VECTOR DATABASE STATUS CHECK")
    print("=" * 80)
    print(f"Database: {database_path}")
    print()
    
    try:
        vector_store = VectorStore(database_path)
        if not vector_store._available:
            print("⚠️  Vector store not available")
            print("   Install: pip install chromadb sentence-transformers")
            return
        
        # Get counts for all collections
        counts = {}
        try:
            counts['sec'] = vector_store.sec_collection.count()
        except:
            counts['sec'] = 0
        
        try:
            counts['uploaded'] = vector_store.uploaded_collection.count()
        except:
            counts['uploaded'] = 0
        
        try:
            counts['earnings'] = vector_store.earnings_collection.count()
        except:
            counts['earnings'] = 0
        
        try:
            counts['news'] = vector_store.news_collection.count()
        except:
            counts['news'] = 0
        
        try:
            counts['analyst'] = vector_store.analyst_collection.count()
        except:
            counts['analyst'] = 0
        
        try:
            counts['press'] = vector_store.press_collection.count()
        except:
            counts['press'] = 0
        
        try:
            counts['industry'] = vector_store.industry_collection.count()
        except:
            counts['industry'] = 0
        
        try:
            counts['portfolio'] = vector_store.portfolio_spreadsheets_collection.count()
        except:
            counts['portfolio'] = 0
        
        # Display statistics
        print("📊 Document Counts by Collection:")
        print("-" * 80)
        print(f"  ✅ SEC narratives:           {counts['sec']:>10,} documents")
        print(f"  ✅ Uploaded documents:       {counts['uploaded']:>10,} documents")
        print(f"  ✅ Earnings transcripts:     {counts['earnings']:>10,} documents")
        print(f"  ✅ Financial news:            {counts['news']:>10,} documents")
        print(f"  ✅ Analyst reports:           {counts['analyst']:>10,} documents")
        print(f"  ✅ Press releases:           {counts['press']:>10,} documents")
        print(f"  ✅ Industry research:        {counts['industry']:>10,} documents")
        print(f"  ✅ Portfolio spreadsheets:   {counts['portfolio']:>10,} documents")
        print("-" * 80)
        
        total = sum(counts.values())
        print(f"  📈 TOTAL:                    {total:>10,} documents")
        print()
        
        # Calculate storage size
        try:
            import os
            chroma_db_path = database_path.parent / "chroma_db"
            if chroma_db_path.exists():
                total_size = sum(
                    os.path.getsize(os.path.join(dirpath, filename))
                    for dirpath, dirnames, filenames in os.walk(chroma_db_path)
                    for filename in filenames
                )
                size_mb = total_size / (1024 * 1024)
                print(f"  💾 Storage Size:             {size_mb:>10.2f} MB")
                print()
        except:
            pass
        
        # Show sample documents
        if show_samples:
            print("📄 Sample Documents:")
            print("-" * 80)
            
            # SEC narratives sample
            if counts['sec'] > 0:
                try:
                    sample = vector_store.sec_collection.peek(limit=2)
                    if sample.get('metadatas'):
                        print("  SEC Narratives:")
                        for i, meta in enumerate(sample['metadatas'][:2], 1):
                            ticker = meta.get('ticker', 'N/A')
                            section = meta.get('section', 'N/A')
                            filing_type = meta.get('filing_type', 'N/A')
                            print(f"    {i}. {ticker} - {section} ({filing_type})")
                except:
                    pass
            
            # Earnings transcripts sample
            if counts['earnings'] > 0:
                try:
                    sample = vector_store.earnings_collection.peek(limit=1)
                    if sample.get('metadatas'):
                        print("  Earnings Transcripts:")
                        for meta in sample['metadatas'][:1]:
                            ticker = meta.get('ticker', 'N/A')
                            date = meta.get('date', 'N/A')
                            quarter = meta.get('quarter', '')
                            print(f"    • {ticker} - {quarter} ({date})")
                except:
                    pass
            
            # News sample
            if counts['news'] > 0:
                try:
                    sample = vector_store.news_collection.peek(limit=1)
                    if sample.get('metadatas'):
                        print("  Financial News:")
                        for meta in sample['metadatas'][:1]:
                            ticker = meta.get('ticker', 'N/A')
                            title = meta.get('title', 'N/A')[:50]
                            date = meta.get('date', 'N/A')
                            print(f"    • {ticker} - {title}... ({date})")
                except:
                    pass
        
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check vector database contents and statistics")
    parser.add_argument("--database", type=Path, help="Path to database (default: data/financial.db)")
    parser.add_argument("--no-samples", action="store_true", help="Don't show sample documents")
    
    args = parser.parse_args()
    
    db_path = args.database if args.database else Path("data/financial.db")
    
    if not db_path.exists():
        print(f"❌ Error: Database not found: {db_path}")
        sys.exit(1)
    
    check_vector_db(db_path, show_samples=not args.no_samples)

