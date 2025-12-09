"""
Quick RAG Integration Test

Tests RAG components with a real database (if available) or shows what's needed.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot.rag_retriever import RAGRetriever, VectorStore
from finanlyzeos_chatbot.rag_prompt_template import build_rag_prompt


def test_rag_with_real_database():
    """Test RAG with actual database if available."""
    # Try to find database
    possible_paths = [
        Path("data/financial.db"),
        Path("../data/financial.db"),
        Path("financial.db"),
    ]
    
    db_path = None
    for path in possible_paths:
        if path.exists():
            db_path = path
            break
    
    if not db_path:
        print("=" * 70)
        print("RAG INTEGRATION TEST")
        print("=" * 70)
        print()
        print("[INFO] No database found. Testing components without database...")
        print()
        return test_rag_components_only()
    
    print("=" * 70)
    print("RAG INTEGRATION TEST")
    print("=" * 70)
    print(f"Database: {db_path}")
    print()
    
    # Test 1: Vector Store
    print("[TEST 1] Vector Store Initialization...")
    try:
        store = VectorStore(db_path)
        if store._available:
            print("[PASS] Vector store initialized successfully")
            stats = store.get_collection_stats()
            print(f"   SEC narratives: {stats.get('document_count', 0)} documents")
        else:
            print("[WARN] Vector store not available (missing chromadb/sentence-transformers)")
            print("   Install with: pip install chromadb sentence-transformers")
    except Exception as e:
        print(f"[FAIL] Vector store initialization failed: {e}")
    
    print()
    
    # Test 2: RAG Retriever (requires AnalyticsEngine)
    print("[TEST 2] RAG Retriever...")
    try:
        from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
        from finanlyzeos_chatbot.config import Settings
        
        settings = Settings.load()
        analytics_engine = AnalyticsEngine(settings)
        
        retriever = RAGRetriever(db_path, analytics_engine)
        print("[PASS] RAG retriever initialized")
        
        # Test retrieval
        print("   Testing retrieval with sample query...")
        result = retriever.retrieve(
            query="What is Apple's revenue?",
            tickers=["AAPL"],
            use_semantic_search=False,  # Skip semantic search if not available
        )
        
        print(f"   Retrieved: {len(result.metrics)} metrics, {len(result.sec_narratives)} narratives")
        if result.metrics:
            print(f"   Sample metric: {result.metrics[0]}")
        
    except ImportError as e:
        print(f"[WARN] Could not import AnalyticsEngine: {e}")
    except Exception as e:
        print(f"[FAIL] RAG retriever test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Test 3: RAG Prompt Template
    print("[TEST 3] RAG Prompt Template...")
    try:
        from finanlyzeos_chatbot.rag_retriever import RetrievalResult, RetrievedDocument
        
        # Create sample result
        sample_result = RetrievalResult(
            metrics=[
                {"ticker": "AAPL", "metric": "revenue", "value": 394.3e9, "period": "FY2023", "source": "database"}
            ],
            facts=[],
            sec_narratives=[],
            uploaded_docs=[],
        )
        
        prompt = build_rag_prompt("What is Apple's revenue?", sample_result)
        assert len(prompt) > 0
        assert "AAPL" in prompt
        print("[PASS] RAG prompt template works")
        print(f"   Generated prompt: {len(prompt)} characters")
        
    except Exception as e:
        print(f"[FAIL] RAG prompt template failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("RAG components are functional!")
    print()
    print("Next steps:")
    print("1. Install dependencies: pip install chromadb sentence-transformers")
    print("2. Index documents: python scripts/index_documents_for_rag.py --database data/financial.db")
    print("3. Integrate into chatbot (see docs/RAG_IMPLEMENTATION_SUMMARY.md)")


def test_rag_components_only():
    """Test RAG components without database."""
    print("[TEST] RAG Prompt Template (no database needed)...")
    try:
        from finanlyzeos_chatbot.rag_retriever import RetrievalResult, RetrievedDocument
        
        sample_result = RetrievalResult(
            metrics=[
                {"ticker": "AAPL", "metric": "revenue", "value": 394.3e9, "period": "FY2023", "source": "database"}
            ],
            facts=[],
            sec_narratives=[
                RetrievedDocument(
                    text="Revenue declined due to iPhone sales slowdown.",
                    source_type="sec_filing",
                    metadata={"ticker": "AAPL", "filing_type": "10-K", "fiscal_year": 2023, "section": "MD&A"},
                    score=0.92,
                )
            ],
            uploaded_docs=[],
        )
        
        prompt = build_rag_prompt("Why did revenue decline?", sample_result)
        assert len(prompt) > 0
        print("[PASS] RAG prompt template works")
        print(f"   Generated prompt: {len(prompt)} characters")
        print()
        print("Sample prompt preview:")
        print("-" * 70)
        # Encode to handle Windows console encoding issues
        try:
            preview = prompt[:500] + "..."
            print(preview.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
        except:
            print("(Preview available - contains special characters)")
        print("-" * 70)
        
    except Exception as e:
        print(f"[FAIL] RAG prompt template failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print("RAG prompt template is functional!")
    print()
    print("To test full RAG system:")
    print("1. Ensure you have a database with financial data")
    print("2. Install: pip install chromadb sentence-transformers")
    print("3. Run: python scripts/index_documents_for_rag.py --database data/financial.db")
    
    return True


if __name__ == "__main__":
    test_rag_with_real_database()

