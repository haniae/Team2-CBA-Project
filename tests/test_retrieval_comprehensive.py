#!/usr/bin/env python3
"""
Comprehensive Data Retrieval Investigation
Tests all failure points in the data retrieval pipeline
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.parsing.parse import parse_to_structured
from finanlyzeos_chatbot import database
from finanlyzeos_chatbot.analytics_engine import AnalyticsEngine
from finanlyzeos_chatbot.context_builder import build_financial_context
from finanlyzeos_chatbot.database import get_connection_pool

def test_ticker_extraction():
    """Test 1: Ticker extraction"""
    print("=" * 80)
    print("TEST 1: TICKER EXTRACTION")
    print("=" * 80)
    
    test_queries = [
        ("what is Apple revenue?", ["AAPL"]),
        ("what is Microsoft revenue?", ["MSFT"]),
        ("what is Tesla revenue?", ["TSLA"]),
        ("what is Google revenue?", ["GOOGL"]),
        ("what is Amazon revenue?", ["AMZN"]),
        ("compare Apple and Microsoft", ["AAPL", "MSFT"]),
        ("why is Tesla margin declining?", ["TSLA"]),
    ]
    
    results = {"pass": 0, "fail": 0}
    for query, expected_tickers in test_queries:
        structured = parse_to_structured(query)
        tickers = [t["ticker"] for t in structured.get("tickers", [])]
        
        if set(tickers) == set(expected_tickers):
            print(f"✅ '{query}' → {tickers}")
            results["pass"] += 1
        else:
            print(f"❌ '{query}' → {tickers} (expected {expected_tickers})")
            results["fail"] += 1
    
    print(f"\nResults: {results['pass']} passed, {results['fail']} failed")
    return results["fail"] == 0

def test_database_access():
    """Test 2: Database access"""
    print("\n" + "=" * 80)
    print("TEST 2: DATABASE ACCESS")
    print("=" * 80)
    
    settings = load_settings()
    db_path = settings.database_path
    
    test_tickers = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN", "META", "NVDA"]
    
    results = {"pass": 0, "fail": 0}
    for ticker in test_tickers:
        try:
            records = database.fetch_metric_snapshots(db_path, ticker)
            revenue_records = [r for r in records if r.metric.lower() == "revenue"]
            
            if len(records) > 0 and len(revenue_records) > 0:
                print(f"✅ {ticker}: {len(records)} records, {len(revenue_records)} revenue records")
                results["pass"] += 1
            else:
                print(f"❌ {ticker}: {len(records)} records, {len(revenue_records)} revenue records")
                results["fail"] += 1
        except Exception as e:
            print(f"❌ {ticker}: Error - {e}")
            results["fail"] += 1
    
    print(f"\nResults: {results['pass']} passed, {results['fail']} failed")
    return results["fail"] == 0

def test_select_latest_records():
    """Test 3: _select_latest_records"""
    print("\n" + "=" * 80)
    print("TEST 3: _SELECT_LATEST_RECORDS")
    print("=" * 80)
    
    settings = load_settings()
    db_path = settings.database_path
    analytics = AnalyticsEngine(settings)
    
    test_tickers = ["AAPL", "MSFT", "TSLA"]
    
    results = {"pass": 0, "fail": 0}
    for ticker in test_tickers:
        try:
            records = database.fetch_metric_snapshots(db_path, ticker)
            latest = analytics._select_latest_records(records, span_fn=analytics._period_span)
            
            if latest and len(latest) > 0:
                has_revenue = "revenue" in latest
                print(f"✅ {ticker}: {len(latest)} metrics selected, revenue={'✅' if has_revenue else '❌'}")
                results["pass"] += 1
            else:
                print(f"❌ {ticker}: No latest records selected (but {len(records)} records exist)")
                results["fail"] += 1
        except Exception as e:
            print(f"❌ {ticker}: Error - {e}")
            results["fail"] += 1
    
    print(f"\nResults: {results['pass']} passed, {results['fail']} failed")
    return results["fail"] == 0

def test_build_financial_context():
    """Test 4: build_financial_context"""
    print("\n" + "=" * 80)
    print("TEST 4: BUILD_FINANCIAL_CONTEXT")
    print("=" * 80)
    
    settings = load_settings()
    db_path = settings.database_path
    analytics = AnalyticsEngine(settings)
    
    test_queries = [
        ("what is Apple revenue?", "AAPL"),
        ("what is Microsoft revenue?", "MSFT"),
        ("what is Tesla revenue?", "TSLA"),
        ("compare Apple and Microsoft", "AAPL"),
    ]
    
    results = {"pass": 0, "fail": 0}
    for query, expected_ticker in test_queries:
        try:
            context = build_financial_context(
                query=query,
                analytics_engine=analytics,
                database_path=str(db_path),
                max_tickers=3
            )
            
            if context and "NO FINANCIAL DATA" not in context:
                print(f"✅ '{query}' → Context built ({len(context)} chars)")
                results["pass"] += 1
            else:
                print(f"❌ '{query}' → No context or 'NO DATA' message")
                if context:
                    print(f"   Context preview: {context[:200]}")
                results["fail"] += 1
        except Exception as e:
            print(f"❌ '{query}': Error - {e}")
            results["fail"] += 1
    
    print(f"\nResults: {results['pass']} passed, {results['fail']} failed")
    return results["fail"] == 0

def test_rag_orchestrator():
    """Test 5: RAG Orchestrator"""
    print("\n" + "=" * 80)
    print("TEST 5: RAG ORCHESTRATOR")
    print("=" * 80)
    
    settings = load_settings()
    db_path = settings.database_path
    analytics = AnalyticsEngine(settings)
    
    try:
        from finanlyzeos_chatbot.rag_orchestrator import RAGOrchestrator
        from finanlyzeos_chatbot.llm import AnthropicClient
        
        llm_client = AnthropicClient(settings)
        rag_orchestrator = RAGOrchestrator(
            database_path=db_path,
            analytics_engine=analytics,
            llm_client=llm_client
        )
        
        test_queries = [
            "what is Apple revenue?",
            "what is Microsoft revenue?",
        ]
        
        results = {"pass": 0, "fail": 0}
        for query in test_queries:
            try:
                rag_prompt, rag_result, rag_metadata = rag_orchestrator.process_query(
                    query=query,
                    conversation_id=None,
                    user_id=None
                )
                
                confidence = rag_metadata.get("confidence", 0.0)
                should_answer = rag_metadata.get("should_answer", True)
                num_metrics = rag_metadata.get("num_metrics", 0)
                num_sec_docs = rag_metadata.get("num_sec_docs", 0)
                
                if should_answer and (num_metrics > 0 or num_sec_docs > 0):
                    print(f"✅ '{query}' → Confidence: {confidence:.2f}, Metrics: {num_metrics}, Docs: {num_sec_docs}")
                    results["pass"] += 1
                else:
                    print(f"❌ '{query}' → Should answer: {should_answer}, Metrics: {num_metrics}, Docs: {num_sec_docs}")
                    results["fail"] += 1
            except Exception as e:
                print(f"❌ '{query}': Error - {e}")
                results["fail"] += 1
        
        print(f"\nResults: {results['pass']} passed, {results['fail']} failed")
        return results["fail"] == 0
    except Exception as e:
        print(f"⚠️  RAG Orchestrator not available: {e}")
        return None

def main():
    print("🔍 COMPREHENSIVE DATA RETRIEVAL INVESTIGATION")
    print("=" * 80)
    print()
    
    results = {}
    results["ticker_extraction"] = test_ticker_extraction()
    results["database_access"] = test_database_access()
    results["select_latest_records"] = test_select_latest_records()
    results["build_financial_context"] = test_build_financial_context()
    results["rag_orchestrator"] = test_rag_orchestrator()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    for test_name, result in results.items():
        if result is None:
            status = "⚠️  N/A"
        elif result:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        print(f"{test_name:30} {status}")
    
    print("\n" + "=" * 80)
    print("FAILURE POINTS IDENTIFIED")
    print("=" * 80)
    
    if not results.get("ticker_extraction", True):
        print("❌ TICKER EXTRACTION: Some queries fail to extract tickers")
    if not results.get("database_access", True):
        print("❌ DATABASE ACCESS: Some companies have no data")
    if not results.get("select_latest_records", True):
        print("❌ _SELECT_LATEST_RECORDS: Returns empty even when records exist")
    if not results.get("build_financial_context", True):
        print("❌ BUILD_FINANCIAL_CONTEXT: Returns 'NO DATA' even when data exists")
    if results.get("rag_orchestrator") is False:
        print("❌ RAG ORCHESTRATOR: Returns low confidence/empty retrieval")

if __name__ == "__main__":
    main()

