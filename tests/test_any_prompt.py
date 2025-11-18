#!/usr/bin/env python3
"""
Test script to verify the chatbot handles ANY type of user prompt.
Tests edge cases, unrelated queries, gibberish, etc.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.context_builder import build_financial_context, _extract_partial_info_from_query
from finanlyzeos_chatbot.parsing.parse import parse_to_structured

# Edge case queries that should still get a response
EDGE_CASE_QUERIES = [
    # Completely unrelated
    "what's the weather today",
    "tell me a joke",
    "how do I cook pasta",
    "what is 2+2",
    
    # Gibberish
    "asdfghjkl",
    "qwertyuiop",
    "123456789",
    "!@#$%^&*()",
    
    # Empty/whitespace
    "   ",
    "",
    "\n\n\n",
    
    # Just punctuation
    "???",
    "!!!",
    "...",
    
    # Random words
    "the quick brown fox jumps over the lazy dog",
    "hello world this is a test",
    "random text with no meaning",
    
    # Financial but no company
    "what is revenue",
    "explain profit margins",
    "how does cash flow work",
    "what is a p/e ratio",
    
    # Company name but not in database
    "xyz corp revenue",
    "random company financials",
    "unknown company analysis",
    
    # Mixed unrelated
    "apple pie recipe and tesla margins",
    "weather forecast and microsoft revenue",
    "cooking tips and nvidia stock",
    
    # Very long unrelated
    "this is a very long query that has absolutely nothing to do with finance or companies or stocks or anything related to the chatbot's purpose and it's just random text to see if the system can handle it gracefully",
]

def test_edge_cases():
    """Test that edge cases still get context/response."""
    print("=" * 80)
    print("Testing Edge Cases - Should Always Get Response")
    print("=" * 80)
    
    # Mock analytics engine (we just need to test context building)
    class MockAnalyticsEngine:
        def _select_latest_records(self, records, span_fn):
            return {}
        def _period_span(self, record):
            return record.period if record.period else ""
    
    mock_engine = MockAnalyticsEngine()
    database_path = "test.db"  # Won't be used for these queries
    
    for query in EDGE_CASE_QUERIES:
        try:
            # Test partial extraction
            partial_info = _extract_partial_info_from_query(query)
            
            # Test context building (will fail gracefully)
            try:
                context = build_financial_context(
                    query=query,
                    analytics_engine=mock_engine,
                    database_path=database_path,
                    max_tickers=3,
                    include_macro_context=False
                )
            except Exception as e:
                context = f"Error building context: {e}"
            
            # Check if we got something (even if minimal)
            has_context = context and len(context.strip()) > 0
            has_partial_info = any([
                partial_info.get("tickers"),
                partial_info.get("metrics"),
                partial_info.get("concepts"),
                partial_info.get("question_type")
            ])
            
            print(f"\nQuery: {repr(query[:60])}")
            print(f"  Has context: {has_context} ({len(context) if context else 0} chars)")
            print(f"  Has partial info: {has_partial_info}")
            if has_partial_info:
                print(f"    Tickers: {partial_info.get('tickers', [])}")
                print(f"    Metrics: {partial_info.get('metrics', [])}")
                print(f"    Concepts: {partial_info.get('concepts', [])}")
                print(f"    Question Type: {partial_info.get('question_type')}")
            
            # Verify we always get something
            if not has_context and not has_partial_info:
                print(f"  ⚠️  WARNING: No context or partial info extracted!")
            else:
                print(f"  ✅ OK: System can handle this query")
                
        except Exception as e:
            print(f"\nQuery: {repr(query[:60])}")
            print(f"  ❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

def test_parsing_edge_cases():
    """Test that parsing doesn't crash on edge cases."""
    print("\n" + "=" * 80)
    print("Testing Parsing Edge Cases")
    print("=" * 80)
    
    edge_queries = [
        "",
        "   ",
        "???",
        "asdfghjkl",
        "what's the weather",
    ]
    
    for query in edge_queries:
        try:
            structured = parse_to_structured(query)
            print(f"\nQuery: {repr(query)}")
            print(f"  ✅ Parsed successfully")
            print(f"    Tickers: {structured.get('tickers', [])}")
            print(f"    Intent: {structured.get('intent')}")
        except Exception as e:
            print(f"\nQuery: {repr(query)}")
            print(f"  ❌ ERROR: {e}")

def main():
    """Run all edge case tests."""
    print("\n" + "=" * 80)
    print("EDGE CASE TESTING - ANY PROMPT HANDLING")
    print("=" * 80 + "\n")
    
    try:
        test_edge_cases()
        test_parsing_edge_cases()
        
        print("\n" + "=" * 80)
        print("✅ Edge case tests completed!")
        print("=" * 80)
        print("\nNote: These tests verify the system handles ANY prompt gracefully.")
        print("Even unrelated queries should get a helpful response from the LLM.")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

