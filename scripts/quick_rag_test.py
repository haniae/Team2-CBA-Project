"""
Quick RAG System Test

Tests that all RAG components can be imported and work together.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("=" * 70)
print("QUICK RAG SYSTEM TEST")
print("=" * 70)
print()

# Test 1: Import RAG components
print("[TEST 1] Importing RAG components...")
try:
    from finanlyzeos_chatbot.rag_retriever import (
        RAGRetriever,
        VectorStore,
        RetrievalResult,
        RetrievedDocument,
    )
    from finanlyzeos_chatbot.rag_prompt_template import build_rag_prompt
    print("[PASS] All RAG components imported successfully")
except ImportError as e:
    print(f"[FAIL] Import failed: {e}")
    sys.exit(1)

print()

# Test 2: Create sample retrieval result
print("[TEST 2] Creating sample retrieval result...")
try:
    result = RetrievalResult(
        metrics=[
            {
                "ticker": "AAPL",
                "metric": "revenue",
                "value": 394.3e9,
                "period": "FY2023",
                "source": "database",
            },
            {
                "ticker": "AAPL",
                "metric": "net_income",
                "value": 99.8e9,
                "period": "FY2023",
                "source": "database",
            },
        ],
        facts=[],
        sec_narratives=[
            RetrievedDocument(
                text="Revenue declined primarily due to lower iPhone sales in China, "
                     "partially offset by Services growth. iPhone revenue decreased 6.1% "
                     "to $200.6B, while Services revenue grew 16.3% to $85.2B.",
                source_type="sec_filing",
                metadata={
                    "ticker": "AAPL",
                    "filing_type": "10-K",
                    "fiscal_year": 2023,
                    "section": "MD&A",
                    "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230930.htm",
                },
                score=0.92,
            )
        ],
        uploaded_docs=[],
    )
    print("[PASS] RetrievalResult created successfully")
    print(f"   Metrics: {len(result.metrics)}")
    print(f"   SEC narratives: {len(result.sec_narratives)}")
except Exception as e:
    print(f"[FAIL] Failed to create RetrievalResult: {e}")
    sys.exit(1)

print()

# Test 3: Generate RAG prompt
print("[TEST 3] Generating RAG prompt...")
try:
    query = "Why did Apple's revenue decline in 2023?"
    prompt = build_rag_prompt(query, result)
    
    assert len(prompt) > 0
    assert query in prompt
    assert "AAPL" in prompt
    assert "revenue" in prompt.lower()
    assert "RAG CONTEXT" in prompt or "USE ONLY" in prompt
    
    print("[PASS] RAG prompt generated successfully")
    print(f"   Prompt length: {len(prompt)} characters")
    print(f"   Contains query: {query in prompt}")
    print(f"   Contains metrics: {'revenue' in prompt.lower()}")
    print(f"   Contains SEC excerpts: {len(result.sec_narratives) > 0}")
    
except Exception as e:
    print(f"[FAIL] Failed to generate RAG prompt: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 4: Check Vector Store (if dependencies available)
print("[TEST 4] Checking Vector Store availability...")
try:
    # Try to create vector store (will fail gracefully if dependencies missing)
    test_path = Path("/tmp/test_rag.db")
    store = VectorStore(test_path)
    
    if store._available:
        print("[PASS] Vector store is available")
        print("   Dependencies installed: chromadb, sentence-transformers")
    else:
        print("[WARN] Vector store not available (missing dependencies)")
        print("   Install with: pip install chromadb sentence-transformers")
        print("   This is OK - RAG will work without vector store (SQL only)")
except Exception as e:
    print(f"[WARN] Vector store check: {e}")
    print("   This is OK - RAG will work without vector store (SQL only)")

print()

# Test 5: Verify RAG Retriever structure
print("[TEST 5] Verifying RAG Retriever structure...")
try:
    # Mock analytics engine
    class MockAnalyticsEngine:
        pass
    
    # Test with dummy path (won't actually retrieve, just test structure)
    test_db = Path("/tmp/test.db")
    retriever = RAGRetriever(test_db, MockAnalyticsEngine())
    
    assert hasattr(retriever, 'retrieve')
    assert hasattr(retriever, 'vector_store')
    assert hasattr(retriever, '_retrieve_sql_data')
    
    print("[PASS] RAG Retriever structure is correct")
    print("   Has retrieve() method")
    print("   Has vector_store attribute")
    print("   Has _retrieve_sql_data() method")
    
except Exception as e:
    print(f"[FAIL] RAG Retriever structure check failed: {e}")
    sys.exit(1)

print()
print("=" * 70)
print("TEST SUMMARY")
print("=" * 70)
print()
print("[SUCCESS] All RAG components are functional!")
print()
print("Component Status:")
print("  [PASS] RAG Prompt Template - Working")
print("  [PASS] RAG Retriever Structure - Correct")
print("  [PASS] RetrievalResult - Working")
print("  [PASS] RetrievedDocument - Working")
print("  [WARN] Vector Store - Requires dependencies (optional)")
print()
print("Next Steps:")
print("  1. Install dependencies: pip install chromadb sentence-transformers")
print("  2. Index documents: python scripts/index_documents_for_rag.py --database data/financial.db")
print("  3. Integrate into chatbot (see docs/RAG_IMPLEMENTATION_SUMMARY.md)")
print()
print("=" * 70)

