#!/usr/bin/env python3
"""Test script to demonstrate chatbot performance improvements."""

import time
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot import FinanlyzeOSChatbot
from finanlyzeos_chatbot.config import load_settings
from finanlyzeos_chatbot.query_classifier import classify_query, QueryComplexity


def test_query_performance(chatbot, query: str, description: str):
    """Test performance of a single query."""
    print(f"\n🧪 Testing: {description}")
    print(f"Query: '{query}'")
    
    # Classify the query
    complexity, query_type, metadata = classify_query(query)
    print(f"Classification: {complexity.value} {query_type.value}")
    print(f"Detected tickers: {metadata.get('tickers', [])}")
    
    # Time the response
    start_time = time.time()
    try:
        response = chatbot.ask(query)
        end_time = time.time()
        
        response_time = end_time - start_time
        print(f"⏱️  Response time: {response_time:.2f} seconds")
        print(f"📝 Response preview: {response[:100]}...")
        
        # Performance rating
        if response_time < 1.0:
            print("🚀 EXCELLENT - Sub-second response!")
        elif response_time < 3.0:
            print("✅ GOOD - Fast response")
        elif response_time < 10.0:
            print("⚠️  ACCEPTABLE - Could be faster")
        else:
            print("❌ SLOW - Needs optimization")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    
    return response_time


def main():
    """Run performance tests."""
    print("🚀 Chatbot Performance Test Suite")
    print("=" * 50)
    
    # Load settings and create chatbot
    print("Loading chatbot...")
    settings = load_settings()
    chatbot = FinanlyzeOSChatbot.create(settings)
    print("✅ Chatbot loaded successfully!")
    
    # Test queries of different complexities
    test_queries = [
        # Simple factual queries (should use fast path)
        ("AAPL revenue", "Simple factual query - Apple revenue"),
        ("What is Tesla's stock price?", "Simple factual query - Tesla price"),
        ("MSFT market cap", "Simple factual query - Microsoft market cap"),
        
        # Medium complexity queries
        ("Compare Apple and Microsoft revenue", "Medium complexity - comparison"),
        ("Show me Google's financial performance", "Medium complexity - analysis"),
        
        # Complex queries (full RAG pipeline)
        ("Analyze Apple's competitive position in the smartphone market and explain the key risks", "Complex analysis query"),
        ("What are the main factors driving Tesla's revenue growth and how do they compare to traditional automakers?", "Complex multi-part query"),
    ]
    
    response_times = []
    
    for query, description in test_queries:
        response_time = test_query_performance(chatbot, query, description)
        if response_time is not None:
            response_times.append(response_time)
        time.sleep(1)  # Brief pause between tests
    
    # Summary statistics
    if response_times:
        print("\n📊 Performance Summary")
        print("=" * 30)
        print(f"Total queries tested: {len(response_times)}")
        print(f"Average response time: {sum(response_times) / len(response_times):.2f} seconds")
        print(f"Fastest response: {min(response_times):.2f} seconds")
        print(f"Slowest response: {max(response_times):.2f} seconds")
        
        # Performance categories
        excellent = sum(1 for t in response_times if t < 1.0)
        good = sum(1 for t in response_times if 1.0 <= t < 3.0)
        acceptable = sum(1 for t in response_times if 3.0 <= t < 10.0)
        slow = sum(1 for t in response_times if t >= 10.0)
        
        print(f"\n🎯 Performance Breakdown:")
        print(f"🚀 Excellent (<1s): {excellent} queries")
        print(f"✅ Good (1-3s): {good} queries")
        print(f"⚠️  Acceptable (3-10s): {acceptable} queries")
        print(f"❌ Slow (>10s): {slow} queries")
        
        if excellent > 0:
            print(f"\n🎉 SUCCESS! {excellent} queries achieved sub-second response times!")
        if sum(response_times) / len(response_times) < 5.0:
            print("🎉 Overall performance is GOOD - average under 5 seconds!")
    
    print("\n✅ Performance testing complete!")


if __name__ == "__main__":
    main()
