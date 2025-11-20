"""
Test script for advanced RAG features: reranking, observability, multi-hop
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.finanlyzeos_chatbot.rag_retriever import RAGRetriever
from src.finanlyzeos_chatbot.rag_reranker import Reranker
from src.finanlyzeos_chatbot.rag_observability import RAGObserver, RAGGuardrails
from src.finanlyzeos_chatbot.rag_controller import RAGController
from src.finanlyzeos_chatbot.rag_prompt_template import build_rag_prompt
from src.finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
from src.finanlyzeos_chatbot.config import Settings
from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured

def test_reranking():
    """Test reranking functionality."""
    print("\n" + "="*60)
    print("TEST 1: Reranking")
    print("="*60)
    
    db_path = Path("data/test_chatbot.db")
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return False
    
    settings = Settings(database_path=db_path)
    analytics_engine = AnalyticsEngine(settings)
    retriever = RAGRetriever(db_path, analytics_engine)
    
    # Initialize reranker
    reranker = Reranker(use_reranking=True)
    print(f"Reranker initialized: {reranker.use_reranking}")
    
    # Test query
    query = "What is Apple's revenue?"
    tickers = ["AAPL"]
    
    print(f"\nQuery: {query}")
    print(f"Tickers: {tickers}")
    
    # Retrieve without reranking
    print("\n--- Retrieval WITHOUT reranking ---")
    result_no_rerank = retriever.retrieve(
        query=query,
        tickers=tickers,
        use_reranking=False,
    )
    print(f"SEC docs: {len(result_no_rerank.sec_narratives)}")
    print(f"Uploaded docs: {len(result_no_rerank.uploaded_docs)}")
    if result_no_rerank.sec_narratives:
        print(f"Top SEC score: {result_no_rerank.sec_narratives[0].score}")
    
    # Retrieve with reranking
    print("\n--- Retrieval WITH reranking ---")
    result_rerank = retriever.retrieve(
        query=query,
        tickers=tickers,
        use_reranking=True,
        reranker=reranker,
    )
    print(f"SEC docs: {len(result_rerank.sec_narratives)}")
    print(f"Uploaded docs: {len(result_rerank.uploaded_docs)}")
    if result_rerank.sec_narratives:
        print(f"Top SEC score: {result_rerank.sec_narratives[0].score}")
    
    print("\n✅ Reranking test completed")
    return True


def test_observability():
    """Test observability and guardrails."""
    print("\n" + "="*60)
    print("TEST 2: Observability & Guardrails")
    print("="*60)
    
    db_path = Path("data/test_chatbot.db")
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return False
    
    settings = Settings(database_path=db_path)
    analytics_engine = AnalyticsEngine(settings)
    retriever = RAGRetriever(db_path, analytics_engine)
    
    # Initialize observer with guardrails
    guardrails = RAGGuardrails(
        min_relevance_score=0.3,
        max_context_chars=15000,
        max_documents=10,
    )
    observer = RAGObserver(guardrails)
    
    # Test query
    query = "Why did revenue decline?"
    tickers = ["AAPL"]
    
    print(f"\nQuery: {query}")
    print(f"Guardrails: min_score={guardrails.min_relevance_score}, max_docs={guardrails.max_documents}")
    
    # Retrieve with observer
    result = retriever.retrieve(
        query=query,
        tickers=tickers,
        use_reranking=True,
        observer=observer,
    )
    
    # Get metrics
    metrics = observer.metrics[-1] if observer.metrics else None
    if metrics:
        print(f"\n--- Retrieval Metrics ---")
        print(f"SEC docs: {metrics.num_sec_docs}")
        print(f"Uploaded docs: {metrics.num_uploaded_docs}")
        print(f"Metrics: {metrics.num_metrics}")
        print(f"Retrieval time: {metrics.retrieval_time_ms:.1f}ms")
        print(f"Reranking time: {metrics.reranking_time_ms:.1f}ms")
        print(f"Low score warning: {metrics.low_score_warning}")
        print(f"Empty retrieval: {metrics.empty_retrieval}")
        if metrics.sec_scores:
            print(f"SEC scores: {[f'{s:.3f}' for s in metrics.sec_scores[:3]]}")
    
    # Get summary stats
    stats = observer.get_summary_stats()
    print(f"\n--- Summary Stats ---")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: {value:.3f}")
        else:
            print(f"{key}: {value}")
    
    print("\n✅ Observability test completed")
    return True


def test_multi_hop():
    """Test multi-hop RAG controller."""
    print("\n" + "="*60)
    print("TEST 3: Multi-Hop RAG Controller")
    print("="*60)
    
    db_path = Path("data/test_chatbot.db")
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return False
    
    settings = Settings(database_path=db_path)
    analytics_engine = AnalyticsEngine(settings)
    retriever = RAGRetriever(db_path, analytics_engine)
    controller = RAGController(retriever)
    
    # Complex query
    query = "Why did Apple's revenue decline, and what's the economic context?"
    tickers = ["AAPL"]
    
    print(f"\nQuery: {query}")
    
    # Decompose query
    decomposed = controller.decompose_query(query, tickers)
    print(f"\nComplexity: {decomposed.complexity.value}")
    print(f"Steps: {len(decomposed.steps)}")
    for step in decomposed.steps:
        print(f"  Step {step.step_number}: {step.retrieval_type} - {step.sub_query[:50]}...")
    
    # Execute multi-hop
    result = controller.execute_multi_hop(
        query=query,
        tickers=tickers,
        max_steps=5,
        use_reranking=True,
    )
    
    print(f"\n--- Multi-Hop Results ---")
    print(f"Metrics: {len(result.metrics)}")
    print(f"SEC narratives: {len(result.sec_narratives)}")
    print(f"Uploaded docs: {len(result.uploaded_docs)}")
    
    print("\n✅ Multi-hop test completed")
    return True


def test_full_pipeline():
    """Test full RAG pipeline with all features."""
    print("\n" + "="*60)
    print("TEST 4: Full RAG Pipeline")
    print("="*60)
    
    db_path = Path("data/test_chatbot.db")
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return False
    
    settings = Settings(database_path=db_path)
    analytics_engine = AnalyticsEngine(settings)
    retriever = RAGRetriever(db_path, analytics_engine)
    reranker = Reranker(use_reranking=True)
    guardrails = RAGGuardrails(min_relevance_score=0.2)  # Lower threshold for testing
    observer = RAGObserver(guardrails)
    
    # Parse query
    query = "What is Apple's revenue and why did it change?"
    structured = parse_to_structured(query)
    tickers = [t["ticker"] for t in structured.get("tickers", [])][:3]
    
    if not tickers:
        tickers = ["AAPL"]  # Fallback for testing
    
    print(f"\nQuery: {query}")
    print(f"Parsed tickers: {tickers}")
    
    # Retrieve with all features
    result = retriever.retrieve(
        query=query,
        tickers=tickers,
        use_reranking=True,
        reranker=reranker,
        observer=observer,
    )
    
    # Build prompt
    prompt = build_rag_prompt(query, result)
    
    print(f"\n--- Pipeline Results ---")
    print(f"Metrics: {len(result.metrics)}")
    print(f"SEC narratives: {len(result.sec_narratives)}")
    print(f"Uploaded docs: {len(result.uploaded_docs)}")
    print(f"Prompt length: {len(prompt)} chars")
    
    # Show prompt preview
    print(f"\n--- Prompt Preview (first 500 chars) ---")
    print(prompt[:500] + "...")
    
    # Show metrics
    if observer.metrics:
        metrics = observer.metrics[-1]
        print(f"\n--- Metrics ---")
        print(f"Retrieval time: {metrics.retrieval_time_ms:.1f}ms")
        print(f"Reranking time: {metrics.reranking_time_ms:.1f}ms")
        print(f"Total time: {metrics.retrieval_time_ms + metrics.reranking_time_ms:.1f}ms")
    
    print("\n✅ Full pipeline test completed")
    return True


def main():
    """Run all tests."""
    print("="*60)
    print("ADVANCED RAG FEATURES TEST SUITE")
    print("="*60)
    
    tests = [
        ("Reranking", test_reranking),
        ("Observability", test_observability),
        ("Multi-Hop Controller", test_multi_hop),
        ("Full Pipeline", test_full_pipeline),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} test failed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{name:30s}: {status}")
    
    all_passed = all(result for _, result in results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())

