"""Test edge cases for metric name matching - typos, extra spaces, punctuation, etc."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from finanlyzeos_chatbot.parsing.parse import resolve_metrics, normalize

def test_edge_cases():
    """Test edge cases that users might encounter."""
    
    # Edge case test scenarios
    edge_cases = [
        # Extra spaces
        ("What is Apple's net  income?", "net_income"),  # Double space
        ("What is Apple's revenue   growth?", "revenue_growth"),  # Triple space
        ("What is Apple's free   cash   flow?", "free_cash_flow"),  # Multiple spaces
        
        # Mixed punctuation and spacing
        ("What is Apple's price-to-earnings?", "pe_ratio"),  # Hyphenated
        ("What is Apple's price to earnings?", "pe_ratio"),  # Space separated
        ("What is Apple's price/earnings?", "pe_ratio"),  # Slash
        ("What is Apple's P/E?", "pe_ratio"),  # Abbreviation with slash
        
        # Case variations in context
        ("What is Apple's REVENUE?", "revenue"),  # All caps
        ("What is Apple's Revenue?", "revenue"),  # Title case
        ("What is Apple's revenue?", "revenue"),  # Lowercase
        ("What is Apple's ReVeNuE?", "revenue"),  # Mixed case
        
        # Compound words
        ("What is Apple's netincome?", "net_income"),  # No space
        ("What is Apple's marketcap?", "market_cap"),  # No space
        ("What is Apple's grossprofit?", "gross_profit"),  # No space
        ("What is Apple's workingcapital?", "working_capital"),  # No space
        
        # Abbreviations with various formats
        ("What is Apple's P E?", "pe_ratio"),  # Space separated abbreviation
        ("What is Apple's P/E?", "pe_ratio"),  # Slash separated
        ("What is Apple's PE?", "pe_ratio"),  # No separator
        ("What is Apple's P-B?", "pb_ratio"),  # Hyphen
        ("What is Apple's P B?", "pb_ratio"),  # Space
        ("What is Apple's P/B?", "pb_ratio"),  # Slash
        
        # With apostrophes and possessives
        ("What is Apple's revenue?", "revenue"),  # Standard possessive
        ("What is Apples revenue?", "revenue"),  # No apostrophe
        ("What is the revenue of Apple?", "revenue"),  # Different structure
        
        # Multiple metrics in one query
        ("What is Apple's revenue and profit?", "revenue"),  # Should find revenue
        ("What is Apple's revenue and net income?", "revenue"),  # Should find revenue
        
        # Natural language variations
        ("How much revenue does Apple make?", "revenue"),
        ("What's Apple's revenue?", "revenue"),  # Contraction
        ("What is Apples revenue?", "revenue"),  # No apostrophe
        ("Show me Apple revenue", "revenue"),  # Different query structure
        
        # With numbers and units
        ("What is Apple's revenue in billions?", "revenue"),
        ("What is Apple's P/E ratio?", "pe_ratio"),
        ("What is Apple's PE ratio?", "pe_ratio"),
        
        # Hyphenated vs spaced
        ("What is Apple's debt-to-equity?", "debt_equity"),
        ("What is Apple's debt to equity?", "debt_equity"),
        ("What is Apple's debt/equity?", "debt_equity"),
        
        # Common abbreviations
        ("What is Apple's FCF?", "free_cash_flow"),
        ("What is Apple's fcf?", "free_cash_flow"),
        ("What is Apple's EBITDA?", "ebitda"),
        ("What is Apple's ebitda?", "ebitda"),
        ("What is Apple's ROE?", "roe"),
        ("What is Apple's roe?", "roe"),
        
        # With "the" article
        ("What is the revenue of Apple?", "revenue"),
        ("What is the net income of Apple?", "net_income"),
        ("What is the P/E of Apple?", "pe_ratio"),
    ]
    
    print("=" * 80)
    print("Testing Metric Name Edge Cases")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    failures = []
    
    for query, expected_metric_id in edge_cases:
        # Normalize and resolve
        normalized = normalize(query)
        matches = resolve_metrics(query, normalized)
        
        # Check if we found the expected metric
        found_metric = None
        if matches:
            for match in matches:
                if match.get("metric_id") == expected_metric_id:
                    found_metric = match.get("metric_id")
                    break
        
        if found_metric == expected_metric_id:
            print(f"[PASS] '{query}' -> {expected_metric_id}")
            passed += 1
        else:
            found_ids = [m.get("metric_id") for m in matches] if matches else []
            print(f"[FAIL] '{query}' -> Expected: {expected_metric_id}, Got: {found_ids}")
            failed += 1
            failures.append((query, expected_metric_id, found_ids))
    
    print()
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(edge_cases)} tests")
    print("=" * 80)
    
    if failures:
        print("\nFailures:")
        for query, expected, found in failures:
            print(f"  - '{query}': Expected {expected}, Found {found}")
    
    return failed == 0

if __name__ == "__main__":
    success = test_edge_cases()
    sys.exit(0 if success else 1)

