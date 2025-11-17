"""Test suite for enhanced intent classification (Step 3)."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot.parsing.parse import parse_to_structured

def test_enhanced_intents():
    """Test that new intent patterns are correctly classified."""
    
    test_cases = [
        # Forecast intent
        ("What will Apple's revenue be next year?", "forecast"),
        ("Can you forecast Microsoft's earnings?", "forecast"),
        ("What's the outlook for Tesla?", "forecast"),
        ("Where is Amazon heading?", "forecast"),
        ("Project Apple's growth for next quarter", "forecast"),
        
        # Recommendation intent
        ("Should I invest in Tesla?", "recommend"),
        ("Is Microsoft a good investment?", "recommend"),
        ("Would you recommend buying Apple?", "recommend"),
        ("Should I buy Amazon stock?", "recommend"),
        ("Is Tesla worth investing in?", "recommend"),
        
        # Risk analysis intent
        ("What are the risks of investing in Tesla?", "risk_analysis"),
        ("Is Microsoft risky?", "risk_analysis"),
        ("How volatile is Amazon?", "risk_analysis"),
        ("What concerns should I have about Apple?", "risk_analysis"),
        ("Is Tesla stable?", "risk_analysis"),
        
        # Valuation intent
        ("Is Apple overvalued?", "valuation"),
        ("Is Microsoft trading at a fair price?", "valuation"),
        ("Is Tesla expensive?", "valuation"),
        ("What's Amazon's fair value?", "valuation"),
        ("Is Apple undervalued?", "valuation"),
        
        # Quality/health intent
        ("How's Microsoft's financial health?", "quality_check"),
        ("Is Apple financially strong?", "quality_check"),
        ("What's Tesla's competitive advantage?", "quality_check"),
        ("How strong are Amazon's fundamentals?", "quality_check"),
        ("Does Microsoft have a moat?", "quality_check"),
        
        # Existing intents should still work
        ("Compare Apple and Microsoft", "compare"),
        ("Show me Apple's revenue trend", "trend"),
        ("Which company has the best margins?", "rank"),
        ("Explain P/E ratio", "explain_metric"),
    ]
    
    print("=" * 80)
    print("Testing Enhanced Intent Classification (Step 3)")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for query, expected_intent in test_cases:
        structured = parse_to_structured(query)
        detected_intent = structured.get("intent")
        
        success = detected_intent == expected_intent
        status = "✓" if success else "✗"
        result = "PASS" if success else "FAIL"
        
        print(f"{status} {result}: '{query}'")
        print(f"   Expected: {expected_intent}")
        print(f"   Detected: {detected_intent}")
        
        if success:
            passed += 1
        else:
            failed += 1
            print(f"   ⚠ Intent mismatch!")
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
    success = test_enhanced_intents()
    sys.exit(0 if success else 1)

