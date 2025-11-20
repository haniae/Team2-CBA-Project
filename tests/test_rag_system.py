"""
Test RAG System Components

Tests the RAG retriever, vector store, and prompt template to ensure they work correctly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from finanlyzeos_chatbot.rag_retriever import (
    RAGRetriever,
    VectorStore,
    RetrievalResult,
    RetrievedDocument,
)
from finanlyzeos_chatbot.rag_prompt_template import build_rag_prompt


def test_vector_store_initialization(db_path):
    """Test that VectorStore can be initialized."""
    try:
        store = VectorStore(db_path)
        assert store is not None
        print("[PASS] VectorStore initialization: PASSED")
        return True
    except ImportError as e:
        print(f"[WARN] VectorStore requires dependencies: {e}")
        print("   Install with: pip install chromadb sentence-transformers")
        return False
    except Exception as e:
        print(f"[FAIL] VectorStore initialization failed: {e}")
        return False


def test_vector_store_add_documents(db_path):
    """Test adding documents to vector store."""
    
    try:
        store = VectorStore(db_path)
        if not store._available:
            print("[WARN] VectorStore not available (missing dependencies)")
            return False
        
        # Test documents
        test_docs = [
            {
                "text": "Apple's revenue declined in 2023 due to lower iPhone sales in China.",
                "metadata": {
                    "ticker": "AAPL",
                    "filing_type": "10-K",
                    "fiscal_year": 2023,
                    "section": "MD&A",
                    "source_url": "https://sec.gov/test",
                }
            },
            {
                "text": "Microsoft's operating margin improved due to cloud revenue growth.",
                "metadata": {
                    "ticker": "MSFT",
                    "filing_type": "10-K",
                    "fiscal_year": 2023,
                    "section": "MD&A",
                    "source_url": "https://sec.gov/test2",
                }
            }
        ]
        
        count = store.add_sec_documents(test_docs)
        assert count == 2
        print(f"[PASS] Added {count} documents to vector store: PASSED")
        
        # Test search
        results = store.search_sec_narratives("Why did revenue decline?", n_results=2)
        assert len(results) > 0
        print(f"[PASS] Semantic search found {len(results)} results: PASSED")
        
        return True
    except ImportError:
        print("⚠️  VectorStore requires dependencies")
        return False
    except Exception as e:
        print(f"❌ VectorStore add/search failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_retriever_sql_retrieval(db_path, monkeypatch):
    """Test RAG retriever SQL data retrieval."""
    
    # Mock analytics engine
    class MockAnalyticsEngine:
        pass
    
    try:
        retriever = RAGRetriever(db_path, MockAnalyticsEngine())
        
        # Test retrieval (will fail if no data, but should not crash)
        result = retriever.retrieve(
            query="What is Apple's revenue?",
            tickers=["AAPL"],
            use_semantic_search=False,  # Skip semantic search for this test
        )
        
        assert isinstance(result, RetrievalResult)
        assert isinstance(result.metrics, list)
        assert isinstance(result.sec_narratives, list)
        print("[PASS] RAGRetriever.retrieve() returns correct structure: PASSED")
        return True
    except Exception as e:
        print(f"[FAIL] RAGRetriever test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_prompt_template():
    """Test RAG prompt template generation."""
    # Create mock retrieval result
    result = RetrievalResult(
        metrics=[
            {
                "ticker": "AAPL",
                "metric": "revenue",
                "value": 394.3e9,
                "period": "FY2023",
                "source": "database",
            }
        ],
        facts=[],
        sec_narratives=[
            RetrievedDocument(
                text="Revenue declined primarily due to lower iPhone sales in China.",
                source_type="sec_filing",
                metadata={
                    "ticker": "AAPL",
                    "filing_type": "10-K",
                    "fiscal_year": 2023,
                    "section": "MD&A",
                    "source_url": "https://sec.gov/test",
                },
                score=0.92,
            )
        ],
        uploaded_docs=[],
    )
    
    try:
        prompt = build_rag_prompt(
            "Why did Apple's revenue decline?",
            result,
        )
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "Why did Apple's revenue decline?" in prompt
        assert "AAPL" in prompt
        assert "revenue" in prompt.lower()
        print("[PASS] RAG prompt template generation: PASSED")
        print(f"   Prompt length: {len(prompt)} characters")
        return True
    except Exception as e:
        print(f"[FAIL] RAG prompt template failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rag_prompt_with_all_sections():
    """Test RAG prompt with all sections populated."""
    result = RetrievalResult(
        metrics=[
            {"ticker": "AAPL", "metric": "revenue", "value": 394.3e9, "period": "FY2023", "source": "db"},
            {"ticker": "AAPL", "metric": "net_income", "value": 99.8e9, "period": "FY2023", "source": "db"},
        ],
        facts=[],
        sec_narratives=[
            RetrievedDocument(
                text="Revenue declined due to iPhone sales slowdown.",
                source_type="sec_filing",
                metadata={"ticker": "AAPL", "filing_type": "10-K", "fiscal_year": 2023, "section": "MD&A", "source_url": "https://sec.gov/test"},
                score=0.92,
            )
        ],
        uploaded_docs=[
            RetrievedDocument(
                text="Analyst report indicates strong Services growth.",
                source_type="uploaded_doc",
                metadata={"filename": "analyst_report.pdf", "file_type": "pdf", "uploaded_at": "2024-01-01"},
                score=0.85,
            )
        ],
        macro_data={"gdp_growth": "2.5%", "inflation": "3.2%"},
        portfolio_data={"total_value": 1000000, "holdings": ["AAPL", "MSFT"]},
    )
    
    try:
        prompt = build_rag_prompt("Why did revenue decline?", result)
        
        # Check all sections are present
        assert "FINANCIAL METRICS" in prompt
        assert "SEC FILING EXCERPTS" in prompt
        assert "UPLOADED DOCUMENTS" in prompt
        assert "MACROECONOMIC DATA" in prompt
        assert "PORTFOLIO DATA" in prompt
        print("[PASS] RAG prompt with all sections: PASSED")
        return True
    except Exception as e:
        print(f"[FAIL] RAG prompt with all sections failed: {e}")
        return False


def run_all_tests():
    """Run all RAG system tests."""
    import tempfile
    
    print("=" * 70)
    print("RAG SYSTEM TEST SUITE")
    print("=" * 70)
    print()
    
    results = []
    
    # Test 1: Vector Store Initialization
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        # Create parent directory if needed
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()
        results.append(("VectorStore Initialization", test_vector_store_initialization(db_path)))
    
    # Test 2: Vector Store Add/Search
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()
        results.append(("VectorStore Add/Search", test_vector_store_add_documents(db_path)))
    
    # Test 3: RAG Retriever
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.touch()
        results.append(("RAG Retriever", test_rag_retriever_sql_retrieval(db_path, None)))
    
    # Test 4: RAG Prompt Template
    results.append(("RAG Prompt Template", test_rag_prompt_template()))
    
    # Test 5: RAG Prompt with All Sections
    results.append(("RAG Prompt (All Sections)", test_rag_prompt_with_all_sections()))
    
    # Summary
    print()
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All tests passed!")
    elif passed > 0:
        print("[WARN] Some tests passed, but some failed or require dependencies")
    else:
        print("[FAIL] All tests failed or require dependencies")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

