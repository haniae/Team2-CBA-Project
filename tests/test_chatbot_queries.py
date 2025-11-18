#!/usr/bin/env python3
"""
Comprehensive test script to verify chatbot handles all query types well.
Tests actual chatbot responses, not just parsing.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test queries organized by category
TEST_QUERIES = {
    "Simple & Direct": [
        "apple revenue",
        "tesla margins",
        "microsoft cash",
        "nvidia profit",
    ],
    
    "With Typos": [
        "microsft revenu",
        "appl margens",
        "nvida profit",
        "googl earnings",
    ],
    
    "Conversational": [
        "how's apple doing",
        "what's up with tesla",
        "is microsoft good",
        "tell me about nvidia",
    ],
    
    "Comparisons": [
        "apple vs microsoft",
        "which is better apple or microsoft",
        "compare apple microsoft google",
    ],
    
    "Why Questions": [
        "why did tesla margins drop",
        "what caused apple revenue to drop",
        "why is nvidia expensive",
    ],
    
    "Forecasting": [
        "forecast apple revenue",
        "what will tesla revenue be next year",
        "nvidia outlook",
    ],
    
    "Complex Multi-Part": [
        "can you show me apple's revenue growth over the last five years and compare it to microsoft",
        "why did tesla's margins drop in 2023 and what does that mean for investors",
        "analyze nvidia's financial health including revenue margins cash flow and valuation",
    ],
    
    "Unrelated Queries": [
        "what's the weather",
        "tell me a joke",
        "how do I cook pasta",
    ],
    
    "Financial Concepts (No Company)": [
        "what is revenue",
        "explain profit margins",
        "how does cash flow work",
    ],
    
    "Edge Cases": [
        "",
        "???",
        "asdfghjkl",
    ],
}

def test_chatbot_query(category: str, query: str, chatbot):
    """Test a single query with the chatbot."""
    print(f"\n{'='*80}")
    print(f"Category: {category}")
    print(f"Query: {repr(query)}")
    print(f"{'='*80}")
    
    try:
        # Get response from chatbot
        response = chatbot.ask(query)
        
        # Analyze response quality
        has_response = response and len(response.strip()) > 0
        response_length = len(response) if response else 0
        
        print(f"\nOK: Response received ({response_length} chars)")
        
        # Check for error indicators
        error_indicators = [
            "i don't understand",
            "i cannot",
            "i can't",
            "unable to",
            "error",
            "failed",
        ]
        
        has_errors = any(indicator in response.lower() for indicator in error_indicators)
        
        if has_errors:
            print(f"WARNING: Response may contain error indicators")
        else:
            print(f"OK: No error indicators found")
        
        # Check if response is helpful (not too short)
        if response_length < 50:
            print(f"WARNING: Response is quite short ({response_length} chars)")
        else:
            print(f"OK: Response length is adequate")
        
        # Show preview
        preview = response[:200] if response else "No response"
        print(f"\nResponse preview:\n{preview}...")
        
        return {
            "success": True,
            "has_response": has_response,
            "response_length": response_length,
            "has_errors": has_errors,
            "is_helpful": response_length >= 50,
        }
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
        }

def run_comprehensive_tests():
    """Run comprehensive tests on the chatbot."""
    print("\n" + "="*80)
    print("COMPREHENSIVE CHATBOT QUERY TESTING")
    print("="*80)
    
    # Initialize chatbot
    print("\nInitializing chatbot...")
    try:
        from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
        from finanlyzeos_chatbot.config import Settings
        
        # Try to load settings
        settings = Settings()
        chatbot = FinanlyzeOSChatbot.create(settings)
        print("OK: Chatbot initialized successfully")
    except Exception as e:
        print(f"ERROR: Failed to initialize chatbot: {e}")
        print("\nNote: Make sure your database is set up and settings are configured.")
        return
    
    # Run tests
    results = {}
    total_tests = 0
    passed_tests = 0
    
    for category, queries in TEST_QUERIES.items():
        category_results = []
        for query in queries:
            total_tests += 1
            result = test_chatbot_query(category, query, chatbot)
            category_results.append(result)
            
            if result.get("success") and result.get("has_response") and not result.get("has_errors"):
                passed_tests += 1
        
        results[category] = category_results
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\nTotal queries tested: {total_tests}")
    print(f"Successful responses: {passed_tests}")
    print(f"Success rate: {passed_tests/total_tests*100:.1f}%")
    
    print("\n" + "-"*80)
    print("Category Breakdown:")
    print("-"*80)
    
    for category, category_results in results.items():
        category_passed = sum(1 for r in category_results if r.get("success") and r.get("has_response") and not r.get("has_errors"))
        category_total = len(category_results)
        print(f"\n{category}: {category_passed}/{category_total} passed")
        
        # Show any failures
        for i, result in enumerate(category_results):
            if not result.get("success") or not result.get("has_response") or result.get("has_errors"):
                query = TEST_QUERIES[category][i]
                print(f"  FAILED: {repr(query)}")
                if result.get("error"):
                    print(f"     Error: {result['error']}")
    
    print("\n" + "="*80)
    print("Testing complete!")
    print("="*80)
    print("\nRecommendations:")
    if passed_tests == total_tests:
        print("SUCCESS: All queries handled successfully!")
    else:
        print(f"WARNING: {total_tests - passed_tests} queries need attention")
        print("   - Check responses for error messages")
        print("   - Verify context building is working")
        print("   - Ensure LLM is being called with proper context")

def quick_test():
    """Quick test with a few key queries."""
    print("\n" + "="*80)
    print("QUICK TEST - Key Queries")
    print("="*80)
    
    try:
        from finanlyzeos_chatbot.chatbot import FinanlyzeOSChatbot
        from finanlyzeos_chatbot.config import Settings
        
        settings = Settings()
        chatbot = FinanlyzeOSChatbot.create(settings)
        
        quick_queries = [
            "apple revenue",
            "microsft revenu",  # Typo
            "how's apple doing",  # Conversational
            "apple vs microsoft",  # Comparison
            "what's the weather",  # Unrelated
        ]
        
        for query in quick_queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print(f"{'='*60}")
            try:
                response = chatbot.ask(query)
                print(f"Response ({len(response)} chars): {response[:300]}...")
                print("✅ Success")
            except Exception as e:
                print(f"❌ Error: {e}")
        
    except Exception as e:
        print(f"❌ Failed to initialize: {e}")

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test chatbot query handling")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Run quick test with key queries only"
    )
    
    args = parser.parse_args()
    
    if args.quick:
        quick_test()
    else:
        run_comprehensive_tests()

if __name__ == "__main__":
    main()

