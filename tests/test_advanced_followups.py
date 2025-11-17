"""Comprehensive test suite for advanced follow-up question handling."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from finanlyzeos_chatbot import FinanlyzeOSChatbot, load_settings

def test_comprehensive_followups():
    """Test all advanced follow-up features together."""
    
    print("=" * 80)
    print("Testing Advanced Follow-up Question Handling")
    print("=" * 80)
    print()
    
    # Create chatbot instance
    settings = load_settings()
    
    test_scenarios = [
        {
            "name": "Context Carryover - Metrics",
            "conversation": [
                ("Tell me about Apple's revenue", "Should mention Apple/AAPL and revenue"),
                ("What about margins?", "Should carry over Apple context"),
            ],
            "expected": "margins.*apple|apple.*margins"
        },
        {
            "name": "Intent Carryover - Risk Analysis",
            "conversation": [
                ("What are the risks of Tesla?", "Risk analysis for Tesla"),
                ("What about Microsoft?", "Should carry over 'risks' intent"),
            ],
            "expected": "risk.*microsoft|microsoft.*risk"
        },
        {
            "name": "Intent Carryover - Valuation",
            "conversation": [
                ("Is Apple overvalued?", "Valuation analysis for Apple"),
                ("What about Amazon?", "Should ask about Amazon valuation"),
            ],
            "expected": "valuation.*amazon|amazon.*valuation|overvalued|undervalued"
        },
        {
            "name": "Pronoun Resolution - Singular",
            "conversation": [
                ("Tell me about Microsoft", "Info about Microsoft"),
                ("What's its P/E ratio?", "Should resolve 'its' to Microsoft"),
            ],
            "expected": "microsoft|msft"
        },
        {
            "name": "Pronoun Resolution - Plural",
            "conversation": [
                ("Compare Apple and Tesla", "Comparison"),
                ("How are they performing?", "Should resolve 'they' to both"),
            ],
            "expected": "apple.*tesla|tesla.*apple|aapl.*tsla|tsla.*aapl"
        },
        {
            "name": "Ambiguity Detection",
            "conversation": [
                ("Compare Apple, Microsoft, and Tesla", "Multi-company comparison"),
                ("Tell me about it", "Should ask for clarification"),
            ],
            "expected_clarification": True
        },
        {
            "name": "Metric-Only Follow-up",
            "conversation": [
                ("Show me Amazon's revenue", "Amazon revenue"),
                ("What about net income?", "Should add Amazon context"),
            ],
            "expected": "amazon.*income|income.*amazon|amzn"
        },
    ]
    
    passed = 0
    failed = 0
    
    for scenario in test_scenarios:
        print(f"\n{'='*80}")
        print(f"Scenario: {scenario['name']}")
        print('='*80)
        
        # Create fresh bot for each scenario
        bot = FinanlyzeOSChatbot.create(settings)
        
        last_reply = ""
        for i, (query, description) in enumerate(scenario['conversation'], 1):
            print(f"\nTurn {i}: {query}")
            print(f"  ({description})")
            
            try:
                # Suppress debug output
                import io
                import contextlib
                
                f = io.StringIO()
                with contextlib.redirect_stdout(f):
                    reply = bot.ask(query)
                
                last_reply = reply
                print(f"  Reply preview: {reply[:100]}...")
                
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
                failed += 1
                break
        
        # Check final result
        if 'expected_clarification' in scenario:
            # Check if clarification was requested
            if "which" in last_reply.lower() or "clarif" in last_reply.lower():
                print(f"\n✅ PASS: Clarification requested (ambiguity detected)")
                passed += 1
            else:
                print(f"\n❌ FAIL: Should have requested clarification")
                failed += 1
        else:
            # Check if expected pattern appears in reply
            import re
            expected_pattern = scenario.get('expected', '')
            if re.search(expected_pattern, last_reply, re.IGNORECASE):
                print(f"\n✅ PASS: Expected pattern found in reply")
                passed += 1
            else:
                print(f"\n❌ FAIL: Expected pattern '{expected_pattern}' not found")
                print(f"  Reply: {last_reply[:200]}...")
                failed += 1
    
    print("\n" + "=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_scenarios)} scenarios")
    print(f"Success Rate: {passed / len(test_scenarios) * 100:.1f}%")
    print("=" * 80)
    
    if failed == 0:
        print("✓ All advanced follow-up tests passed!")
        return True
    else:
        print(f"✗ {failed} tests failed.")
        return False

if __name__ == "__main__":
    success = test_comprehensive_followups()
    sys.exit(0 if success else 1)

