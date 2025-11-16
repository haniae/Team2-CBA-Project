"""Test suite for enhanced metric synonym matching."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def test_natural_language_metrics():
    """Test that natural language metric expressions are recognized."""
    
    test_cases = [
        # Revenue variations
        ("How much money did Apple make?", ["revenue"]),
        ("What's Apple's money made last year?", ["revenue"]),
        ("Show me total revenue for Microsoft", ["revenue"]),
        
        # Profitability variations
        ("What's Tesla's profitability?", ["net_margin"]),
        ("How profitable is Microsoft?", ["net_margin"]),
        ("What are Apple's profit margins?", ["net_margin"]),
        ("Show me margins for Tesla", ["net_margin"]),
        
        # Growth variations
        ("How fast is Microsoft growing?", ["revenue_growth"]),
        ("What's Apple's growth rate?", ["revenue_growth"]),
        ("Show me Tesla's expansion", ["revenue_growth"]),
        
        # Valuation variations
        ("What's Amazon trading at?", ["pe_ratio"]),
        ("How much is Tesla worth?", ["market_cap"]),
        ("What's Microsoft's valuation?", ["market_cap"]),
        ("What's Apple's trading multiple?", ["pe_ratio"]),
        
        # Cash flow variations
        ("How much cash does Apple generate?", ["free_cash_flow"]),
        ("What's Microsoft's cash generation?", ["free_cash_flow"]),
        ("Show me Tesla's operating cash flow", ["cash_operations"]),
        
        # Leverage/debt variations
        ("How much debt does Tesla have?", ["debt_equity"]),
        ("What's Apple's debt level?", ["debt_equity"]),
        ("Is Microsoft leveraged?", ["debt_equity"]),
        
        # Performance variations
        ("How is Apple performing?", ["net_income"]),
        ("How are they doing?", ["net_income"]),
        ("What's Tesla's performance?", ["net_income"]),
        
        # Return metrics
        ("What's Microsoft's return on investment?", ["roic"]),
        ("Show me Apple's ROI", ["roic"]),
        ("What's Tesla's shareholder returns?", ["roe"]),
    ]
    
    print("=" * 80)
    print("Testing Enhanced Metric Synonym Matching")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for query, expected_metrics in test_cases:
        structured = parse_to_structured(query)
        detected_metrics = [m["key"] for m in structured.get("vmetrics", [])]
        
        # Check if at least one expected metric was detected
        success = any(expected in detected_metrics for expected in expected_metrics)
        
        status = "✓" if success else "✗"
        result = "PASS" if success else "FAIL"
        
        print(f"{status} {result}: '{query}'")
        print(f"   Expected metrics: {expected_metrics}")
        print(f"   Detected metrics: {detected_metrics}")
        
        if success:
            passed += 1
        else:
            failed += 1
            print(f"   ⚠ Metric not detected!")
        print()
    
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print(f"Success Rate: {passed / len(test_cases) * 100:.1f}%")
    print("=" * 80)
    
    if failed == 0:
        print("✓ All tests passed!")
        return True
    else:
        print(f"✗ {failed} tests failed. Review patterns above.")
        return False

if __name__ == "__main__":
    success = test_natural_language_metrics()
    sys.exit(0 if success else 1)

