"""Test various user query patterns to check detection coverage."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.finanlyzeos_chatbot.parsing.parse import parse_to_structured

def test_query_patterns():
    """Test various query patterns."""
    print("=" * 80)
    print("Query Pattern Detection Test")
    print("=" * 80)
    
    test_cases = [
        # Basic question patterns
        ("What is Apple's revenue?", "Basic question"),
        ("What's Apple's revenue?", "Contraction"),
        ("How is Apple doing?", "How question"),
        ("Show me Apple's revenue", "Command"),
        ("Tell me about Apple", "Request"),
        
        # Spelling mistakes
        ("What is Appel's revenue?", "Company spelling mistake"),
        ("Show me revenu for Apple", "Metric spelling mistake"),
        
        # Intent patterns
        ("Compare Apple and Microsoft", "Compare intent"),
        ("What is Apple's revenue trend?", "Trend intent"),
        ("Which company has highest revenue?", "Rank intent"),
        ("Explain Apple's revenue", "Explain intent"),
        ("Why is Apple's revenue high?", "Why intent"),
        ("What if Apple's revenue doubles?", "What-if intent"),
        ("How does revenue relate to profit?", "Relationship intent"),
        ("How does Apple compare to industry?", "Benchmark intent"),
        ("When did Apple report?", "When intent"),
        
        # Variations
        ("Apple revenue", "Minimal query"),
        ("Revenue for Apple", "Reversed order"),
        ("What was Apple's revenue last quarter?", "Temporal"),
        ("Apple vs Microsoft revenue", "Comparison shorthand"),
        ("Top 5 companies by revenue", "Ranking query"),
        
        # Complex patterns
        ("How has Apple's revenue changed over the past year?", "Complex trend"),
        ("What are Apple's key metrics?", "Summary query"),
        ("Is Apple more profitable than Microsoft?", "Comparison question"),
        ("Calculate Apple's P/E ratio", "Calculation request"),
        ("Find companies with revenue > 100B", "Filter query"),
        
        # Edge cases
        ("Revenue", "Just metric"),
        ("AAPL", "Just ticker"),
        ("Apple", "Just company"),
        ("What is the revenue?", "Missing company"),
        ("Who has the highest revenue?", "Who question"),
        
        # Multiple companies/metrics
        ("Apple and Microsoft revenue", "Multiple companies"),
        ("Apple revenue and profit", "Multiple metrics"),
        
        # Portfolio queries (should be detected but not trigger ticker resolution)
        ("What's my portfolio risk?", "Portfolio query"),
        ("Show my portfolio", "Portfolio command"),
    ]
    
    results = {"passed": 0, "failed": 0, "warnings": 0}
    
    print("\nTesting Query Patterns:\n")
    
    for query, description in test_cases:
        try:
            parsed = parse_to_structured(query)
            
            # Check if query was parsed
            has_intent = parsed.get("intent") and parsed["intent"] != "unknown"
            has_tickers = len(parsed.get("vtickers", [])) > 0
            has_metrics = len(parsed.get("vmetrics", [])) > 0
            has_periods = len(parsed.get("vperiods", [])) > 0
            
            # For portfolio queries, we expect no tickers
            is_portfolio = "portfolio" in query.lower()
            if is_portfolio:
                if not has_tickers:
                    status = "[PASS]"
                    results["passed"] += 1
                else:
                    status = "[WARN]"
                    results["warnings"] += 1
            # For queries with just metric or ticker, that's okay
            elif description in ["Just metric", "Just ticker", "Just company"]:
                if has_metrics or has_tickers or has_intent:
                    status = "[PASS]"
                    results["passed"] += 1
                else:
                    status = "[WARN]"
                    results["warnings"] += 1
            # For other queries, we expect at least intent or some extraction
            else:
                if has_intent or has_tickers or has_metrics:
                    status = "[PASS]"
                    results["passed"] += 1
                else:
                    status = "[FAIL]"
                    results["failed"] += 1
            
            print(f"  {status} {description:30} | Query: {query[:50]}")
            if status == "[FAIL]":
                print(f"      Intent: {parsed.get('intent')}, Tickers: {len(parsed.get('vtickers', []))}, "
                      f"Metrics: {len(parsed.get('vmetrics', []))}")
        
        except Exception as e:
            print(f"  [ERROR] {description:30} | Query: {query[:50]}")
            print(f"      Error: {str(e)[:100]}")
            results["failed"] += 1
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    total = results["passed"] + results["failed"] + results["warnings"]
    print(f"Passed: {results['passed']}/{total} ({results['passed']*100/total:.1f}%)")
    print(f"Failed: {results['failed']}/{total} ({results['failed']*100/total:.1f}%)")
    print(f"Warnings: {results['warnings']}/{total} ({results['warnings']*100/total:.1f}%)")
    
    if results["passed"] / total >= 0.80:
        print("\n[SUCCESS] Query pattern detection is working well!")
    elif results["passed"] / total >= 0.60:
        print("\n[INFO] Query pattern detection needs some improvement")
    else:
        print("\n[WARNING] Query pattern detection needs significant improvement")

if __name__ == "__main__":
    test_query_patterns()

